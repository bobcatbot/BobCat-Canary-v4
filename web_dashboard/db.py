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

async def get_dash_config(guild) -> DashConfig | None:
    """Async read of the guild's DashConfig. Quart's Jinja environment runs
    async, so context-processor helpers can await this directly instead of
    going through the blocking PyMongo client, which stalls the event loop
    that's shared with the Discord bot."""
    doc = await get_guild(guild)
    return doc.dashboard if doc else None

async def get_premium_config(guild) -> dict | None:
    doc = await get_guild(guild)
    return doc.premium if doc else None

async def get_notifications(guild) -> list[Notification]:
    guild_id = _guild_id(guild)
    return await Notification.find(Notification.guild_id == guild_id).to_list()
