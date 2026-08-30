# web_dashboard/db.py – QUART VERSION (NO FLASK g)

from modules import bot as v
from modules.models import Guild, Notification, DashConfig

def _guild_id(guild) -> str:
    return str(getattr(guild, "id", guild))

async def get_guild(guild) -> Guild | None:
    """
    Fetch the full Guild Beanie document.
    Removed Flask's `g` caching - Quart handles this differently.
    """
    guild_id = _guild_id(guild)
    return await Guild.get(guild_id)

async def get_settings_config(guild) -> dict | None:
    doc = await get_guild(guild)
    return doc.settings if doc else None

def get_dash_config(guild) -> DashConfig | None:
    """Sync read of the guild's DashConfig for sync-only call sites
    (context processors / async-Jinja templates). Read-only."""
    guild_id = _guild_id(guild)
    doc = v._sync_guilds.find_one({"_id": guild_id}, {"Dash": 1})
    if not doc:
        return None
    return DashConfig(**(doc.get("Dash") or {}))

async def get_premium_config(guild) -> dict | None:
    doc = await get_guild(guild)
    return doc.premium if doc else None

async def get_notifications(guild) -> list[Notification]:
    guild_id = _guild_id(guild)
    return await Notification.find(Notification.guild_id == guild_id).to_list()
