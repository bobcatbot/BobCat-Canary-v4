# web_dashboard/db.py – MINIMAL VERSION

from flask import g
from modules.models import Guild, Notification

def _guild_id(guild) -> str:
    return str(getattr(guild, "id", guild))

def get_guild(guild) -> Guild | None:
    """
    Fetch the full Guild Bunnet document, cached once per request on Flask's `g`.
    """
    guild_id = _guild_id(guild)
    cache_key = f"guild_doc_{guild_id}"

    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached

    doc = Guild.get(guild_id).run()
    if doc is not None:
        setattr(g, cache_key, doc)
    return doc

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

# ── REMOVED: get_server_config(), update_config() ──
# Blueprints now use Bunnet models directly.