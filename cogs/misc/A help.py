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
    def __init__(self, client: discord.Bot, g):
        self.client: discord.Bot = client

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
        def command(self, itr: discord.Interaction, command: str = "help"):
            commands = self.client.application_commands
            
            for c in commands:
                if c.name == command:
                    return f"</{c.name}:{c.id}>"
            return ""
            
        if self.values[0] == "Commands":
            commands = [
                f"{command(interaction, 'help')} - The command you used to get here!",
                f"{command(interaction, 'invite')} - Invite BobCat to your server",
                f"{command(interaction, 'user')} - Get information about a user",
                f"{command(interaction, 'server')} - Get information about a server",
            ]

            em = discord.Embed(title="BobCat General Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Commands', url="https://docs.bobcatbot.xyz/commands"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)
    
        if self.values[0] == "Games":
            commands = [
                f"{command(interaction, 'games')} - Shows all of bobcats game commands",
                f"{command(interaction, '8ball')} - Ask a question to the magic 8ball",
                f"{command(interaction, 'coinflip')} - Flips a coin",
                f"{command(interaction, 'diceroll')} - Rolls a 6 sided dice",
                f"{command(interaction, 'guess')} - Guess the random number between 1 and 10",
                f"{command(interaction, 'rps')} - Play rock, paper, scissors against your opponent",
                f"{command(interaction, 'tictactoe')} - Play tic-tac-toe",
            ]

            em = discord.Embed(title="BobCat Game Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Games', url="https://docs.bobcatbot.xyz/commands/games"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

        if self.values[0] == "Mod":
            commands = [
                f"{command(interaction, 'clear')} - Clears messages",
                f"{command(interaction, 'kick')} - Kicks a user",
                f"{command(interaction, 'ban')} - Bans a user",
                f"{command(interaction, 'unban')} - Unbans a user",
                f"{self.client.command_prefix}massban - Bans multiple users at once",
                f"{command(interaction, 'mute')} - Mutes a user",
                f"{command(interaction, 'unmute')} - Unmutes a user",
                f"{command(interaction, 'warn')} - Warns a user",
                f"{command(interaction, 'unwarn')} - Unwarns a user",
                f"{command(interaction, 'warnings')} - Gets the warnings of a user",
                f"{command(interaction, 'slowmode')} - Sets the slowmode of a channel",
            ]

            em = discord.Embed(title="BobCat Moderation Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Moderation', url="https://docs.bobcatbot.xyz/commands/moderation"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

        if self.values[0] == "Leveling":
            commands = [
                f"{command(interaction, 'rank')} - Shows your or member's level and XP",
                f"{command(interaction, 'leaderboard')} - Shows the leaderboard",
            ]

            em = discord.Embed(title="BobCat Leveling Commands", description="\n".join(commands), color=v.style(interaction.guild.id))
            em.set_thumbnail(url=self.client.user.avatar.url)
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label='Leveling', url="https://docs.bobcatbot.xyz/commands/leveling"))
            view.add_item(BackBtn(self.client))
            await interaction.response.edit_message(embed=em, view=view)

        if self.values[0] == "Economy":
            commands = [
                f"{command(interaction, 'shop')} - Shows all of bobcats economy commands",
                f"{command(interaction, 'leaderboard')} - Shows the leaderboard",
                f"{command(interaction, 'balance')} - Shows your balance",
                f"{command(interaction, 'work')} - Works and earns coins",
                f"{command(interaction, 'withdraw')} - Withdraws coins from the bank",
                f"{command(interaction, 'deposit')} - Deposits coins to the bank",
                f"{command(interaction, 'buy')} - Buys an item from the shop",
                f"{command(interaction, 'sell')} - Sells an item from your inventory",
                f"{command(interaction, 'inventory')} - Shows your inventory",
                f"{command(interaction, 'givecoins')} - MODERATOR ONLY - Gives coins to a user" if interaction.user.guild_permissions.moderate_members else "",
                f"{command(interaction, 'removecoins')} - MODERATOR ONLY - Removes coins from a user" if interaction.user.guild_permissions.moderate_members else "", 
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
    def __init__(self, client: discord.Bot):
        self.client: discord.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            self.client.add_view(DropdownView(self.client, guild.id))
       
    @commands.slash_command(description="A list of commands and utilities")
    async def help(self, ctx):
        em = discord.Embed(
            color=v.style(ctx.guild.id),
            title="BobCat Help Menu",
            description=(
                "Thanks for using **BobCat**"
                f"\n**BobCat Prefix:** `{self.client.command_prefix}`"
                "\nBobcat is a simple to use bot. It has functions such as entertainment, moderation, administration, and so much more."
            )
        )
        em.set_thumbnail(url=self.client.user.avatar.url)
        await ctx.respond(embed=em, view=DropdownView(self.client, ctx.guild), ephemeral=False)

def setup(client):
    client.add_cog(MiscHelp(client))