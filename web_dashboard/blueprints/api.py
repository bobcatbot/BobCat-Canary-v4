"""JSON API for the Next.js dashboard.

These routes return the same context the Jinja templates get today, as JSON, so
the React frontend can render pages without server-side templates. Auth is the
existing `plugin_guard` chain (it already accepts an `Authorization: Bearer`
header via `current_token()`), so nothing new to enforce here.

One route per migrated page. Writes still go through the existing endpoints
(`/dashboard/<gid>/data/post`, the per-plugin action routes) unchanged.
"""
import logging

from quart import Blueprint, jsonify

from modules import bot as v
from modules.models import Guild
from ..utils import bearer_client, plugin_guard, is_premium, plugin_item_cap, GuildModels
from ..plugins import PLUGIN_LIST, fetch_plugins

api_bp = Blueprint("api", __name__, url_prefix="/api")
logger = logging.getLogger(__name__)


def _user_dict(u):
    return {"id": str(u.id), "username": u.username, "avatar_url": u.avatar_url}


@api_bp.route("/dashboard/<int:guild_id>/meta")
@plugin_guard("economy", require_enabled=False)
async def meta(guild_id):
    """Shared shell data: current user, guild, roles/channels/emojis, plugin list.

    The Jinja context processor injects this into every dashboard render; the
    SPA fetches it once per guild instead.
    """
    guild = v.client.get_guild(guild_id)
    gm = GuildModels(guild)
    doc = await Guild.get(str(guild.id))
    return jsonify({
        "user": _user_dict(bearer_client().get_current_user()),
        "guild": {
            "id": str(guild.id),
            "name": guild.name,
            "icon_url": str(guild.icon.url) if guild.icon else None,
        },
        "roles": [{**r, "id": str(r["id"]), "color": str(r["color"])} for r in gm.roles],
        "channels": [{**c, "id": str(c["id"])} for c in gm.channels["text"]],
        "emojis": [{**e, "id": str(e["id"]), "url": str(e["url"])} for e in gm.emojis],
        "is_premium": await is_premium(guild),
        "plugins": [
            {"key": key, "meta": meta}
            for key, meta in fetch_plugins(doc.dashboard if doc else None)
        ],
    })


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
