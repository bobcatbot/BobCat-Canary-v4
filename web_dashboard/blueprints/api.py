"""JSON API for the Next.js dashboard.

These routes return the same context the Jinja templates get today, as JSON, so
the React frontend can render pages without server-side templates. Auth is the
existing guard chain (both `dashboard_guard` and `plugin_guard` accept an
`Authorization: Bearer` header via `current_token()`), so nothing new to
enforce here.

Writes still go through the existing endpoints (`/dashboard/<gid>/data/post`,
the per-plugin action routes) unchanged.
"""
import logging

from quart import Blueprint, jsonify

from modules import bot as v
from modules.models import Guild, Notification
from ..utils import (
    bearer_client,
    dashboard_guard,
    plugin_guard,
    is_premium,
    plugin_item_cap,
    GuildModels,
)
from ..plugins import PLUGIN_LIST, fetch_plugins

api_bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def _user_dict(u):
    return {"id": str(u.id), "username": u.username, "avatar_url": u.avatar_url}


# ── Guild picker (dashboard/guilds.html) ────────────────────────────────────
@api_bp.route("/dashboard/guilds")
@dashboard_guard
async def guild_list():
    from .dashboard import get_user_eligible_guilds

    current_user = bearer_client().get_current_user()
    eligible = await get_user_eligible_guilds(current_user)

    guilds = [
        {
            "id": str(g["id"]),
            "name": g["name"],
            "icon_url": g["icon_url"],
            "perm": g["perm"],
            "is_bot_in_guild": g["is_bot_in_guild"],
            "btn_name": "Go" if g["is_bot_in_guild"] else "Setup",
            "color": "#5865F2" if g["is_bot_in_guild"] else "#36393f",
        }
        for g in eligible
    ]
    guilds.sort(key=lambda x: not x["is_bot_in_guild"])
    return jsonify({"user": _user_dict(current_user), "guilds": guilds})


# ── Shared shell data (context.py processors) ──────────────────────────────
@api_bp.route("/dashboard/<int:guild_id>/meta")
@dashboard_guard
async def meta(guild_id):
    """Current user, guild, roles/channels/emojis, live plugin list.

    The Jinja context processor injects this into every dashboard render; the
    SPA fetches it once per guild instead.
    """
    guild = v.client.get_guild(guild_id)
    gm = GuildModels(guild)
    doc = await Guild.get(str(guild.id))

    unread_docs = await Notification.find(
        Notification.guild_id == str(guild.id),
        Notification.read == False,  # noqa: E712
    ).sort([(Notification.created_at, -1)]).to_list()
    unread = [
        {
            "id": n.notification_id,
            "type": n.type,
            "title": n.title,
            "description": n.description,
            "fix": n.fix,
            "link": n.link,
            "user": n.user,
            "read": n.read,
        }
        for n in unread_docs[:5]
    ]

    return jsonify({
        "user": _user_dict(bearer_client().get_current_user()),
        "guild": {
            "id": str(guild.id),
            "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else None,
            "member_count": guild.member_count,
        },
        "notifications": {"unread": unread, "unread_count": len(unread_docs)},
        "is_premium": await is_premium(guild),
        "roles": [{**r, "id": str(r["id"]), "color": str(r["color"])} for r in gm.roles],
        "channels": [{**c, "id": str(c["id"])} for c in gm.channels["text"]],
        "emojis": [{**e, "id": str(e["id"]), "url": str(e["url"])} for e in gm.emojis],
        "plugins": [
            {"key": key, **meta_} for key, meta_ in fetch_plugins(doc.dashboard if doc else None)
        ],
    })


# ── Economy (blueprints/plugins/economy.py) ────────────────────────────────
@api_bp.route("/dashboard/<int:guild_id>/economy")
@plugin_guard("economy", require_enabled=False)
async def economy(guild_id):
    """JSON mirror of blueprints/plugins/economy.py:economy()."""
    guild = v.client.get_guild(guild_id)
    config = await Guild.get(str(guild.id))

    dash_data = config.dashboard.economy
    data = dash_data.copy() if isinstance(dash_data, dict) else {}
    data["num_items"] = len(data.get("shop", []))

    guild_premium = await is_premium(guild)
    return jsonify({
        "data": data,
        "is_premium": guild_premium,
        "shop_cap": plugin_item_cap("economy", guild_premium),
        "shop_cap_premium": PLUGIN_LIST.get("economy", {}).get("max_premium", 15),
    })
