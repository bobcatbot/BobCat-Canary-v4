import logging
import stripe
from threading import Thread
from flask import Flask, render_template, flash, session, redirect, request, url_for
from zenora import BadTokenError

from modules import bot as v

from .config import PY_ENV, APP_SECRET, OAUTH_URL, stripe_config
from .context import register_context_processors
from .utils import PremiumModuleError

from .blueprints.auth import auth_bp
from .blueprints.web import web_bp
from .blueprints.dashboard import dashboard_bp
from .blueprints.stripe import stripe_bp

from .blueprints.plugins.welcome import welcome_bp
from .blueprints.plugins.moderation import moderation_bp
from .blueprints.plugins.verification import verification_bp
from .blueprints.plugins.starboard import starboard_bp
from .blueprints.plugins.forms import forms_bp
from .blueprints.plugins.temporary_channels import temporary_channels_bp
from .blueprints.plugins.ticketing import ticketing_bp
from .blueprints.plugins.leveling import leveling_bp
from .blueprints.plugins.birthdays import birthdays_bp
from .blueprints.plugins.giveaways import giveaways_bp
from .blueprints.plugins.economy import economy_bp
 
app = Flask(__name__)

app.config["SECRET_KEY"] = APP_SECRET
app.config["STRIPE_PUBLIC_KEY"] = stripe_config["PUBLIC_KEY"]
app.config["STRIPE_WEBHOOK_KEY"] = stripe_config["WH_KEY"]

stripe.api_key = stripe_config["SECRET_KEY"]

logging.getLogger('werkzeug').setLevel(logging.ERROR)

if PY_ENV != "production":
    app.config['TEMPLATES_AUTO_RELOAD'] = True

# ── Blueprints ────────────────────────────────────────────────────────────
app.register_blueprint(web_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(stripe_bp)

# Plugin blueprints
app.register_blueprint(welcome_bp)
app.register_blueprint(moderation_bp)
app.register_blueprint(verification_bp)
app.register_blueprint(starboard_bp)
app.register_blueprint(forms_bp)
app.register_blueprint(temporary_channels_bp)
app.register_blueprint(ticketing_bp)
app.register_blueprint(leveling_bp)
app.register_blueprint(birthdays_bp)
app.register_blueprint(giveaways_bp)
app.register_blueprint(economy_bp)

# ── Global error handlers ─────────────────────────────────────────────────
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error/404.html'), 404

@app.errorhandler(BadTokenError)
def handle_bad_token(e):
    session.pop("token", None)
    return redirect(OAUTH_URL)

@app.errorhandler(PremiumModuleError)
def handle_premium_error(e):
    guild_id = request.view_args.get('guild_id')
    flash("You don't have access to this module", "PremiumModal")
    return redirect(url_for('dashboard.dashboard_home', guild_id=guild_id))

# ── Template filters ──────────────────────────────────────────────────────
@app.template_filter('titlecase')
def titlecase(s):
    return f"{s}".capitalize()

@app.template_filter('lowercase')
def lowercase(s):
    return f"{s}".lower()

# ── Context processors ────────────────────────────────────────────────────
register_context_processors(app)

# ── Run ───────────────────────────────────────────────────────────
import waitress

app_started = False

@v.client.event
async def on_ready():
    if app_started:
        print("Dashboard is Online")

def run_app():
    global app_started
    app_started = True
    waitress.serve(app, host='localhost', port=8000, threads=16, connection_limit=200)

def run_dashboard():
    Thread(target=run_app).start()