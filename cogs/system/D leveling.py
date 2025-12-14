import time
import pymongo
import discord
import re
import random
from modules import bot as v
from discord.ext import commands
from easy_pil import Editor, Font, load_image
from cogs.money.tools.utils import open_account, update_bank

max_exp = 1000

class Leveling(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.cooldown = None

    def get_ratelimit(self, message: discord.Message):
        config = v.db.get_dash(message.guild)['leveling']
        cd = config.get('cooldown', 60)

        cooldown = commands.CooldownMapping.from_cooldown(1, cd, commands.BucketType.user)

        bucket = cooldown.get_bucket(message)
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
        status = lvl_data['status']
        chan = lvl_data['channel']
        anno = lvl_data["message"]["status"]
        mess: str = lvl_data["message"]["content"]
        auto_roles = lvl_data['roleRewards']
        maxLevel = lvl_data['max_level']
        economy = lvl_data['economy']
        noXP = lvl_data['noXP']

        if not status:
            return
        
        if self.get_ratelimit(message) is not None:
            return
        
        data: dict = v.db.get_server_config(message.guild)['leveling'].get(f'{message.author.id}')
        exp = data.get('exp')
        lvl = data.get('lvl')

        def replace_placeholder(match):
            key = match.group(1)
            if key == 'level':
                return f'{{{key}}}'
            if '.' in key:
                keys = key.split('.')
                obj = message.author if keys[0] == 'user' else message.guild
                for k in keys[1:]:
                    obj = obj.get(k, f'{{{k}}}')
                return str(obj)
            return str(message.author) if key == 'user' else str(message.guild.name)
        
        if noXP and str(message.channel.id) in noXP:
            return

        increase_exp = int(exp) + random.randint(1, 10)
        new_lvl = int(increase_exp / max_exp)

        if new_lvl >= maxLevel: # max level
            return
        if maxLevel == 0: # max level is set to 0, no max level
            pass
        
        v.db.update_server_config(message.guild, key=f"leveling.{message.author.id}.exp", value=increase_exp)

        if new_lvl > int(lvl):
            msg = re.sub(r'\{([\w.]+)\}', replace_placeholder, mess)
            
            if anno == "disabled":
                pass
            elif anno == "current":
                await message.channel.send(f"{msg}".format(server=message.guild, user=message.author, level=new_lvl
                ))
            elif anno == "dm":
                await message.author.send(f"{msg}".format(server=message.guild, user=message.author, level=new_lvl
                ))
            elif anno == "custom":
                try:
                    channel = self.client.get_channel(int(chan))
                    await channel.send(f"{msg}".format(server=message.guild, user=message.author, level=new_lvl))
                except AttributeError:
                    return
            
            v.db.update_server_config(message.guild, key=f"leveling.{message.author.id}", value={ "exp": 0, "lvl": new_lvl })
            
            if economy: # Economy integration
                await open_account(message.guild, message.author)
                await update_bank(message.guild, message.author, 'bank', 5)

            for role in auto_roles["roles"]:
                if new_lvl == role["level"]:
                    if auto_roles["stacked"] == False: # find the previous roles and remove them then add the new role
                        for r in auto_roles["roles"]:
                            r_id = message.guild.get_role(r["id"])
                            await message.author.remove_roles(r_id)
                        
                        roleID = message.guild.get_role(role["id"])
                        await message.author.add_roles(roleID)
                    
                    if auto_roles["stacked"] == True: # add the new role
                        roleID = message.guild.get_role(role["id"])
                        await message.author.add_roles(roleID)
            #
            return
    
    @commands.user_command(name="View Level")
    async def view_level(self, ctx, member: discord.Member):
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
        
        next_lvl_up = (lvl+1) * max_exp
        
        styles = level_card(ctx.guild)

        background = Editor(styles["background"])
        
        Profile = load_image(str(member.avatar.url))
        profile = Editor(Profile).resize((150, 150)).circle_image()
        background.paste(profile, (30, 30))
        background.text((200, 40), str(member), font=Font.poppins(size=40), color="#FFFFFF") # member usermame
        background.rectangle((200, 100), width=400, height=2, fill="#FFFFFF") # member profile underline
        background.text((200, 130), f"Level: {lvl}  XP: {exp} / {next_lvl_up}", color="white", font=Font.poppins(size=30),) # lvl & xp
        background.rectangle((styles["bar_indent_left"], 220), width=styles["bar_width"], height=40, fill=styles["bar_bg"], radius=20) # progress bar bg
        
        if exp != 0:
            _percentage = (exp / next_lvl_up) * 100
            percentage = max(0, min(_percentage, 100))

            background.bar( # progress bar inline
                (styles["bar_indent_left"], 220), 
                max_width=styles["bar_width"], height=42, percentage=percentage, fill=styles["bar_fill"], radius=20
            )
        
        await ctx.respond(file=discord.File(fp=background.image_bytes, filename=f"{member.id}_rank.png"), ephemeral=False)

    @commands.slash_command(description="Gives yours or member's ranks")
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
        
        next_lvl_up = (lvl+1) * max_exp
        
        styles = level_card(ctx.guild)

        background = Editor(styles["background"])
        
        Profile = load_image(str(member.avatar.url))
        profile = Editor(Profile).resize((150, 150)).circle_image()
        background.paste(profile, (30, 30))
        background.text((200, 40), str(member), font=Font.poppins(size=40), color="#FFFFFF") # member usermame
        background.rectangle((200, 100), width=400, height=2, fill="#FFFFFF") # member profile underline
        background.text((200, 130), f"Level: {lvl}  XP: {exp} / {next_lvl_up}", color="white", font=Font.poppins(size=30),) # lvl & xp
        background.rectangle((styles["bar_indent_left"], 220), width=styles["bar_width"], height=40, fill=styles["bar_bg"], radius=20) # progress bar bg
        
        if exp != 0:
            _percentage = (exp / next_lvl_up) * 100
            percentage = max(0, min(_percentage, 100))

            background.bar( # progress bar inline
                (styles["bar_indent_left"], 220), 
                max_width=styles["bar_width"], height=42, percentage=percentage, fill=styles["bar_fill"], radius=20
            )
        
        await ctx.respond(file=discord.File(fp=background.image_bytes, filename=f"{member.id}_rank.png"), ephemeral=False)
    
    @commands.slash_command(description=f"View the top 5 users in the server")
    async def leaderboard(self, ctx: discord.ApplicationContext):
        status = v.db.get_dash(ctx.guild)['leveling']['status']
        if not status:
            embed = discord.Embed(description="Levelling is disabled", color=v.error)
            return await ctx.respond(embed=embed, ephemeral=True)
        
        lvl_users = v.db.get_server_config(ctx.guild)['leveling']
        sorted_players = sorted(lvl_users.items(), key=lambda x: int(x[1]['lvl']), reverse=True)[:5]
        
        desc = ""
        for idx, (u_id, data) in enumerate(sorted_players, start=1):
            member = await v.client.fetch_user(u_id)
            desc += f"#{idx} ● {member.name} ● LVL: {data['lvl']}\n"
        
        embed = discord.Embed(title=f"{ctx.guild.name}'s Leaderboard", description=desc, color=0xffffff)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="View Leaderboard", url=f"{v.web_url}/leaderboard/{ctx.guild.id}"))
        await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(Leveling(client))

def level_card(guild: discord.Guild):
    URL = "databases/lvl-cards"
    theme = v.db.get_dash(guild)['leveling']['card']
    
    mongoRankCards = pymongo.MongoClient(v.config['mongoURI_cdn'])['RankCards']['Cards']
    
    default_cards = [
        card
        for card in mongoRankCards.find({"theme": "default"}).sort("theme", pymongo.ASCENDING)
    ]
    fun_cards = [
        card
        for card in mongoRankCards.find({"theme": "bobcat"}).sort("theme", pymongo.ASCENDING)
    ]
    all_cards = default_cards + fun_cards

    for file in all_cards:
        if theme == file['card']:
            style = {
                "background": f"{URL}/{file['card']}",
                "bar_bg": file["bar_bg"],
                "bar_fill": file["bar_fill"],
                "bar_indent_left": int(file["bar_indent_left"]),
                "bar_width": int(file["bar_width"])
            }
            break
    
    return style