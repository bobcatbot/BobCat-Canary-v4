import discord
from modules import bot as v
from discord.ext import commands

def init_database(guild: discord.Guild):
    warn_users = {}
    lvl_users = {}
    eco_users = {}
    
    for member in guild.members:
        if member.bot:
            continue
        
        warn_users[f"{member.id}"] = []
        
        lvl_users[f"{member.id}"] = {}
        lvl_users[f"{member.id}"]["exp"] = 0
        lvl_users[f"{member.id}"]["lvl"] = 0

        eco_users[f"{member.id}"] = {}
        eco_users[f"{member.id}"]["wallet"] = 0
        eco_users[f"{member.id}"]["bank"] = 0
        eco_users[f"{member.id}"]["bag"] = []

    guild_data = {
        "moderation": {
            "warnings": warn_users
        },
        "economy": eco_users,
        "leveling": lvl_users,
        'starboards': [],
        'suggestions': [],
        'giveaways': [],
        'forms': [],
        'tickets': [],
        'temporary_channels': [],
        'birthdays': {},
    }
    
    dashboard_data = {
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
            'autoRoles': {
                'status': False,
                'roles': []
            }
        },
        "moderation": {
            'status': False,
            'automod': {
                'Timeout': { 'enabled': False },
                'ServerInvites': { 'enabled': False },
                'Externallinks': { 'enabled': False },
                'GhostPing': { 'enabled': False },
            },
            'settings': { # ['server', 'action', 'mod', 'reason']
                'kick': { 'dm': [] },
                'ban':  { 'dm': [], 'deleteMessageDays': '0' },
                'mute': { 'dm': [], 'type': 'timeout', 'duration': '60-sec'},
                'warn': { 'dm': [] }
            },
            'logging': {
                "channel": None,
                "bots": False,
                "events": {
                    'ModerationKick': False, 'ModerationBan': False, 'ModerationUnban': False, 'ModerationMute': False, 'ModerationUnmute': False, 'ModerationWarn': False,
                    'ModerationUnwarn': False,
                    'Verification': False,
                    'MemberJoin': False, 'MemberLeave': False, 'MemberUpdate': False, 'MemberBan': False, 'MemberUnban': False, 
                    'MessageDelete': False, 'MessageEdit': False, 
                    'ServerUpdate': False, 'ServerInviteCreate': False, 'ServerInviteDelete': False, 'ServerEmojis': False, 
                    'ChannelCreate': False, 'ChannelDelete': False, 'ChannelUpdate': False, 
                    'RoleCreate': False, 'RoleDelete': False, 'RoleUpdate': False, 
                }
            }
        },
        "leveling": {
            'status': False,
            'channel': None,
            'message': {
                'status': 'CurrentChannel', 
                'content': 'Congrats, {user} You has reached level {level}'
            },
            'roleRewards': {
                "stacked": False,
                "roles": []
            },
            'leaderboard': {
                'public': False,
                'url': '',
                'banner': ''
            },
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
                {"name": "Teddy", "price": 50, "icon": "🧸", "description": "Very sot cuddly teddy bear", "type": "string", "max_limit": 5},
                {"name": "Watch", "price": 100, "icon": "⌚", "description": "A thing to tell the time", "type": "string", "max_limit": 5},
                {"name": "Phone", "price": 500, "icon": "📱", "description": "A phone", "type": "string", "max_limit": 5},
                {"name": "Laptop", "price": 1000, "icon": "💻", "description": "A nice laptop for work and play", "type": "string", "max_limit": 5},
            ],
            'name': 'BobCat Coin',
            'icon': '🪙',
            'MaxGambling': '250',
            'MaxPayment': '500'
        },
        "starboard": {
            'status': False,
            'channel': None,
            'emoji': '⭐',
            'limit': '3',
            'jumpLink': True,
            'selfStar': False,
            'locked': False,
            'ignore': []
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
                    "author": {
                        "name": ""
                    },
                    "footer": {
                        "text": ""
                    }
                },
                "btn": {
                    "emoji": "\u2705",
                    "title": "Verify",
                    "color": "green"
                }
            },
            "message_id": "",
            "message_published": False
        },
        "giveaway": {
            'status': False,
        },
        "forms": {
            'status': False,
        },
        "ticketing": {
            'status': False,
            'panels': []
        },
        "temporary_channels": {
            'status': False,
            'hubs': []
        },
        "birthdays": {
            "status": False,
            "channel_id": "",
            "message_hour": "0",
            "birthday_role": "",
            "message": "**Happy birthday, {user.mention}!** They are now {age} years old."
        }
    }

    admin_roles = [str(role.id) for role in guild.roles if role.permissions.administrator]

    config = {
        "_id": f'{guild.id}',
        "premium": {
            "status": False,
        },
        "settings": {
            'language': guild.preferred_locale,
            'timezone': "UTC",
            'color': "#5865f2",
            "admin_roles": admin_roles,
            "bot_masters": [],
            "moderator_roles": [], 
        },
        "notifications": [],
        "Bot": guild_data,
        "Dash": dashboard_data
    }
    v.db.create_server_config(config)
    return True

class GuildEvents(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        # Ensure all guilds are initialized
        for guild in self.client.guilds:
            if not v.db.get_server_config(guild):
                init_database(guild)
    
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
        guild = after

        admin_roles = [
            str(role.id)
            for role in guild.roles
            if role.permissions.administrator
        ]
        v.db.update_server_config(after, key="settings.admin_roles", value=admin_roles)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild
        uid = str(member.id)

        data = v.db.get_server_config(guild)
        if not data:
            init_database(guild)
            data = v.db.get_server_config(guild)

        data["moderation"]["warnings"][uid] = []
        data["leveling"][uid] = {"exp": 0, "lvl": 0}
        data["economy"][uid] = {"wallet": 0, "bank": 0, "bag": []}

        # Single atomic write
        v.db.update_server_config(guild, key="Bot", value=data)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild
        user_id = str(member.id)

        dash = v.db.get_dash(guild.id)
        if not dash.get("leveling", {}).get("auto_reset"):
            return

        config = v.db.get_server_config(guild)
        leveling_data = config.get("leveling", {})

        removed = leveling_data.pop(user_id, None)
        if removed is None:
            return
        
        v.db.update_server_config(guild, key="leveling", value=leveling_data)

def setup(client):
    client.add_cog(GuildEvents(client))