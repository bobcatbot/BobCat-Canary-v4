import discord
from discord.ext import commands
from pymongo.errors import DuplicateKeyError
from modules import bot as v
from modules.models import Guild, Leveling as LevelingModel

def _default_dashboard() -> dict:
    """Default dashboard config for a brand new guild. Keys here must match DashConfig's fields in models.py exactly."""
    return {
        "welcome": {
            "status": False,
            "join": {
                "status": False,
                "channel": None,
                "message": {
                    "type": "text",
                    "content": "Hey {user}, welcome to **{server}**!"
                },
            },
            "dm": {
                "status": False,
                "message": {
                    "type": "text",
                    "content": "Have a great time here in **{server}**"
                },
            },
            "leave": {
                "status": False,
                "channel": None,
                "message": {
                    "type": "text",
                    "content": "**{user}** just left the server. Bye!"
                },
            },
            "autoRoles": {
                "status": False,
                "roles": []
            },
        },
        "moderation": {
            "status": False,
            "automod": {
                "antilink": {
                    "status": False,
                    "block_invites": False,
                    "block_scam_links": False,
                    "action": "delete",
                    "whitelist_channels": [],
                    "whitelist_roles": [],
                    "dm": []  # server | action | moderator | reason
                },
                "antispam": {
                    "status": False,
                    "threshold": 5,
                    "interval": 10,
                    "action": "delete",
                    "whitelist_channels": [],
                    "whitelist_roles": [],
                    "dm": []  # server | action | moderator | reason
                },
                "ghostping": {
                    "status": False,
                    "delete_window": 60,
                    "action": "warn",
                    "whitelist_channels": [],
                    "whitelist_roles": [],
                    "dm": []  # server | action | moderator | reason
                },
                "caps": {
                    "status": False,
                    "threshold": 70,
                    "min_length": 10,
                    "action":"delete",
                    "whitelist_channels": [],
                    "whitelist_roles": [],
                    "dm": []  # server | action | moderator | reason
                },
            },
            "settings": {
                "kick": {
                    "dm": []  # server | action | moderator | reason
                },
                "ban": {
                    "dm": [],  # server | action | moderator | reason
                    "deleteMessageDays": "0"
                },
                "mute": {
                    "dm": [],  # server | action | moderator | reason
                    "type": "timeout",
                    "duration": "60-sec"
                },
                "warn": {
                    "dm": []  # server | action | moderator | reason
                },
            },
            "logging": {
                "channel": None,
                "bots": False,
                "events": {
                    "ModerationKick": False, "ModerationBan": False, "ModerationUnban": False, "ModerationMute": False,
                    "ModerationUnmute": False, "ModerationWarn": False, "ModerationUnwarn": False,
                    "MemberJoin": False, "MemberLeave": False, "MemberUpdate": False, "MemberBan": False, "MemberUnban": False,
                    "MessageDelete": False, "MessageEdit": False,
                    "ModerationAntiLink": False, "ModerationAntiSpam": False, "ModerationGhostPing": False, "ModerationCaps": False,
                    "ServerUpdate": False, "ServerInviteCreate": False, "ServerInviteDelete": False, "ServerEmojis": False,
                    "ChannelCreate": False, "ChannelDelete": False, "ChannelUpdate": False,
                    "RoleCreate": False, "RoleDelete": False, "RoleUpdate": False,
                    "Verification": False,
                },
            },
        },
        "leveling": {
            "status": False,
            "channel": None,
            "message": {
                "status": "CurrentChannel",
                "content": "Congrats, {user} You has reached level {level}"
            },
            "roleRewards": {
                "stacked": False,
                "roles": []
            },
            "leaderboard": {
                "public": False,
                "url": "",
                "banner": ""
            },
            "card": "blurple-rank.png",
            "economy": False,
            "auto_reset": True,
            "cooldown": 60,
            "max_level": 0,
            "noXP": [],
        },
        "verification": {
            "status": False,
            "channel": None,
            "role": None,
            "mode": "instant",  # instant | captcha_dm | captcha_channel | captcha_web
            "failAction": "unverified",  # unverified | kick | ban | timeout
            "message": {
                "embed": {
                    "title": "Verification",
                    "description": "To enter this server and see all channels, you must first prove that you are human. \nClick on the button below to start...",
                    "color": "#5865f2",
                    "author": {"name": ""},
                    "footer": {"text": ""},
                },
                "btn": {"emoji": "✅", "title": "Verify", "color": "green"},
            },
            "message_id": "",
            "message_published": False,
        },
        "starboard": {
            "status": False,
            "channel": None,
            "emoji": "⭐",
            "limit": "3",
            "jumpLink": True,
            "selfStar": False,
            "locked": False,
            "ignore": [],
            "allowNsfw": False,
            "embedNsfwImages": False,
            "autoStar": [],
        },
        "forms": {"status": False},
        "temporary_channels": {
            "status": False,
            "hubs": []
        },
        "ticketing": {
            "status": False,
            "panels": []
        },
        "birthdays": {
            "status": False,
            "channel_id": "",
            "message_hour": "0",
            "birthday_role": "",
            "message": "**Happy birthday, {user.mention}!** They are now {age} years old.",
        },
        "giveaways": {
        },
        "economy": {
            "status": False,
            "shop": [
                {"name": "Teddy", "price": 50, "icon": "🧸", "description": "Very soft cuddly teddy bear", "type": "string", "max_limit": 5},
                {"name": "Watch", "price": 100, "icon": "⌚", "description": "A thing to tell the time", "type": "string", "max_limit": 5},
                {"name": "Phone", "price": 500, "icon": "📱", "description": "A phone", "type": "string", "max_limit": 5},
                {"name": "Laptop", "price": 1000, "icon": "💻", "description": "A nice laptop for work and play", "type": "string", "max_limit": 5},
            ],
            "name": "BobCat Coin",
            "icon": "🪙",
            "MaxGambling": "250",
            "MaxPayment": "500",
        },
        "stats": {
            "status": False,
            "counters": []
        },
    }

async def init_database(guild: discord.Guild) -> bool:
    """Creates the Guild document for a new server. No-op if one already exists."""
    if await Guild.get(str(guild.id)) is not None:
        return False

    admin_roles = [str(role.id) for role in guild.roles if role.permissions.administrator]

    await Guild(
        id=str(guild.id),
        premium={"status": False},
        settings={
            "language": guild.preferred_locale,
            "timezone": "UTC",
            "color": "#5865f2",
            "admin_roles": admin_roles,
            "bot_masters": [],
            "moderator_roles": [],
        },
        dashboard=_default_dashboard(),
    ).insert()

    return True


def _deep_fill_gaps(existing: dict, defaults: dict) -> list[str]:
    """Recursively add any key present in `defaults` but missing from
    `existing` (mutates `existing` in place). Never touches a key that's
    already there, even if its value differs from the default - this is
    for backfilling schema drift (a plugin field added after the guild's
    doc was created), not resetting customization. Returns the dotted
    paths that were added, for logging."""
    added = []
    for key, value in defaults.items():
        if key not in existing:
            existing[key] = value
            added.append(key)
        elif isinstance(value, dict) and isinstance(existing.get(key), dict):
            added.extend(f"{key}.{path}" for path in _deep_fill_gaps(existing[key], value))
    return added


async def sync_guild_dashboard(guild: discord.Guild) -> None:
    """Runs on every on_ready (all guilds) and on_guild_join.

    If the guild has no doc yet, creates one with full defaults
    (init_database). If it already has one, backfills any dashboard keys
    missing from the *stored* document (e.g. a plugin field added to
    _default_dashboard() after this guild's doc was created) without
    touching anything already configured. Reads/writes the raw document
    directly - Guild.get() would silently paper over a missing key with
    its (safe-empty) model default rather than the real starter value,
    and never persist the fix back to Mongo.
    """
    collection = Guild.get_pymongo_collection()
    raw = await collection.find_one({"_id": str(guild.id)})

    if raw is None:
        await init_database(guild)
        return

    dash = raw.get("Dash", {})
    added = _deep_fill_gaps(dash, _default_dashboard())
    if added:
        await collection.update_one({"_id": str(guild.id)}, {"$set": {"Dash": dash}})
        print(f"Backfilled dashboard fields for guild {guild.id}: {', '.join(added)}")

async def sync_admin_roles(guild: discord.Guild) -> None:
    """Keeps settings.admin_roles in line with which roles actually
    have the Administrator permission right now."""
    doc = await Guild.get(str(guild.id))
    if doc is None:
        return

    doc.settings.admin_roles = [
        str(role.id) for role in guild.roles if role.permissions.administrator
    ]
    await doc.save()

class GuildEvents(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            await sync_guild_dashboard(guild)  # creates the doc if missing, else backfills gaps

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await sync_guild_dashboard(guild)

        channel = self.client.get_guild(v.btz_gid).get_channel(962696085787254814)
        await channel.send(f"<:enter:1110325436501737536> Joined {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        channel = self.client.get_guild(v.btz_gid).get_channel(962696085787254814)
        await channel.send(f"<:leave:1110325619511787680> Left {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        await sync_admin_roles(after)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.permissions.administrator == after.permissions.administrator:
            return
        await sync_admin_roles(after.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        await sync_admin_roles(role.guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        # Per-user data (leveling/economy/warnings) is created lazily on
        # first use by their own cogs — nothing to pre-populate here.
        if await Guild.get(str(member.guild.id)) is None:
            await init_database(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        doc = await Guild.get(str(member.guild.id))
        if doc is None:
            return

        if not doc.dashboard.leveling.auto_reset:
            return

        await LevelingModel.find(
            {"_id": f"{member.guild.id}_{member.id}"}
        ).delete()

def setup(client):
    client.add_cog(GuildEvents(client))
