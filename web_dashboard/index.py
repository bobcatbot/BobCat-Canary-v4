import logging
import re
import stripe
from pydantic import BaseModel
from quart import Quart, render_template, flash, session, redirect, request, url_for, jsonify
from quart.json.provider import DefaultJSONProvider
from zenora import BadTokenError

from modules import bot as v

from .config import PY_ENV, APP_SECRET, OAUTH_URL, stripe_config
from .context import register_context_processors
from .maintenance import get_state as get_maintenance
from .utils import PremiumModuleError, DEV_IDS

from .blueprints.auth import auth_bp
from .blueprints.web import web_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.stripe import stripe_bp

# ── Server Management ──────────────────────────────────────────────────────
from .blueprints.plugins.welcome import welcome_bp
from .blueprints.plugins.moderation import moderation_bp
from .blueprints.plugins.verification import verification_bp

# ── Utilities ──────────────────────────────────────────────────────────────
from .blueprints.plugins.starboard import starboard_bp
from .blueprints.plugins.forms import forms_bp
from .blueprints.plugins.temporary_channels import temporary_channels_bp
from .blueprints.plugins.ticketing import ticketing_bp
from .blueprints.plugins.stats import stats_bp

# ── Games & Fun ────────────────────────────────────────────────────────────
from .blueprints.plugins.leveling import leveling_bp
from .blueprints.plugins.birthdays import birthdays_bp
from .blueprints.plugins.giveaways import giveaways_bp
from .blueprints.plugins.economy import economy_bp

class PydanticAwareJSONProvider(DefaultJSONProvider):
    """Lets `| tojson` (and jsonify) serialize the typed DashConfig
    sub-models directly - e.g. `data['join']['message']['embed'].fields`,
    which is now a list of EmbedFieldConfig instances rather than plain
    dicts, still round-trips through `{{ ... | tojson }}` in templates."""

    @staticmethod
    def default(obj):
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        return DefaultJSONProvider.default(obj)

app = Quart(__name__)
app.json_provider_class = PydanticAwareJSONProvider
app.json = PydanticAwareJSONProvider(app)

app.config["SECRET_KEY"] = APP_SECRET
app.config["STRIPE_PUBLIC_KEY"] = stripe_config["PUBLIC_KEY"]
app.config["STRIPE_WEBHOOK_KEY"] = stripe_config["WH_KEY"]

stripe.api_key = stripe_config["SECRET_KEY"]

logging.getLogger('quart.serving').setLevel(logging.ERROR)

if PY_ENV != "production":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# ── Blueprints ────────────────────────────────────────────────────────────
app.register_blueprint(web_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(stripe_bp)

# Server Management
app.register_blueprint(welcome_bp)
app.register_blueprint(moderation_bp)
app.register_blueprint(verification_bp)

# Utilities
app.register_blueprint(starboard_bp)
app.register_blueprint(forms_bp)
app.register_blueprint(temporary_channels_bp)
app.register_blueprint(ticketing_bp)
app.register_blueprint(stats_bp)

# Games & Fun
app.register_blueprint(leveling_bp)
app.register_blueprint(birthdays_bp)
app.register_blueprint(giveaways_bp)
app.register_blueprint(economy_bp)

# ── Maintenance mode ──────────────────────────────────────────────────────
# Toggled with `/dev maintenance` or /admin/maintenance. Left open: static files (the page needs its
# CSS), Stripe webhooks (a paid checkout must still be recorded), OAuth (so a
# dev can log in and bypass) and the public status page.
MAINTENANCE_OPEN = ("/static/", "/webhook/stripe", "/oauth/", "/status", "/api/shard_status")

@app.before_request
async def maintenance_gate():
    # Path first: these never touch Mongo, so /status still answers if the DB is down
    if request.path.startswith(MAINTENANCE_OPEN):
        return
    state = await get_maintenance()
    if not state["enabled"]:
        return
    if (session.get("user") or {}).get("id") in DEV_IDS:
        return

    if request.method != "GET":
        return jsonify({
            'status': 'error',
            'message': 'BobCat is down for maintenance. Please try again shortly.',
            'code': 'maintenance',
        }), 503
    return await render_template('error/maintenance.html', eta=state["eta"]), 503

# ── Global error handlers ─────────────────────────────────────────────────
def error_guild_id():
    """The guild a failed /dashboard/<id>/... request was for, so the error
    page can send the user back to that guild's dashboard. Read from the URL
    rather than request.view_args: that's empty on a 404 (no route matched),
    and public routes like /form/<guild_id>/... shouldn't link to a dashboard."""
    match = re.match(r"/dashboard/(\d+)", request.path)
    return int(match.group(1)) if match else None

@app.errorhandler(404)
async def page_not_found(e):
    return await render_template('error/404.html', guild_id=error_guild_id()), 404

@app.errorhandler(403)
async def forbidden(e):
    return await render_template('error/403.html', guild_id=error_guild_id()), 403

@app.errorhandler(500)
async def internal_error(e):
    # Quart has already logged the traceback by the time this runs
    return await render_template('error/500.html', guild_id=error_guild_id()), 500

@app.errorhandler(BadTokenError)
async def handle_bad_token(e):
    session.pop("token", None)
    return redirect(OAUTH_URL)

@app.errorhandler(PremiumModuleError)
async def handle_premium_error(e):
    guild_id = request.view_args.get('guild_id')
    await flash("You don't have access to this module", "PremiumModal")
    return redirect(url_for('dashboard.dashboard_home', guild_id=guild_id))

# ── Template filters ──────────────────────────────────────────────────────
@app.template_filter('titlecase')
def titlecase(s):
    return f"{s}".capitalize()

@app.template_filter('lowercase')
def lowercase(s):
    return f"{s}".lower()

@app.template_filter('formatStatLabel')
def format_stat_label_filter(target):
    """Format camelCase stat target into readable label."""
    label = target
    label = ''.join(' ' + c if c.isupper() else c for c in label).strip()
    label = ' '.join(word.capitalize() for word in label.split())
    return label

@app.template_filter('hexcolor')
def hexcolor_filter(value, default=0x5865f2):
    if not isinstance(value, int):
        value = default
    return f"#{value:06x}"

# ── Context processors ────────────────────────────────────────────────────
register_context_processors(app)

# ── Run ───────────────────────────────────────────────────────────────────
import asyncio
import uvicorn

async def serve_dashboard() -> None:
    """Run the dashboard on the same event loop as the Discord client."""
    config = uvicorn.Config(app, host="localhost", port=8000, log_level="warning")
    server = uvicorn.Server(config)

    serve_task = asyncio.create_task(server.serve())
    while not server.started:
        await asyncio.sleep(0.1)
    print("🌐 Dashboard is Online")

    await serve_task