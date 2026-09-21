import math
from quart import Blueprint, jsonify, render_template, request, session

from modules import bot as v
from ..config import OAUTH_URL, INVITE_URL
from ..utils import get_current_user

web_bp = Blueprint('web', __name__)

# ── Public pages ──────────────────────────────────────────────────────────────
@web_bp.route("/")
async def index():
    if "token" not in session:
        return await render_template("index.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template("index.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/plugins/management")
async def web_token_management():
    if "token" not in session:
        return await render_template("web-plugins/management.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template("web-plugins/management.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/plugins/utilities")
async def web_token_utilities():
    if "token" not in session:
        return await render_template("web-plugins/utilities.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template("web-plugins/utilities.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route("/plugins/engagement-and-fun")
async def web_token_engagement():
    if "token" not in session:
        return await render_template("web-plugins/engagement-and-fun.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template("web-plugins/engagement-and-fun.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route('/contact-us')
async def contactUs():
    if "token" not in session:
        return await render_template("contact-us.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template("contact-us.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route('/thanks')
async def thanks():
    if "token" not in session:
        return await render_template("thanks.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template("thanks.html", user=current_user, inviteURL=INVITE_URL)

@web_bp.route('/terms')
async def terms():
    if "token" not in session:
        return await render_template('terms.html', logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL)
    
    current_user = session["user"]
    return await render_template('terms.html', user=current_user, inviteURL=INVITE_URL)

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
        return await render_template('docs.html', logInWithDiscord=OAUTH_URL, initial_page=initial_page, inviteURL=INVITE_URL)

    current_user = session["user"]
    return await render_template('docs.html', user=current_user, initial_page=initial_page, inviteURL=INVITE_URL)


# ── Bot status ────────────────────────────────────────────────────────────────
# Every state a shard can be in, in the order the legend lists them. The legend on the
# status page is built from this too, so what visitors are told can't drift from what
# _shard_state() actually detects. "healthy" states count as up in the page banner.
SHARD_STATES = {
    "online": {
        "label": "Online", "emoji": "", "color": "green", "healthy": True,
        "detail": "Working normally.",
    },
    "busy": {
        "label": "Busy", "emoji": "B", "color": "green", "healthy": True,
        "detail": "Working. Discord is briefly limiting how fast we can look up members and update "
                  "presences, so those may lag a little. Commands are not affected.",
    },
    "starting": {
        "label": "Starting", "emoji": "S", "color": "orange", "healthy": False,
        "detail": "Just connected and finishing setup. Should be online within seconds.",
    },
    "waiting": {
        "label": "Waiting to start", "emoji": "W", "color": "orange", "healthy": False,
        "detail": "Queued while the bot starts up. Discord only lets a few shards connect at a time.",
    },
    "reconnecting": {
        "label": "Reconnecting", "emoji": "R", "color": "red", "healthy": False,
        "detail": "Lost its connection to Discord and is reconnecting. Commands in these servers "
                  "won't respond until it's back.",
    },
}

def _shard_state(shard):
    """Which SHARD_STATES key a connected shard is in. None (not connected yet) is 'waiting'."""
    if shard is None:
        return "waiting"
    if shard.is_closed():
        return "reconnecting"
    if not math.isfinite(shard.latency):
        return "starting"  # socket is open but no heartbeat has been answered yet
    if shard.is_ws_ratelimited():
        return "busy"
    return "online"

def _fetch_shard_data(user=None):
    guilds_by_shard = {}
    for g in v.client.guilds:
        guilds_by_shard.setdefault(g.shard_id, []).append(g)

    # Shards are launched one at a time, and only joined to client.shards once connected.
    # shard_count is known before the first one connects, so the rest show as waiting.
    shards = v.client.shards
    shard_ids = range(v.client.shard_count or len(shards))

    shard_list = []
    for shard_id in shard_ids:
        shard = shards.get(shard_id)
        key = _shard_state(shard)
        state = SHARD_STATES[key]
        shard_guilds = guilds_by_shard.get(shard_id, [])
        connected_since = v.client.shard_uptime.get(shard_id)

        shard_list.append({
            "id": shard_id,
            "label": state["label"],
            "detail": state["detail"],
            "emoji": state["emoji"],
            "color": state["color"],
            "healthy": state["healthy"],
            # a closed socket keeps its last heartbeat latency, which would be stale
            "latency_ms": round(shard.latency * 1000) if key in ("online", "busy") else None,
            "connected_since": connected_since.isoformat() if connected_since else None,
            "servers": len(shard_guilds) if shard else None,
            "user_in_guilds": [g.name for g in shard_guilds if user and g.get_member(user.id)],
        })

    return {
        "shards": shard_list,
        "shards_healthy": sum(1 for s in shard_list if s["healthy"]),
        "shards_total": len(shard_list),
        "guilds": len(v.client.guilds),
    }

@web_bp.route("/status")
async def status():
    if "token" not in session:
        return await render_template("status.html", logInWithDiscord=OAUTH_URL, inviteURL=INVITE_URL, shard_states=SHARD_STATES.values())
    return await render_template("status.html", user=get_current_user(), inviteURL=INVITE_URL, shard_states=SHARD_STATES.values())

@web_bp.route("/api/shard_status")
async def api_shard_status():
    current_user = None
    if "token" in session:
        try:
            current_user = get_current_user()
        except Exception:
            pass  # expired Discord token: the public data is still worth serving
    return jsonify(_fetch_shard_data(current_user))