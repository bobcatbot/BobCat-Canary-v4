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

guild_ids = [903243004544962600]
btz_gid = 903243004544962600

web_url = "http://localhost:8000"
webDocs_url = "http://localhost:8000/docs"

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
    guild: Union[int, discord.Guild],  # Guild is a hypothetical class; replace with the actual type
    types: Literal["info", "error"],
    title: str,
    description: Optional[str] = None,
    fix: Optional[str] = None,
    link: Optional[str] = None,
) -> None:
    try:
        guildID = guild.id
    except AttributeError:
        guildID = guild

    from cogs._bot.owner import Owner

    server_config = db.get_server_config(guildID, True)
    date = datetime.now()

    notif = {
        'id': Owner.uuid(Owner, 16, strCase='upper/lower/nums'),
        'type': types,
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

    if types == "error" and fix is not None:
        notif["fix"] = fix
    if types == "link" and link is not None:
        notif["link"] = link

    server_config["notifications"].append(notif)
    db.update_server_config(guild, True, key="notifications", value=server_config["notifications"])