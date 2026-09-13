import os
import re
import pytz
import random
import pymongo
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

# Dedicated *synchronous* pymongo handle for the hot, sync-only config reads
# (`style`, `datetimes`). Beanie/motor is async and loop-bound, so it can't be
# used from the many synchronous call sites (e.g. `discord.Embed(color=v.style(...))`).
# This is a read-only path; all writes still go through Beanie.
_sync_data = pymongo.MongoClient(mongoURI_db)["Data"]
_sync_guilds = _sync_data["guilds"]
_sync_notifs = _sync_data["notifications"]

client = commands.AutoShardedBot(
  command_prefix = prefix,
  intents=discord.Intents.all(),
  case_insensitive=True,
  help_command=None,
  # Gated commands (see gated_command() below) must never be picked up by
  # Pycord's own automatic on_connect sync before we've had a chance to
  # mark them as guild-scoped - otherwise that first automatic sync would
  # register them globally. sync_gated_commands() drives the one true
  # startup sync instead (see GuildEvents.on_ready in cogs/_bot/bot_dash.py).
  auto_sync_commands=False,
)

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

async def dashboard(guild) -> DashConfig | None:
    guild_id = str(getattr(guild, "id", guild))
    data = await Guild.get(guild_id)
    return data.dashboard if data else None

# ── Per-guild command gating ─────────────────────────────────────────────
# Some plugins' commands (e.g. birthdays) should not just refuse to run
# when the plugin is off - they should disappear from the Discord slash
# picker entirely in guilds where it's disabled. Discord's per-guild
# application-command endpoint is a full replace, not an add/remove, so we
# can never push "just this one plugin's commands" for a guild in
# isolation - that would silently wipe out every other gated plugin's
# commands already registered there. Instead:
#   - every gated command's own `.guild_ids` list is kept accurate at all
#     times, added/removed from in place, never overwritten wholesale
#   - resyncing always goes through sync_commands() using its own defaults
#     (no `commands=`/`guild_ids=` override), so a guild's bulk overwrite
#     is always rebuilt from every command's own correct state, not just
#     whichever plugin triggered this particular resync
_gated_commands: dict[str, list] = {}

def gated_command(plugin_key: str):
    """Mark a slash command as belonging to `plugin_key`: it's only
    registered (visible in the Discord command picker) in guilds where
    dashboard.<plugin_key>.status is True. Stack this below
    @commands.slash_command(...) (and below any @discord.option(...)),
    same position as any other command decorator (e.g. is_dev()).

    sync_gated_commands() must be called once at startup, after every cog
    is loaded, and again with a specific guild_id whenever a gated
    plugin's status changes for that guild.
    """
    def decorator(func):
        func.__gated_plugin__ = plugin_key
        return func
    return decorator

def _collect_gated_commands() -> None:
    """Walk every pending application command once and bucket the ones
    marked with @gated_command by plugin key. Idempotent - safe to call
    more than once."""
    _gated_commands.clear()
    for cmd in client.pending_application_commands:
        # pending_application_commands also holds SlashCommandGroup entries
        # (a container of subcommands, no single callback of its own) -
        # @gated_command marks the underlying function of a leaf command, so
        # groups can't carry it. None of BobCat's gated commands live inside
        # a group yet; if one needs to, this will need to walk group.subcommands too.
        if not isinstance(cmd, discord.SlashCommand):
            continue

        plugin_key = getattr(cmd.callback, "__gated_plugin__", None)
        if plugin_key is None:
            continue
        cmd.guild_ids = []  # never global - membership is managed explicitly below
        _gated_commands.setdefault(plugin_key, []).append(cmd)

def _command_enabled(doc, plugin_key: str, command_name: str) -> bool:
    """A gated command is only enabled when its plugin is on AND it hasn't
    been individually disabled - the per-command toggle is a finer-grained
    override that only ever narrows an enabled plugin, never widens a
    disabled one."""
    if doc is None:
        return False
    plugin = getattr(doc.dashboard, plugin_key, None)
    if not getattr(plugin, "status", False):
        return False
    return command_name not in doc.settings.disabled_commands

def is_gated_plugin(plugin_key: str) -> bool:
    """True if at least one command is registered under @gated_command(plugin_key)."""
    if not _gated_commands:
        _collect_gated_commands()
    return plugin_key in _gated_commands

def gated_commands_for(plugin_key: str) -> list:
    """The actual registered SlashCommand objects for `plugin_key`, so a
    dashboard page can list a plugin's commands (name, description, ...)
    straight from the source instead of a second hand-maintained list."""
    if not _gated_commands:
        _collect_gated_commands()
    return list(_gated_commands.get(plugin_key, []))

async def sync_gated_commands(guild_id: int | None = None) -> None:
    """Bring every gated command's guild_ids in line with its plugin's
    current status, then push the result. Pass a guild_id right after a
    dashboard toggle to only recheck that one guild; omit it to recheck
    every guild the bot is in (startup).
    """
    if not _gated_commands:
        _collect_gated_commands()

    if not _gated_commands:
        return

    target_guild_ids = [guild_id] if guild_id is not None else [g.id for g in client.guilds]

    for gid in target_guild_ids:
        doc = await Guild.get(str(gid))  # one fetch per guild, reused across every plugin/command below
        for plugin_key, cmds in _gated_commands.items():
            for cmd in cmds:
                enabled = _command_enabled(doc, plugin_key, cmd.qualified_name)
                current = set(cmd.guild_ids or [])
                if enabled:
                    current.add(gid)
                else:
                    current.discard(gid)
                cmd.guild_ids = sorted(current)

    # force=True: always push the full state unconditionally, skipping
    # Pycord's own diff-against-what-it-thinks-Discord-has check. Ruling out
    # a stale/incorrect diff as the cause of "disable is instant, enable
    # needs a client refresh" - if that persists with force=True too, it's
    # Discord's own command-list caching, not a bug on our end.
    await client.sync_commands(check_guilds=target_guild_ids, force=True)

def style(guild) -> int:
    guild_id = str(getattr(guild, "id", guild))
    guild_data = _sync_guilds.find_one({"_id": guild_id}, {"settings.color": 1})
    color = (
        (guild_data.get("settings") or {}).get("color", "#5865F2")
        if guild_data
        else "#5865F2"
    )
    try:
        return int(str(color).removeprefix("#"), 16)
    except (TypeError, ValueError):
        return blurple

def datetimes(guild):
    guild_id = str(getattr(guild, "id", guild))
    guild_data = _sync_guilds.find_one({"_id": guild_id}, {"settings.timezone": 1})
    timezone_name = (
        (guild_data.get("settings") or {}).get("timezone", "Europe/London")
        if guild_data
        else "Europe/London"
    )
    try:
        return pytz.timezone(str(timezone_name))
    except pytz.UnknownTimeZoneError:
        return pytz.timezone("Europe/London")

def is_premium_sync(guild) -> bool:
    """Synchronous premium check for sync-only call sites (GuildModels /
    async-Jinja templates). Mirrors web_dashboard.utils.is_premium; read-only."""
    guild_id = str(getattr(guild, "id", guild))
    doc = _sync_guilds.find_one({"_id": guild_id}, {"premium": 1})
    premium = (doc or {}).get("premium") or {}
    return bool(premium.get("status") and premium.get("active"))

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

async def push_notification(
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

