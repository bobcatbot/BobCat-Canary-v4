import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild, Leveling as LevelingModel

def _default_dashboard() -> dict:
    """Default `dashboard` (Dash) config for a brand new guild.
    Keys here must match DashConfig's fields in models.py exactly."""
    return {
        "welcome": {
            'status': False,
            'join': {
                'status': False,
                'channel': None,
                'message': {'type': 'text', 'content': 'Hey {user}, welcome to **{server}**!'},
            },
            'dm': {
                'status': False,
                'message': {'type': 'text', 'content': 'Have a great time here in **{server}**'},
            },
            'leave': {
                'status': False,
                'channel': None,
                'message': {'type': 'text', 'content': '**{user}** just left the server. Bye!'},
            },
            'autoRoles': {'status': False, 'roles': []},
        },
        "moderation": {
            'status': False,
            'automod': {
                'Timeout': {'enabled': False},
                'ServerInvites': {'enabled': False},
                'Externallinks': {'enabled': False},
                'GhostPing': {'enabled': False},
            },
            'settings': {
                'kick': {'dm': []},
                'ban': {'dm': [], 'deleteMessageDays': '0'},
                'mute': {'dm': [], 'type': 'timeout', 'duration': '60-sec'},
                'warn': {'dm': []},
            },
            'logging': {
                "channel": None,
                "bots": False,
                "events": {
                    'ModerationKick': False, 'ModerationBan': False, 'ModerationUnban': False,
                    'ModerationMute': False, 'ModerationUnmute': False, 'ModerationWarn': False,
                    'ModerationUnwarn': False,
                    'Verification': False,
                    'MemberJoin': False, 'MemberLeave': False, 'MemberUpdate': False,
                    'MemberBan': False, 'MemberUnban': False,
                    'MessageDelete': False, 'MessageEdit': False,
                    'ServerUpdate': False, 'ServerInviteCreate': False, 'ServerInviteDelete': False,
                    'ServerEmojis': False,
                    'ChannelCreate': False, 'ChannelDelete': False, 'ChannelUpdate': False,
                    'RoleCreate': False, 'RoleDelete': False, 'RoleUpdate': False,
                },
            },
        },
        "leveling": {
            'status': False,
            'channel': None,
            'message': {'status': 'CurrentChannel', 'content': 'Congrats, {user} You has reached level {level}'},
            'roleRewards': {"stacked": False, "roles": []},
            'leaderboard': {'public': False, 'url': '', 'banner': ''},
            'card': 'blurple-rank.png',
            'economy': False,
            'auto_reset': True,
            'cooldown': 60,
            'max_level': 0,
            'noXP': [],
        },
        "economy": {
            'status': False,
            'shop': [
                {"name": "Teddy", "price": 50, "icon": "🧸", "description": "Very soft cuddly teddy bear", "type": "string", "max_limit": 5},
                {"name": "Watch", "price": 100, "icon": "⌚", "description": "A thing to tell the time", "type": "string", "max_limit": 5},
                {"name": "Phone", "price": 500, "icon": "📱", "description": "A phone", "type": "string", "max_limit": 5},
                {"name": "Laptop", "price": 1000, "icon": "💻", "description": "A nice laptop for work and play", "type": "string", "max_limit": 5},
            ],
            'name': 'BobCat Coin',
            'icon': '🪙',
            'MaxGambling': '250',
            'MaxPayment': '500',
        },
        "starboard": {
            'status': False,
            'channel': None,
            'emoji': '⭐',
            'limit': '3',
            'jumpLink': True,
            'selfStar': False,
            'locked': False,
            'ignore': [],
        },
        "verification": {
            'status': False,
            'channel': None,
            'role': None,
            'mode': 'instant',
            'failAction': 'unverified',
            "message": {
                "embed": {
                    "title": "Verification",
                    "desc": "To enter this server and see all channels, you must first prove that you are human. \nClick on the button below to start...",
                    "color": "#5865f2",
                    "author": {"name": ""},
                    "footer": {"text": ""},
                },
                "btn": {"emoji": "\u2705", "title": "Verify", "color": "green"},
            },
            "message_id": "",
            "message_published": False,
        },
        "ticketing": {'status': False, 'panels': []},
        "temporary_channels": {'status': False, 'hubs': []},
        "birthdays": {
            "status": False,
            "channel_id": "",
            "message_hour": "0",
            "birthday_role": "",
            "message": "**Happy birthday, {user.mention}!** They are now {age} years old.",
        },
    }

def init_database(guild: discord.Guild) -> bool:
    """Creates the Guild document for a new server. No-op if one already exists."""
    if Guild.get(str(guild.id)).run() is not None:
        return False

    admin_roles = [str(role.id) for role in guild.roles if role.permissions.administrator]

    Guild(
        id=str(guild.id),
        premium={"status": False},
        settings={
            'language': guild.preferred_locale,
            'timezone': "UTC",
            'color': "#5865f2",
            "admin_roles": admin_roles,
            "bot_masters": [],
            "moderator_roles": [],
        },
        dashboard=_default_dashboard(),
    ).insert()

    return True

def sync_admin_roles(guild: discord.Guild) -> None:
    """Keeps settings.admin_roles in line with which roles actually
    have the Administrator permission right now."""
    doc = Guild.get(str(guild.id)).run()
    if doc is None:
        return

    doc.settings["admin_roles"] = [
        str(role.id) for role in guild.roles if role.permissions.administrator
    ]
    doc.save()

class GuildEvents(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            init_database(guild)  # no-op if the guild already has a doc

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        init_database(guild)

        channel = self.client.get_guild(v.btz_gid).get_channel(962696085787254814)
        await channel.send(f"<:enter:1110325436501737536> Joined {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        channel = self.client.get_guild(v.btz_gid).get_channel(962696085787254814)
        await channel.send(f"<:leave:1110325619511787680> Left {guild.name} ({guild.id})")

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        sync_admin_roles(after)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        if before.permissions.administrator == after.permissions.administrator:
            return
        sync_admin_roles(after.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        sync_admin_roles(role.guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        # Per-user data (leveling/economy/warnings) is created lazily on
        # first use by their own cogs — nothing to pre-populate here.
        if Guild.get(str(member.guild.id)).run() is None:
            init_database(member.guild)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        doc = Guild.get(str(member.guild.id)).run()
        if doc is None:
            return

        if not doc.dashboard.leveling.get("auto_reset"):
            return

        lvl = LevelingModel.get(f"{member.guild.id}_{member.id}").run()
        if lvl is not None:
            lvl.delete()

def setup(client):
    client.add_cog(GuildEvents(client))