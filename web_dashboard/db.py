# web_dashboard/db.py – QUART VERSION (NO FLASK g)

from modules.models import Guild, Notification

def _guild_id(guild) -> str:
    return str(getattr(guild, "id", guild))

def get_guild(guild) -> Guild | None:
    """
    Fetch the full Guild Bunnet document.
    Removed Flask's `g` caching - Quart handles this differently.
    """
    guild_id = _guild_id(guild)
    return Guild.get(guild_id).run()

def get_settings_config(guild) -> dict | None:
    doc = get_guild(guild)
    return doc.settings if doc else None

def get_dash_config(guild):
    doc = get_guild(guild)
    return doc.dashboard if doc else None

def get_premium_config(guild) -> dict | None:
    doc = get_guild(guild)
    return doc.premium if doc else None

def get_notifications(guild) -> list[Notification]:
    guild_id = _guild_id(guild)
    return Notification.find(Notification.guild_id == guild_id).run()