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

client = commands.AutoShardedBot(
  command_prefix = prefix,
  intents=discord.Intents.all(),
  case_insensitive=True,
  help_command=None,
)

btz_gid = 903243004544962600
guild_ids = [ btz_gid, ]

web_url = "http://localhost:8000"
docs = "http://localhost:8000/docs"

premium = "<:premium:1442138047348084806>"

## Colour Codes ##
blurple = 0x5865F2
green = 0x57F287
red = 0xED4245
white = 0xFFFFFF
clear = 0x2b2d31
error = red
success = green


def dashboard(guild) -> DashConfig | None:
    guild_id = str(getattr(guild, "id", guild))
    data = Guild.get(guild_id).run()
    return data.dashboard if data else None

def style(guild) -> int:
    guild_id = str(getattr(guild, "id", guild))
    guild_data = Guild.get(guild_id).run()
    color = (
        guild_data.settings.get("color", "#5865F2")
        if guild_data
        else "#5865F2"
    )
    try:
        return int(str(color).removeprefix("#"), 16)
    except (TypeError, ValueError):
        return blurple

def datetimes(guild):
    guild_id = str(getattr(guild, "id", guild))
    guild_data = Guild.get(guild_id).run()
    timezone_name = (
        guild_data.settings.get("timezone", "Europe/London")
        if guild_data
        else "Europe/London"
    )
    try:
        return pytz.timezone(str(timezone_name))
    except pytz.UnknownTimeZoneError:
        return pytz.timezone("Europe/London")

_MISSING = object()
def render_placeholders(text: str, **context) -> str:
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

def push_notification(
    guild: Union[int, discord.Guild],
    kind: Literal["info", "error"],
    title: str,
    description: Optional[str] = None,
    fix: Optional[str] = None,
    link: Optional[str] = None,
) -> None:
    guild_id = str(getattr(guild, "id", guild))

    details = description

    if kind == "error" and fix:
        details = (
            f"{description or ''}\n\n"
            f"Suggested fix: {fix}"
        ).strip()

    elif kind == "info" and link:
        details = (
            f"{description or ''}\n\n"
            f"{link}"
        ).strip()

    Notification(
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