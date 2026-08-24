import re
import io
import random
from typing import List
import aiohttp
import pymongo
import discord
import asyncio
from discord.ext import commands
from easy_pil import Editor, Font, load_image
from modules import bot as v
from modules.models import Guild, Leveling as LevelingModel
from cogs.money.tools.utils import open_account, update_bank

CARDS_URL = "images/lvl-cards"
FALLBACK_CARD = "blurple-rank.png"

mongo_cdn_client = pymongo.MongoClient(v.mongo_cdn)
mongoRankCards = mongo_cdn_client['RankCards']['Cards']

# In-Memory Cache for Rank Cards to prevent blocking MongoDB queries on every command
CARD_CACHE: dict[str, dict] = {}

def xp_for_level(lvl: int) -> int:
    """XP required to complete a given level (scales with level)."""
    return 5 * (lvl ** 2) + 50 * lvl + 100

def get_level_card_config(configured_card: str) -> dict:
    if configured_card in CARD_CACHE:
        return CARD_CACHE[configured_card]

    document = mongoRankCards.find_one({"card": configured_card})

    if document is None:
        document = mongoRankCards.find_one({"card": FALLBACK_CARD})

    card_data = {
        **document,
        "background": f"{CARDS_URL}/{document['card']}",
    }

    CARD_CACHE[configured_card] = card_data
    return card_data

class Leveling(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self._cooldown_cache: dict[int, commands.CooldownMapping] = {}
        
        self.XP_PER_MESSAGE_MIN = 1
        self.XP_PER_MESSAGE_MAX = 10
 
    def _get_cooldown(self, guild_id: int, cd: int) -> commands.CooldownMapping:
        existing = self._cooldown_cache.get(guild_id)
        if existing is None or existing._cooldown.per != cd:
            mapping = commands.CooldownMapping.from_cooldown(1, cd, commands.BucketType.user)
            self._cooldown_cache[guild_id] = mapping
            return mapping
        return existing
 
    def get_ratelimit(self, message: discord.Message) -> float | None:
        config = Guild.get(str(message.guild.id)).run().dashboard.leveling
        cd = config.get('cooldown', 60)
        mapping = self._get_cooldown(message.guild.id, cd)
        bucket = mapping.get_bucket(message)
        return bucket.update_rate_limit()
 
    def render_rank_card_sync(
        self,
        avatar_bytes: bytes, 
        member_name: str, 
        lvl: int, 
        exp: int, 
        next_lvl_xp: int, 
        card_cfg: dict
    ) -> io.BytesIO:
        """CPU-bound PIL operations run in a thread pool."""
        background = Editor(card_cfg["background"])
        
        # Avatar rendering - now receiving bytes directly
        _profile = load_image(avatar_bytes)
        profile = Editor(_profile).resize((150, 150)).circle_image()
        background.paste(profile, (30, 30))

        # Member rendering
        background.text((200, 40), member_name, font=Font.poppins(size=40), color="#FFFFFF")
        background.rectangle((200, 100), width=400, height=2, fill="#FFFFFF")
        background.text((200, 130), f"Level: {lvl}  XP: {exp} / {next_lvl_xp}", color="#FFFFFF", font=Font.poppins(size=30))
        
        # Progress Bar rendering
        bar_y = 220
        bar_h = 40
        indent = card_cfg["bar_indent_left"]
        width = card_cfg["bar_width"]
        
        background.rectangle((indent, bar_y), width=width, height=bar_h, fill=card_cfg["bar_bg"], radius=20)

        if exp > 0 and next_lvl_xp > 0:
            percentage = max(0.0, min((exp / next_lvl_xp) * 100, 100.0))
            background.bar(
                (indent, bar_y),
                max_width=width,
                fill=card_cfg["bar_fill"],
                percentage=percentage,
                height=bar_h + 2,
                radius=20,
            )
            
        return background.image_bytes
 
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.channel.type == discord.ChannelType.private:
            return
 
        # Fetch guild config
        guild_doc = Guild.get(str(message.guild.id)).run()
        if guild_doc is None:
            return
            
        lvl_data = guild_doc.dashboard.leveling
 
        if not lvl_data.get('status', False):
            return
 
        # No XP channels
        noXP: List[str] = lvl_data.get('noXP', [])
        if noXP and str(message.channel.id) in noXP:
            return
 
        if self.get_ratelimit(message) is not None:
            return
 
        # Fetch user data — initialize if missing
        data = LevelingModel.get(f"{message.guild.id}_{message.author.id}").run()
        if data is None:
            data = LevelingModel(
                id=f"{message.guild.id}_{message.author.id}",
                guild_id=str(message.guild.id),
                user_id=str(message.author.id),
            )
            data.insert()

        exp: int = int(data.exp)
        lvl: int = int(data.lvl)
        maxLevel: int = int(lvl_data.get('max_level', 0))
 
        # Don't give XP if already at max level (0 = no limit)
        if maxLevel != 0 and lvl >= maxLevel:
            return
 
        gained = random.randint(self.XP_PER_MESSAGE_MIN, self.XP_PER_MESSAGE_MAX)
        
        new_exp = exp + gained
        new_lvl = lvl
        while new_exp >= xp_for_level(new_lvl):
            new_exp -= xp_for_level(new_lvl)
            new_lvl += 1
        leftover_exp = new_exp
 
        # Cap at max level
        if maxLevel != 0 and new_lvl >= maxLevel:
            new_lvl = maxLevel
            leftover_exp = 0
 
        leveled_up = new_lvl > lvl
 
        # Write new exp/level in one update
        data.exp = leftover_exp
        data.lvl = new_lvl
        data.save()
 
        if not leveled_up:
            return
 
        # ── Level-up announcement ──────────────────────────────────────────
        message_config = lvl_data.get('message', {})
        anno: str = message_config.get('status', 'current')
        mess: str = message_config.get('content', '{user} just reached level {level}!')
        chan = lvl_data.get('channel')
 
        def replace_placeholder(match: re.Match) -> str:
            key = match.group(1)
            if key == 'level':
                return str(new_lvl)
            if '.' in key:
                parts = key.split('.')
                obj = message.author if parts[0] == 'user' else message.guild
                for k in parts[1:]:
                    obj = getattr(obj, k, f'{{{k}}}')
                return str(obj)
            if key == 'user':
                return str(message.author)
            return str(message.guild.name)
 
        formatted = re.sub(r'\{([\w.]+)\}', replace_placeholder, mess)
        msg_text = formatted.format(server=message.guild, user=message.author, level=new_lvl)
 
        if anno == "current":
            await message.channel.send(msg_text)
        elif anno == "dm":
            await message.author.send(msg_text)
        elif anno == "custom" and chan:
            channel = self.client.get_channel(int(chan))
            if channel:
                await channel.send(msg_text)
 
        # ── Economy integration ────────────────────────────────────────────
        if lvl_data.get('economy', False):
            await open_account(message.guild, message.author)
            await update_bank(message.guild, message.author, 'bank', 5)
 
        # ── Role rewards ───────────────────────────────────────────────────
        auto_roles: dict = lvl_data.get('roleRewards', {})
        stacked: bool = auto_roles.get('stacked', False)
 
        for reward in auto_roles.get('roles', []):
            if new_lvl != int(reward['level']):
                continue
 
            role_id = int(reward['id'])
            role = message.guild.get_role(role_id)
            if role is None:
                continue
 
            if not stacked:
                # Remove all other reward roles first
                roles_to_remove = [
                    message.guild.get_role(int(r['id']))
                    for r in auto_roles['roles']
                    if message.guild.get_role(int(r['id'])) in message.author.roles
                ]
                roles_to_remove = [r for r in roles_to_remove if r is not None]
                if roles_to_remove:
                    await message.author.remove_roles(*roles_to_remove)
 
            await message.author.add_roles(role)

    # ── Slash commands ─────────────────────────────────────────────────────
    @commands.slash_command(description="Gives yours or member's ranks")
    @discord.option("member", discord.Member, description="Select a member", required=False)
    async def rank(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        guild_doc = Guild.get(str(ctx.guild.id)).run()
        if guild_doc is None:
            return await ctx.respond("❌ Guild not found!", ephemeral=True)
            
        lvl_data = guild_doc.dashboard.leveling
        status = lvl_data.get('status', False)
        if not status:
            embed = discord.Embed(description="Leveling is disabled", color=v.error)
            return await ctx.respond(embed=embed, ephemeral=True)
        
        member = ctx.author if not member else member
        if member.bot:
            return await ctx.respond(f"{member.mention} is a bot! So they have no rank")
        
        data = LevelingModel.get(f"{ctx.guild.id}_{member.id}").run()
        if data is None or (data.lvl == 0 and data.exp == 0):
            return await ctx.respond(f"**{member.display_name}** has no rank. Keep chatting to earn a rank!")
        
        exp = data.exp
        lvl = data.lvl
        next_lvl_xp = xp_for_level(lvl)
        
        configured_card = lvl_data.get('card', FALLBACK_CARD)
        card_cfg = get_level_card_config(configured_card)

        # ── FIX: Download avatar as bytes ──────────────────────────────────
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(member.avatar.url) as resp:
                    if resp.status != 200:
                        # Fallback to default avatar
                        avatar_bytes = await member.default_avatar.read()
                    else:
                        avatar_bytes = await resp.read()
        except Exception:
            # Fallback to default avatar on any error
            avatar_bytes = await member.default_avatar.read()

        # Execute heavy PIL rendering inside a thread to avoid blocking the asyncio event loop
        img_bytes = await asyncio.to_thread(
            self.render_rank_card_sync,
            avatar_bytes,  # ✅ Now passing bytes!
            str(member),
            lvl,
            exp,
            next_lvl_xp,
            card_cfg
        )
        
        file = discord.File(fp=img_bytes, filename=f"{member.id}_rank.png")
        await ctx.respond(file=file)

    @commands.slash_command(description="View the top 5 users in the server")
    async def leaderboard(self, ctx: discord.ApplicationContext):
        guild_doc = Guild.get(str(ctx.guild.id)).run()
        if guild_doc is None:
            return await ctx.respond("❌ Guild not found!", ephemeral=True)
            
        lvl_data = guild_doc.dashboard.leveling
        if not lvl_data.get('status', False):
            return await ctx.respond(
                embed=discord.Embed(description="Leveling is disabled", color=v.error),
                ephemeral=True
            )
 
        lvl_users = LevelingModel.find(LevelingModel.guild_id == str(ctx.guild.id)).run()
        sorted_players = sorted(
            lvl_users,
            key=lambda user: (int(user.lvl), int(user.exp)),
            reverse=True
        )[:5]

        desc = ""
        for idx, data in enumerate(sorted_players, start=1):
            member = ctx.guild.get_member(int(data.user_id)) or await v.client.fetch_user(int(data.user_id))
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
            desc += f"{medal} ● {member.display_name} ● LVL: {data.lvl}\n"
 
        embed = discord.Embed(
            title=f"🏆 {ctx.guild.name}'s Leaderboard",
            description=desc if desc else "No users ranked yet!",
            color=0xffffff
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="View Full Leaderboard",
            url=f"{v.web_url}/leaderboard/{ctx.guild.id}"
        ))
        await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(Leveling(client))