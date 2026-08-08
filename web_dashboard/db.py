import pymongo
from datetime import datetime, timezone
from flask import g

from modules.models import Guild, Notification
from .config import mongoURI_db

# ── Legacy raw pymongo handle ────────────────────────────────────────────────
MongoClientBot = pymongo.MongoClient(
    mongoURI_db,
    maxPoolSize=20,
    minPoolSize=2,
    serverSelectionTimeoutMS=10000,
    socketTimeoutMS=10000,
    connectTimeoutMS=10000,
)
db = MongoClientBot['Data']['guilds']

def _guild_id(guild) -> str:
    return str(getattr(guild, "id", guild))

def get_guild(guild) -> Guild | None:
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

def save_config(guild, key: str, value) -> bool:
    if not key or key.startswith(".") or key.endswith("."):
        raise ValueError("A valid dotted key is required.")
    config = get_guild(guild)
    if config is None:
        return False
    parts = key.split(".")
    current = config
    for index, part in enumerate(parts[:-1]):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            next_part = parts[index + 1]
            if part not in current:
                current[part] = [] if next_part.isdigit() else {}
            current = current[part]
        else:
            current = getattr(current, part)
    final = parts[-1]
    if isinstance(current, list):
        idx = int(final)
        if idx == len(current):
            current.append(value)
        else:
            current[idx] = value
    elif isinstance(current, dict):
        current[final] = value
    else:
        setattr(current, final, value)
    config.updated_at = datetime.now(timezone.utc)
    config.save()
    cache_key = f"guild_doc_{_guild_id(guild)}"
    if hasattr(g, cache_key):
        delattr(g, cache_key)
    return True

# ── ADDED FUNCTIONS (for backward compatibility with blueprints) ──

def get_server_config(guild, all=False):
    """
    Returns the raw MongoDB document for the guild.
    If all=True, still returns the whole document (backward compat).
    """
    guild_id = _guild_id(guild)
    doc = db.find_one({"_id": guild_id})
    return doc  # None if not found

def update_config(guild, key, value):
    """
    Update a field in the guild document using MongoDB dot notation.
    Example: update_config(guild, "Dash.welcome.status", True)
    """
    guild_id = _guild_id(guild)
    db.update_one({"_id": guild_id}, {"$set": {key: value}})