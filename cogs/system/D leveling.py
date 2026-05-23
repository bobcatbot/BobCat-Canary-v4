import pymongo
import discord
import re
import random
from modules import bot as v
from discord.ext import commands
from easy_pil import Editor, Font, load_image
from cogs.money.tools.utils import open_account, update_bank
 
CARDS_URL = "databases/lvl-cards"
FALLBACK_CARD = "blurple-rank.png"
 
mongo_cdn_client = pymongo.MongoClient(v.mongo_cdn)
mongoRankCards = mongo_cdn_client['RankCards']['Cards']
 
 
def xp_for_level(lvl: int) -> int:
    """XP required to complete a given level (scales with level)."""
    return 5 * (lvl ** 2) + 50 * lvl + 100
 
 
def calculate_level(total_exp: int) -> tuple[int, int]:
    """
    Given total accumulated XP, returns (current_level, leftover_exp).
    """
    lvl = 0
    while total_exp >= xp_for_level(lvl):
        total_exp -= xp_for_level(lvl)
        lvl += 1
    return lvl, total_exp
 
 
def level_card(guild: discord.Guild) -> dict | None:
    theme = v.db.get_dash(guild)['leveling']['card']
    file = mongoRankCards.find_one({"card": theme}) or mongoRankCards.find_one({"card": FALLBACK_CARD})
    if not file:
        return None
    return {
        **file,
        "background": f"{CARDS_URL}/{file['card']}",
    }

class Leveling(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        # CooldownMapping is created once per cog instance, not per message
        self._cooldown_cache: dict[int, commands.CooldownMapping] = {}
 
    def _get_cooldown(self, guild_id: int, cd: int) -> commands.CooldownMapping:
        """Returns a stable CooldownMapping per guild, recreating only if the cooldown value changes."""
        existing = self._cooldown_cache.get(guild_id)
        if existing is None:
            mapping = commands.CooldownMapping.from_cooldown(1, cd, commands.BucketType.user)
            self._cooldown_cache[guild_id] = mapping
            return mapping
        return existing
 
    def get_ratelimit(self, message: discord.Message) -> float | None:
        config = v.db.get_dash(message.guild.id)['leveling']
        cd = config.get('cooldown', 60)
        mapping = self._get_cooldown(message.guild.id, cd)
        bucket = mapping.get_bucket(message)
        return bucket.update_rate_limit()
 
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if message.channel.type == discord.ChannelType.private:
            return
 
        lvl_data = v.db.get_dash(message.guild)['leveling']
 
        if not lvl_data.get('status'):
            return
 
        # No XP channels
        noXP: list = lvl_data.get('noXP', [])
        if noXP and str(message.channel.id) in noXP:
            return
 
        if self.get_ratelimit(message) is not None:
            return
 
        # Fetch user data — initialize if missing
        server_config = v.db.get_server_config(message.guild)
        data: dict | None = server_config['leveling'].get(str(message.author.id))
        if data is None:
            data = {'exp': 0, 'lvl': 0}
            v.db.update_server_config(
                message.guild,
                key=f"leveling.{message.author.id}",
                value=data
            )
 
        exp: int = int(data.get('exp', 0))
        lvl: int = int(data.get('lvl', 0))
        maxLevel: int = int(lvl_data.get('max_level', 0))
 
        # Don't give XP if already at max level
        if maxLevel != 0 and lvl >= maxLevel:
            return
 
        gained = random.randint(1, 10)
        new_exp = exp + gained
        new_lvl, leftover_exp = calculate_level(
            sum(xp_for_level(i) for i in range(lvl)) + new_exp
        )
 
        # Cap at max level
        if maxLevel != 0 and new_lvl >= maxLevel:
            new_lvl = maxLevel
            leftover_exp = 0
 
        leveled_up = new_lvl > lvl
 
        # Write new exp/level in one update
        v.db.update_server_config(
            message.guild,
            key=f"leveling.{message.author.id}",
            value={'exp': leftover_exp, 'lvl': new_lvl}
        )
 
        if not leveled_up:
            return
 
        # ── Level-up announcement ──────────────────────────────────────────
        anno: str = lvl_data["message"]["status"]
        mess: str = lvl_data["message"]["content"]
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
        if lvl_data.get('economy'):
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
                if roles_to_remove:
                    await message.author.remove_roles(*roles_to_remove)
 
            await message.author.add_roles(role)

    # ── Slash commands ─────────────────────────────────────────────────────
    
    @commands.slash_command(description="Gives yours or member's ranks", guild_ids=v.guild_ids)
    @discord.option("member", discord.Member, description="Select a member", required=False)
    async def rank(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        status = v.db.get_dash(ctx.guild)['leveling']['status']
        if not status:
            embed = discord.Embed(description="Levelling is disabled", color=v.error)
            return await ctx.respond(embed=embed, ephemeral=True)
        
        member = ctx.author if not member else member
        
        if member.bot:
            return await ctx.respond(f"{member.mention} is a bot! So they have no rank")
        
        data: dict = v.db.get_server_config(ctx.guild)['leveling'].get(f'{member.id}')
        exp = data.get('exp')
        lvl = data.get('lvl')
        
        if data is None:
            return await ctx.respond(f"**{member.display_name}** has no rank. Keep chatting to earn a rank!")
        if lvl == 0 and exp == 0:
            return await ctx.respond(f"**{member.display_name}** has no rank. Keep chatting to earn a rank!")
        
        next_lvl_xp = xp_for_level(lvl)
        
        styles = level_card(ctx.guild)

        background = Editor(styles["background"])
        
        Profile = load_image(str(member.avatar.url))
        profile = Editor(Profile).resize((150, 150)).circle_image()
        background.paste(profile, (30, 30))
        background.text((200, 40), str(member), font=Font.poppins(size=40), color="#FFFFFF") # member usermame
        background.rectangle((200, 100), width=400, height=2, fill="#FFFFFF") # member profile underline
        background.text((200, 130), f"Level: {lvl}  XP: {exp} / {next_lvl_xp}", color="white", font=Font.poppins(size=30),) # lvl & xp
        background.rectangle((styles["bar_indent_left"], 220), width=styles["bar_width"], height=40, fill=styles["bar_bg"], radius=20) # progress bar bg
        
        if exp > 0:
            percentage = max(0.0, min((exp / next_lvl_xp) * 100, 100.0))

            background.bar( # progress bar inline
                (styles["bar_indent_left"], 220), 
                max_width=styles["bar_width"], 
                fill=styles["bar_fill"],
                percentage=percentage, 
                height=42, 
                radius=20
            )
        
        await ctx.respond(file=discord.File(fp=background.image_bytes, filename=f"{member.id}_rank.png"), ephemeral=False)

    @commands.slash_command(description=f"View the top 5 users in the server")
    async def leaderboard(self, ctx: discord.ApplicationContext):
        lvl_data = v.db.get_dash(ctx.guild)['leveling']
        if not lvl_data.get('status'):
            return await ctx.respond(
                embed=discord.Embed(description="Levelling is disabled", color=v.error),
                ephemeral=True
            )
 
        lvl_users: dict = v.db.get_server_config(ctx.guild)['leveling']
        sorted_players = sorted(
            lvl_users.items(),
            key=lambda x: (int(x[1].get('lvl', 0)), int(x[1].get('exp', 0))),
            reverse=True
        )[:5]
 
        desc = ""
        for idx, (u_id, data) in enumerate(sorted_players, start=1):
            member = await v.client.fetch_user(int(u_id))
            desc += f"#{idx} ● {member.name} ● LVL: {data['lvl']}\n"
 
        embed = discord.Embed(
            title=f"{ctx.guild.name}'s Leaderboard",
            description=desc,
            color=0xffffff
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="View Leaderboard",
            url=f"{v.web_url}/leaderboard/{ctx.guild.id}"
        ))
        await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(Leveling(client))

def level_card(guild: discord.Guild) -> dict | None:
    theme = v.db.get_dash(guild)['leveling']['card']

    file = mongoRankCards.find_one({"card": {"$in": [theme, FALLBACK_CARD]}})
    if not file:
        return None  # or a default style

    return {
        **file,
        "background": f"{CARDS_URL}/{file['card']}",
    }