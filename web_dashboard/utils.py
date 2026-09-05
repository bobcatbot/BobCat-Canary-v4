import discord
from functools import wraps
from quart import session, request, render_template, url_for, redirect, jsonify, flash, g
from zenora import APIClient

from modules import bot as v
from modules.models import Guild
from .config import BOT_TOKEN, CLIENT_SECRET
from .db import get_guild
from .plugins import PLUGIN_LIST

# ── Discord OAuth client ───────────────────────────────────────────────────────

api_client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)


def current_token():
    """The caller's Discord bearer token.

    Server-rendered pages carry it in the signed-cookie session
    (``session["token"]``); the Next.js frontend calls the same routes with an
    ``Authorization: Bearer <token>`` header instead. Accept either so one set
    of blueprints serves both front-ends during the migration.
    """
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return session.get("token")


def bearer_client():
    """Returns a Zenora users client scoped to the current caller's token."""
    c = APIClient(current_token(), bearer=True)
    return c.users


async def _cached_guild(guild_id):
    """Fetch a Guild document, memoized per-request.

    check_guild_permission / is_premium / plugin_enabled are all called for
    the same guild within a single request (e.g. from plugin_guard); this
    avoids re-fetching the identical document from Mongo each time.
    """
    guild_id = str(guild_id)
    cache = getattr(g, "_guild_doc_cache", None)
    if cache is None:
        cache = {}
        g._guild_doc_cache = cache
    if guild_id not in cache:
        cache[guild_id] = await Guild.get(guild_id)
    return cache[guild_id]

# ── Auth helpers ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if 'token' not in session:
            session['redirect'] = request.url
            return await render_template("login.html", logInWithDiscord=url_for('auth.login'))
        return await f(*args, **kwargs)
    return decorated_function


async def check_guild_permission(guild, user_id) -> tuple[bool, str]:
    """Check if user has permission to modify guild settings."""
    try:
        member = guild.get_member(user_id)
        if member is None:
            return False, "Not a member of this guild"

        # Check if user is guild owner
        if guild.owner_id == user_id:
            return True, "Owner"

        # Get guild config for custom roles
        config = await _cached_guild(guild.id)
        if config is None:
            return False, "Guild config not found"

        settings = config.settings

        # Check if user has administrator permission
        if member.guild_permissions.administrator:
            return True, "Administrator"

        # Check custom admin roles
        admin_roles = settings.get('admin_roles', [])
        if any(str(role.id) in admin_roles for role in member.roles):
            return True, "Admin Role"

        # Check bot master roles
        bot_masters = settings.get('bot_masters', [])
        if any(str(role.id) in bot_masters for role in member.roles):
            return True, "Bot Master"

        return False, "Insufficient permissions"

    except Exception as e:
        return False, f"Error checking permissions: {str(e)}"


# ── Premium helpers ───────────────────────────────────────────────────────────
class PremiumModuleError(Exception):
    pass

async def is_premium(guild) -> bool:
    """Single source of truth for premium checks using Beanie directly."""
    guild_id = str(getattr(guild, "id", guild))
    doc = await _cached_guild(guild_id)

    if not doc:
        return False

    premium = doc.premium
    return premium.get('status') and premium.get('active')

async def premium_module(guild, module):
    """Check if a guild has access to a premium module."""
    plug = PLUGIN_LIST.get(module, {})
    if plug.get('premium') and not await is_premium(guild):
        raise PremiumModuleError(f"Guild {guild} does not have access to {module}.")


async def plugin_enabled(guild_id, plugin_key) -> bool:
    """True if the plugin's main status toggle is on for this guild."""
    db_key = PLUGIN_LIST.get(plugin_key, {}).get('db_key', plugin_key)
    doc = await _cached_guild(guild_id)
    cfg = getattr(doc.dashboard, db_key, None) if doc else None
    if isinstance(cfg, dict):
        return bool(cfg.get('status'))
    return bool(getattr(cfg, 'status', False))


def plugin_item_cap(plugin_key, guild_is_premium) -> int:
    """Max first-class items (panels / hubs / forms / shop items / stat
    channels) a guild may create for a plugin: `max_premium` with premium,
    `max` without. Falls back to 15 / 5."""
    meta = PLUGIN_LIST.get(plugin_key, {})
    return meta.get('max_premium', 15) if guild_is_premium else meta.get('max', 5)


# ── Payload shaping helpers ─────────────────────────────────────────────────────
def unflatten_keys(data: dict) -> dict:
    """Expand a flat dict with dotted keys into a nested dict.

    ``{"a.b.c": 1, "a.b.d": 2, "x": 3}`` -> ``{"a": {"b": {"c": 1, "d": 2}}, "x": 3}``

    The dashboard forms post settings as dotted paths (``intro_message.embed.title``);
    the bot and the edit templates expect the nested shape.
    """
    result: dict = {}
    for key, value in data.items():
        parts = str(key).split('.')
        node = result
        for part in parts[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[parts[-1]] = value
    return result


def deep_merge(base: dict, incoming: dict) -> dict:
    """Recursively merge ``incoming`` into ``base`` (mutates and returns ``base``).

    Nested dicts merge key-by-key so a partial update (e.g. only
    ``intro_message.embed.title``) doesn't wipe its siblings; every other value
    type overwrites.
    """
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
    return base

# ── Plugin-route authorization guard ─────────────────────────────────────────
def plugin_guard(plugin_key, *, require_enabled=True):
    """Guard for every dashboard guild route - page, action, or combined.

    Same chain for all requests: authenticated -> guild is known -> caller has
    guild permission -> guild has premium for the module. For *write* requests
    (method not in GET/HEAD/OPTIONS) it also enforces the plugin's main status
    toggle when `require_enabled` is True.

    Failure response format is inferred from the method: JSON + HTTP status for
    writes, an HTML login page / 404 / redirect-with-flash for reads. So the
    same decorator serves page routes, JSON action routes, and combined
    GET/POST routes with no inline checks.

    `plugin_key` is the PLUGIN_LIST key ('giveaway', 'stats', ...), not the
    db_key used on DashConfig.
    """
    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            guild_id = kwargs.get('guild_id') or (args[0] if args else None)
            is_write = request.method not in ('GET', 'HEAD', 'OPTIONS')

            async def login_page():
                session['redirect'] = request.url
                return await render_template("login.html", logInWithDiscord=url_for('auth.login'))

            if not current_token():
                if is_write:
                    return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
                return await login_page()

            guild = v.client.get_guild(guild_id)
            if guild is None:
                if is_write:
                    return jsonify({'status': 'error', 'message': 'Guild not found'}), 404
                return await render_template("error/404.html"), 404

            try:
                user = bearer_client().get_current_user()
            except Exception:
                if is_write:
                    return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
                return await login_page()

            allowed, level = await check_guild_permission(guild, user.id)
            if not allowed:
                if is_write:
                    return jsonify({'status': 'error', 'message': f'Permission denied: {level}'}), 403
                await flash(f"You don't have permission to manage this server ({level})", "danger")
                return redirect(url_for('dashboard.guilds'))

            try:
                await premium_module(guild, plugin_key)
            except PremiumModuleError:
                if is_write:
                    return jsonify({'status': 'error', 'message': 'This module requires premium'}), 403
                raise  # -> app-level errorhandler: flash + redirect

            if is_write and require_enabled and not await plugin_enabled(guild_id, plugin_key):
                return jsonify({
                    'status': 'error',
                    'message': 'This plugin is disabled. Enable it before making changes.',
                    'code': 'plugin_disabled',
                }), 409

            return await f(*args, **kwargs)
        return wrapper
    return decorator


# ── GuildModels ───────────────────────────────────────────────────────────────
class GuildModels:
    def __init__(self, guild: discord.Guild = None):
        self.guild = guild

    @property
    def roles(self):
        roles = [
            {
                'id': role.id,
                'name': role.name,
                'color': role.colors.primary if hasattr(role.colors, 'primary') else 0,
                'permissions': role.permissions.value,
                'position': role.position,
                'disabled': role.position >= self.guild.me.top_role.position,
            }
            for role in self.guild.roles
        ]
        return sorted(roles, key=lambda x: x['position'], reverse=True)

    @property
    def channels(self):
        text_channels = sorted([
            {
                'type': 'text',
                'id': channel.id,
                'name': channel.name,
                'position': channel.position,
                'can_send': channel.permissions_for(self.guild.me).send_messages,
            }
            for channel in self.guild.text_channels
        ], key=lambda x: x['position'])

        return {
            "text": text_channels,
            "voice": sorted(self.guild.voice_channels, key=lambda c: c.position),
            "categories": sorted(self.guild.categories, key=lambda c: c.position),
        }

    @property
    def emojis(self):
        return [
            {
                'id': emoji.id,
                'name': emoji.name,
                'url': emoji.url,
                'animated': emoji.animated,
            }
            for emoji in self.guild.emojis
        ]

    @property
    def isPremium(self):
        return v.is_premium_sync(self.guild)