import discord
from functools import wraps
from flask import session, request, render_template, url_for
from zenora import APIClient

from modules import bot as v
from modules.models import Guild
from .config import BOT_TOKEN, CLIENT_SECRET
from .db import get_guild
from .plugins import PLUGIN_LIST

# ── Discord OAuth client ───────────────────────────────────────────────────────

api_client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)

def bearer_client():
    """Returns a Zenora users client scoped to the current session token."""
    c = APIClient(session.get("token"), bearer=True)
    return c.users

# ── Auth helpers ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session:
            session['redirect'] = request.url
            return render_template("login.html", logInWithDiscord=url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# ── Premium helpers ───────────────────────────────────────────────────────────
class PremiumModuleError(Exception):
    pass

def is_premium(guild) -> bool:
    """Single source of truth for premium checks using Bunnet directly."""
    # Handle both Guild object and guild ID
    guild_id = str(getattr(guild, "id", guild))
    doc = Guild.get(guild_id).run()
    
    if not doc:
        return False
    
    premium = doc.premium
    return bool(premium.get('status') and premium.get('active'))

def premium_module(guild, module):
    """Check if a guild has access to a premium module."""
    plug = PLUGIN_LIST.get(module, {})
    if plug.get('premium') and not is_premium(guild):
        raise PremiumModuleError(f"Guild {guild} does not have access to {module}.")


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
        return is_premium(self.guild)