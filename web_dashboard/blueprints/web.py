from datetime import datetime
from flask import Blueprint, jsonify, render_template, request, session

from modules import bot as v
from ..config import OAUTH_URL, INVITE_URL
from ..utils import bearer_client

web_bp = Blueprint('web', __name__)

# ── Public pages ──────────────────────────────────────────────────────────────
@web_bp.route("/")
def index():
    if "token" not in session:
        return render_template("index.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template("index.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/plugins/management")
def web_token_management():
    if "token" not in session:
        return render_template("web-plugins/management.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template("web-plugins/management.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/plugins/utilities")
def web_token_utilities():
    if "token" not in session:
        return render_template("web-plugins/utilities.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template("web-plugins/utilities.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/plugins/engagement-and-fun")
def web_token_engagement():
    if "token" not in session:
        return render_template("web-plugins/engagement-and-fun.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template("web-plugins/engagement-and-fun.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route('/contact-us')
def contactUs():
    if "token" not in session:
        return render_template("contact-us.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template("contact-us.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route('/thanks')
def thanks():
    if "token" not in session:
        return render_template("thanks.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template("thanks.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route('/terms')
def terms():
    if "token" not in session:
        return render_template('terms.html', logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return render_template('terms.html', user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/docs")
@web_bp.route("/docs/<section>")
@web_bp.route("/docs/<section>/<page_id>")
async def docs(section=None, page_id=None):
    if page_id:
        initial_page = page_id
    elif section:
        initial_page = section
    else:
        initial_page = 'home'

    if "token" not in session:
        session['redirect'] = request.url
        return render_template('docs.html', logInWithDiscord=OAUTH_URL, initial_page=initial_page, inviteURL=INVITE_URL)

    current_user = session["user"]
    return render_template('docs.html', user=current_user, initial_page=initial_page, inviteURL=INVITE_URL)


# ── Bot status ────────────────────────────────────────────────────────────────
def _fetch_shard_data(user=None):
    STATE_MAP = {
        (False, False): ("",  "Ready",                "green"),
        (False, True):  ("C", "Connected",             "green"),
        (True,  False): ("L", "Logging in",            "orange"),
        (True,  True):  ("Q", "Offline, waiting turn", "red"),
    }

    shard_list = []
    for shard_id, shard in v.client.shards.items():
        emoji, state, color = STATE_MAP[(shard.is_closed(), shard.is_ws_ratelimited())]
        shard_guilds = [g for g in v.client.guilds if g.shard_id == shard_id]
        user_in_guilds = [g.name for g in shard_guilds if user and g.get_member(user.id)]

        shard_list.append({
            "id": shard_id,
            "emoji": emoji,
            "state": state,
            "color": color,
            "latency": f"{shard.latency * 1000:.0f}ms",
            "uptime": v.client.shard_uptime.get(shard_id, datetime.now()).isoformat(),
            "servers": len(shard_guilds),
            "user_in_guilds": user_in_guilds,
        })

    return shard_list

@web_bp.route("/status")
def status():
    if "token" not in session:
        return render_template("status.html", logInWithDiscord=OAUTH_URL, shards=_fetch_shard_data(), inviteURL=INVITE_URL)
    current_user = bearer_client().get_current_user()
    return render_template("status.html", user=current_user, shards=_fetch_shard_data(current_user), inviteURL=INVITE_URL)

@web_bp.route("/api/shard_status")
def api_shard_status():
    try:
        current_user = bearer_client().get_current_user()
    except Exception:
        current_user = None
    return jsonify(_fetch_shard_data(current_user))