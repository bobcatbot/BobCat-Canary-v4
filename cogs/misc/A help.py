import discord
import platform
import psutil
from modules import bot as v
from discord.ext import commands

class BackBtn(discord.ui.Button):
    def __init__(self, client, row = 1):
        super().__init__(
            label="Return",
            style=discord.ButtonStyle.blurple,
            row=row
        )
        self.client = client
    async def callback(self, interaction: discord.Interaction):
        em=discord.Embed(
            color=v.style(interaction.guild.id),
            title="BobCat Help Menu",
            description=(
                "Thanks for using **BobCat**"
                "\n**BobCat Prefix:** `b!`"
                "\nBobcat is a simple to use bot. It has functions such as entertainment, moderation, administration, and so much more."
            )
        ) 
        em.set_thumbnail(url=self.client.user.avatar.url)
        await interaction.response.edit_message(content=None, embed=em, view=DropdownView(self.client, interaction.guild.id))
        
class Dropdown(discord.ui.Select):
    def __init__(self, client, g):
        self.client = client

        options = [
            discord.SelectOption(label="Commands", description="All of bobcats commands"),
            discord.SelectOption(label="Games", description="All of bobcats game commands"),
        ]
        
        data = v.db.get_dash(g)
        
        if data["moderation"]["status"]:
            options.append(discord.SelectOption(label="Mod", description="All of bobcats moderation commands"))
        if data["leveling"]["status"]:
            options.append(discord.SelectOption(label="Leveling", description="All of bobcats leveling commands"))
        if data["economy"]["status"]:
            options.append(discord.SelectOption(label="Economy", description="All of bobcats economy commands"))
                
        super().__init__(
            placeholder="Browse Categories",
            options=options,
            min_values=1,
            max_values=1,
            disabled=False,
            custom_id="menu"
        )
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Commands":
            commands = [
                "</help:1172159047357710344> - The command you used to get here!",
                "</invite:1172245165407223839> - Invite BobCat to your server",
                "</afk:1172159047357710342> - Sets your status to AFK",
                "</user:1210273601572442152> - Get information about a user",
                "</server:1210273601572442155> - Get information about a server",
            ]

            em = discord.Embed(title="BobCat General Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Commands', url="https://docs.bobcatbot.xyz/commands"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)
    
        if self.values[0] == "Games":
            commands = [
                "/games - Shows all of bobcats game commands",
                "</8ball:1172159047525466149> - Ask a question to the magic 8ball",
                "</coinflip:1172159047525466144> - Flips a coin",
                "</diceroll:1172159047525466148> - Rolls a 6 sided dice",
                "</guess:1172159047525466145> - Guess the random number between 1 and 10",
                "</rps:1172159047525466147> - Play rock, paper, scissors against your opponent",
                "</tictactoe:1172159047525466150> - Play tic-tac-toe",
            ]

            em = discord.Embed(title="BobCat Game Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Games', url="https://docs.bobcatbot.xyz/commands/games"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

        if self.values[0] == "Mod":
            commands = [
                "</clear:1210273600150442027> - Clears messages",
                "</kick:1172159046787268680> - Kicks a user",
                "</ban:1172202464590700636> - Bans a user",
                "</unban:1172159046787268685> - Unbans a user",
                f"{self.client.command_prefix}massban - Bans multiple users at once",
                "</mute:1210273600150442024> - Mutes a user",
                "</unmute:1210273600150442025> - Unmutes a user",
                "</warn:1210273600628858920> - Warns a user",
                "</unwarn:1210273600628858922> - Unwarns a user",
                "</warnings:1210273600628858923> - Gets the warnings of a user",
                "</slowmode:1210273600628858924> - Sets the slowmode of a channel",
            ]

            em = discord.Embed(title="BobCat Moderation Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Moderation', url="https://docs.bobcatbot.xyz/commands/moderation"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

        if self.values[0] == "Leveling":
            commands = [
                "</rank:1210273600150442028> - Shows your or member's level and XP",
                "</leaderboard:1210273600150442029> - Shows the leaderboard",
            ]

            em = discord.Embed(title="BobCat Leveling Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Leveling', url="https://docs.bobcatbot.xyz/commands/leveling"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

        if self.values[0] == "Economy":
            commands = [
                "/shop - Shows all of bobcats economy commands",
                "</leaderboard:1210273600150442029> - Shows the leaderboard",
                "</balance:1210273600150442030> - Shows your balance",
                "</work:1210273600150442031> - Works and earns coins",
                "</withdraw:1210273600150442032> - Withdraws coins from the bank",
                "</deposit:1210273600150442033> - Deposits coins to the bank",
                "</buy:1210273600150442034> - Buys an item from the shop",
                "</sell:1210273600150442035> - Sells an item from your inventory",
                "</inventory:1210273600150442036> - Shows your inventory",
                "</givecoins:1210273600150442037> - MODERATOR ONLY - Gives coins to a user" if interaction.user.guild_permissions.moderate_members else "",
                "</removecoins:1210273600150442038> - MODERATOR ONLY - Removes coins from a user" if interaction.user.guild_permissions.moderate_members else "", 
            ]

            em = discord.Embed(title="BobCat Economy Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Economy', url="https://docs.bobcatbot.xyz/commands/economy"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

class DropdownView(discord.ui.View):
    def __init__(self, client, guild_id):
        super().__init__(timeout=None)
        self.client = client
        
        self.add_item(Dropdown(self.client, guild_id))
        
        self.add_item(discord.ui.Button(label='Invite', url="https://discord.com/oauth2/authorize?client_id=957234668627951640&permissions=8&scope=bot", row=2))
        self.add_item(discord.ui.Button(label="Support", url="https://discord.gg/T7zE4x4xbT", row=2))

class MiscHelp(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(description="A list of commands and utilities")
    async def help(self, ctx):
        em = discord.Embed(
            color=v.style(ctx.guild.id),
            title="BobCat Help Menu",
            description=(
                "Thanks for using **BobCat**"
                "\n**BobCat Prefix:** `b!`"
                "\nBobcat is a simple to use bot. It has functions such as entertainment, moderation, administration, and so much more."
            )
        )
        em.set_thumbnail(url=self.client.user.avatar.url)
        await ctx.respond(embed=em, view=DropdownView(self.client, ctx.guild), ephemeral=False)

def setup(client):
    client.add_cog(MiscHelp(client))



# if self.values[0] == "Information":
#     embed = discord.Embed(color=v.style(interaction.guild.id), title="BobCat",
#         description=(
#             f"**Bot**"
#             f"\n**Severs:** {len(self.client.guilds)}"
#             f"\n**Users:** {len(self.client.users)}"
#             f"\n**Ping:** {(self.client.latency * 1000):.0f}ms"
#             f"\n**Pycord version:** {discord.__version__}"
            
#             "\n\n**Server**"
#             f"\n**Uptime:** {self.client.get_bot_uptime()}"
#             f"\n**CPU Load:** {psutil.virtual_memory().percent}%"
#             f"\n**Memory:** {psutil.cpu_percent()}%"
#             f"\n**Disk:** undefined"
#             f"\n**Server's Operating System:** {platform.uname()[0]}"
#         )
#     )
#     embed.set_thumbnail(url=self.client.user.avatar.url)
    
#     view = discord.ui.View()
#     view.add_item(BackBtn(self.client))
#     await interaction.response.edit_message(content=None, embed=embed, view=view)
        
# if self.values[0] == "Permissions":
#     perms = ""
#     member = interaction.guild.get_member(self.client.user.id)
#     for perm in member.guild_permissions:
#         if perm[1] == True:
#             perms += f"> ✅ {perm[0].replace('_', ' ').title()}" + "\n"
#         else:
#             perms += f"> ❎ {perm[0].replace('_', ' ').title()}" + "\n"
    
#     embed=discord.Embed(
#         color=v.style(interaction.guild.id),
#         description=(
#             f"Permissions"
#             f"\n> Below are a list of permissions SparkV needs in order to work correctly in this server."
#             f"\n\n{perms}"
#         )
#     )
    
#     view = discord.ui.View()
#     view.add_item(BackBtn(self.client))
#     await interaction.response.edit_message(content=None, embed=embed, view=view)