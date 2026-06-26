import pymongo
from flask import g
from .config import mongoURI_db

MongoClientBot = pymongo.MongoClient(
    mongoURI_db,
    maxPoolSize=20,          # allow up to 20 concurrent DB connections
    minPoolSize=2,           # keep 2 warm connections ready
    serverSelectionTimeoutMS=10000,
    socketTimeoutMS=10000,
    connectTimeoutMS=10000,
)
db = MongoClientBot['Bot']['Bot']


def _get_guild_id(guild):
    try:
        return str(guild.id)
    except AttributeError:
        return str(guild)


def _fetch_doc(guild_id: str) -> dict | None:
    """
    Fetch the full guild document once per request and cache it on Flask's g.
    Subsequent calls within the same request return the cached copy instantly.
    """
    cache_key = f"doc_{guild_id}"
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached

    doc = db.find_one({"_id": guild_id})
    if doc is not None:
        setattr(g, cache_key, doc)
    return doc


def get_server_config(guild, all=False):
    guild_id = _get_guild_id(guild)
    data = _fetch_doc(guild_id)
    if data is None:
        return None
    if all:
        return data
    return data["Bot"]


def get_dash_config(guild):
    guild_id = _get_guild_id(guild)
    data = _fetch_doc(guild_id)
    if data is None:
        return None
    return data["Dash"]


def update_config(guild_id, key: str, value):
    _id = _get_guild_id(guild_id)

    # Bust the per-request cache so callers see fresh data if they re-read
    cache_key = f"doc_{_id}"
    if hasattr(g, cache_key):
        delattr(g, cache_key)

    result = db.update_one(
        {'_id': _id},
        {'$set': {key: value}}
    )
    return bool(result)