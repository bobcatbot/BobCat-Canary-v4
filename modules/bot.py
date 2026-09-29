import os
import re
import pytz
import random
import discord
from dotenv import load_dotenv
from typing import Literal, Optional, Union
from discord.ext import commands

from .models import DashConfig, Guild, Notification

load_dotenv()

PY_ENV: Literal["development", "production"] = os.getenv('PY_ENV')
prefix = os.getenv('PREFIX')
token = os.getenv('BOT_TOKEN')
mongoURI_db = os.getenv('mongoURI_db')
mongo_cdn = os.getenv('mongoURI_cdn')

_settings: dict[str, dict] = {}

client = commands.AutoShardedBot(
  command_prefix = prefix,
  intents=discord.Intents.all(),
  case_insensitive=True,
  help_command=None,
)

def get_client(guild_id: Union[int, str, None] = None) -> commands.Bot:
    """Return the bot instance that serves a given guild.

    Always the main client for now. This is the seam a future white-label /
    custom-bot feature would hook into - once a guild can run its own bot,
    this becomes the single place that resolves guild_id -> the right
    client, instead of every call site assuming `client`.
    """
    return client

btz_gid = 903243004544962600
guild_ids = [ btz_gid, ]

web_url = os.getenv('URL_BASE') or "http://localhost:8000"
docs = f"{web_url}/docs"

# Dedicated secret for signing captcha_web verification links. Falls back to
# APP_SECRET (the Quart session key) so the feature still works before anyone
# adds a dedicated VERIFY_SECRET, but a separate secret is preferred so it can
# be rotated independently of dashboard sessions.
verify_secret = (os.getenv('VERIFY_SECRET') or os.getenv('APP_SECRET') or "").encode()

premium = "<:premium:1442138047348084806>"

## Colour Codes ##
blurple = 0x5865F2
green = 0x57F287
red = 0xED4245
white = 0xFFFFFF
clear = 0x2b2d31
error = red
success = green

async def refresh_settings_cache():
    cursor = Guild.get_pymongo_collection().find(
        {}, {"settings.color": 1, "settings.timezone": 1, "premium": 1}
    )
    fresh = {doc["_id"]: doc async for doc in cursor}
    _settings.clear()
    _settings.update(fresh)

def _guild_doc(guild) -> dict:
    return _settings.get(str(getattr(guild, "id", guild)), {})

async def dashboard(guild) -> DashConfig | None:
    guild_id = str(getattr(guild, "id", guild))
    data = await Guild.get(guild_id)
    return data.dashboard if data else None

def style(guild) -> int:
    color = (_guild_doc(guild).get("settings") or {}).get("color", "#5865F2")
    try:
        return int(str(color).removeprefix("#"), 16)
    except (TypeError, ValueError):
        return blurple

def datetimes(guild):
    FALLBACK = "UTC"
    timezone_name = (_guild_doc(guild).get("settings") or {}).get("timezone", FALLBACK)
    try:
        return pytz.timezone(str(timezone_name))
    except pytz.UnknownTimeZoneError:
        return pytz.timezone(FALLBACK)

_MISSING = object()
def c(text: str, **context) -> str:
    def replace(match: re.Match) -> str:
        parts = match.group(1).split(".")
        base = parts[0]
        if base not in context:
            return match.group(0)
        obj = context[base]
        attrs = parts[1:]

        # {x.url} and {x} are equivalent for Asset-like objects since
        # str(Asset) already returns the URL — drop a trailing "url"
        # so both forms resolve the same way.
        if attrs and attrs[-1].lower() == "url":
            attrs = attrs[:-1]
        for attr in attrs:
            obj = getattr(obj, attr, _MISSING)
            if obj is _MISSING:
                return match.group(0)
        return str(obj)
    return re.sub(r"\{([\w.]+)\}", replace, text)

def uuid(length: int = 8, strCase: Literal[ "upper/lower/nums/special"] = "upper/lower/nums") -> str:
    _CHARSET = {
        "upper":   "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "lower":   "abcdefghijklmnopqrstuvwxyz",
        "nums":    "0123456789",
        "special": "!@#$%^&*()_+-=[]{};:,./<>?",
    }
        
    parts = [k.strip() for k in strCase.split("/")]
    unknown = [p for p in parts if p not in _CHARSET]
    
    if unknown:
        raise ValueError(f"Unknown charset(s): {unknown}. Valid: {list(_CHARSET)}")

    combination = "".join(_CHARSET[p] for p in parts)
    return "".join(random.choices(combination, k=length))

async def push_notification(
    guild: Union[int, discord.Guild],
    kind: Literal["info", "warning", "error"],
    title: str,
    description: Optional[str] = None,
    fix: Optional[str] = None,
    link: Optional[str] = None,
) -> None:
    guild_id = str(getattr(guild, "id", guild))

    await Notification(
        guild_id=guild_id,
        notification_id=uuid(16, strCase="upper/lower/nums"),
        type=kind,
        title=title,
        description=description,
        fix=fix if kind == "error" else None,
        link=link if kind == "info" else None,
        user=str(client.user) if client.user else None,
        read=False,
    ).insert()

