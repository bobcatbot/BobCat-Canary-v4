import os
import pytz
import random
import discord
from datetime import datetime
from dotenv import load_dotenv
from typing import Literal, Optional, Union
from discord.ext import commands

from .database import Database

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

db = Database()

premium = "<:premium:1442138047348084806>"

## Colour Codes ##
blurple = 0x5865F2
green = 0x57F287
red = 0xED4245
white = 0xFFFFFF
clear = 0x2b2d31
error = red
success = green

def dashboard(guild, data):
    try:
        val = db.get_dash(guild)
        
        keys = data.split('.')
        for k in keys:
            val = val[k]
        
        return val
    except AttributeError:
        return None

def style(guild):
    data = db.get_server_config(guild, True)
    color = data["settings"]["color"]
    clr = int(color.replace("#", ""), 16)
    return clr

def datetimes(guild):
    tz = db.get_server_config(guild, True)["settings"]["timezone"]
    dt = pytz.timezone(f'{tz}')
    return dt

def uuid(length: int = 8, strCase: Literal["upper/lower/nums/special"] = "upper/lower/nums") -> str:
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
    try:
        guild_id = guild.id
    except AttributeError:
        guild_id = guild

    date = datetime.now()

    notif = {
        'id': uuid(16, strCase='upper/lower/nums'),
        'type': kind,
        'title': title,
        'description': description,
        'user': client.user.name,
        'read': False,
        'created_at': {
            'date': date.strftime("%Y-%m-%d"),
            'time': date.strftime("%H:%M"),
            'timestamp': date.timestamp(),
        },
    }

    if kind == "error" and fix is not None:
        notif["fix"] = fix
    if kind == "info" and link is not None:
        notif["link"] = link

    # Use $push to avoid race condition from read-modify-write
    db.db.update_one(
        {"_id": str(guild_id)},
        {"$push": {"notifications": notif}}
    )