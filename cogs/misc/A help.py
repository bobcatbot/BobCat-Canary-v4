import discord
from modules import bot as v
from discord.ext import commands
from modules.models import Guild

class BackBtn(discord.ui.Button):
    def __init__(self, client, row=1):
        super().__init__(label="Back", style=discord.ButtonStyle.blurple, row=row)
        self.client = client

    async def callback(self, interaction: discord.Interaction):
        em = discord.Embed(
            color=v.style(interaction.guild.id),
            title="BobCat Help Menu",
            description=(
                "Thanks for using **BobCat**"
                "\n**BobCat Prefix:** `b!`"
                "\nBobcat is a simple to use bot with entertainment, moderation, administration, and more."
            )
        )
        em.set_thumbnail(url=self.client.user.avatar.url)
        await interaction.response.edit_message(
            content=None, embed=em, view=DropdownView(self.client, interaction.guild.id, dash=await v.dashboard(interaction.guild.id))
        )


class Dropdown(discord.ui.Select):
    def __init__(self, client: discord.Bot, dash=None):
        self.client: discord.Bot = client
        self._commands = self.get_all_commands()

        options = [
            discord.SelectOption(label="Commands", description="All of bobcats commands"),
            discord.SelectOption(label="Games", description="All of bobcats game commands"),
        ]

        data = dash

        if data:
            if data.moderation["status"]:
                options.append(discord.SelectOption(label="Mod", description="All of bobcats moderation commands"))
            if data.leveling["status"]:
                options.append(discord.SelectOption(label="Leveling", description="All of bobcats leveling commands"))
            if data.economy["status"]:
                options.append(discord.SelectOption(label="Economy", description="All of bobcats economy commands"))
            if data.birthdays['status']:
                options.append(discord.SelectOption(label="Birthdays", description="All of bobcats birthdays commands"))

        super().__init__(
            placeholder="Browse Categories",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="menu"
        )

    def get_all_commands(self) -> dict:
        """Returns a dict of {group_name: [full_command_paths]} and a list of top-level slash commands."""
        groups = {}
        top_level = []

        for command in self.client.walk_application_commands():
            if isinstance(command, discord.SlashCommand):
                parts = []
                c = command
                while c.parent:
                    parts.append(c.parent.name)
                    c = c.parent
                parts.reverse()
                parts.append(command.name)
                full_path = "/" + " ".join(parts)

                if len(parts) > 1:
                    group_name = parts[0]
                    groups.setdefault(group_name, []).append(full_path)
                else:
                    top_level.append(full_path)

            elif isinstance(command, discord.MessageCommand):
                top_level.append(f"[msg] {command.name}")

        return {"groups": groups, "commands": top_level}

    def cmd_mention(self, name: str) -> str:
        """Returns a Discord slash command mention like </help:123456789>"""
        for command in self.client.walk_application_commands():
            if isinstance(command, discord.SlashCommand):
                parts = []
                c = command
                while c.parent:
                    parts.append(c.parent.name)
                    c = c.parent
                parts.reverse()
                parts.append(command.name)
                full_name = " ".join(parts)

                if full_name == name:
                    return f"</{full_name}:{command.qualified_id}>"
        
        return f"`/{name}`"  # fallback if not found

    def _fmt(self, paths: list[str], descriptions: dict[str, str]) -> str:
        """Format a list of command paths with descriptions."""
        lines = []
        for path in paths:
            desc = descriptions.get(path)
            mention = self.cmd_mention(path.lstrip("/"))
            lines.append(f"{mention}{' - ' + desc if desc else ''}")
        return "\n".join(lines)

    async def callback(self, interaction: discord.Interaction):
        category_map = {
            "Commands": {
                "title": "BobCat General Commands",
                "paths": ["/help", "/invite", "/user", "/server"],
                "descriptions": {
                    "/help": "The command you used to get here!",
                    "/invite": "Invite BobCat to your server",
                    "/user": "Get information about a user",
                    "/server": "Get information about a server",
                }
            },
            "Games": {
                "title": "BobCat Game Commands",
                "paths": ["/games", "/8ball", "/coinflip", "/diceroll", "/guess", "/rps", "/tictactoe"],
                "descriptions": {
                    "/games": "Shows all of bobcats game commands",
                    "/8ball": "Ask a question to the magic 8ball",
                    "/coinflip": "Flips a coin",
                    "/diceroll": "Rolls a 6 sided dice",
                    "/guess": "Guess the random number between 1 and 10",
                    "/rps": "Play rock, paper, scissors",
                    "/tictactoe": "Play tic-tac-toe",
                }
            },
            "Mod": {
                "title": "BobCat Moderation Commands",
                "paths": [
                    "/clear", "/kick", "/ban", "/unban", "/mute", "/unmute",
                    "/warn", "/unwarn", "/warnings", "/slowmode",
                    "/lockdown add channel", "/lockdown add server",
                    "/lockdown remove channel", "/lockdown remove server"
                ],
                "descriptions": {
                    "/clear": "Clears messages",
                    "/kick": "Kicks a user",
                    "/ban": "Bans a user",
                    "/unban": "Unbans a user",
                    "/mute": "Mutes a user",
                    "/unmute": "Unmutes a user",
                    "/warn": "Warns a user",
                    "/unwarn": "Unwarns a user",
                    "/warnings": "Gets the warnings of a user",
                    "/slowmode": "Sets the slowmode of a channel",
                    "/lockdown add channel": "Locks a channel",
                    "/lockdown add server": "Locks the server",
                    "/lockdown remove channel": "Unlocks a channel",
                    "/lockdown remove server": "Unlocks the server",
                }
            },
            "Leveling": {
                "title": "BobCat Leveling Commands",
                "paths": ["/rank", "/leaderboard"],
                "descriptions": {
                    "/rank": "Shows your or a member's level and XP",
                    "/leaderboard": "Shows the leaderboard",
                }
            },
            "Economy": {
                "title": "BobCat Economy Commands",
                "paths": [
                    "/economy shop", "/economy balance", "/economy work",
                    "/economy withdraw", "/economy deposit", "/economy buy",
                    "/economy sell", "/economy inventory",
                    *(["/economy give-coins", "/economy remove-coins"] if interaction.user.guild_permissions.moderate_members else [])
                ],
                "descriptions": {
                    "/economy shop": "Browse the shop",
                    "/economy balance": "Shows your balance",
                    "/economy work": "Earn coins",
                    "/economy withdraw": "Withdraw coins from the bank",
                    "/economy deposit": "Deposit coins to the bank",
                    "/economy buy": "Buy an item from the shop",
                    "/economy sell": "Sell an item from your inventory",
                    "/economy inventory": "Shows your inventory",
                    "/economy give-coins": "🔒 Give coins to a user",
                    "/economy remove-coins": "🔒 Remove coins from a user",
                }
            },
            "Giveaway": {
                "title": "BobCat Giveaway Commands",
                "paths": [
                    "/giveaway create", "/giveaway end", "/giveaway reroll",
                    "/giveaway list",
                    # "/giveaway delete"
                ],
                "descriptions": {
                    "/giveaway create": "Create a giveaway",
                    "/giveaway end": "End a giveaway",
                    "/giveaway reroll": "Reroll a giveaway",
                    "/giveaway list": "List all giveaways",
                    # "/giveaway delete": "Delete a giveaway",
                }
            },
            "Birthdays": {
                "title": "BobCat Birthdays Commands",
                "paths": [
                    "/birthdays", "/next-birthdays", "/birthday",
                    "/set-birthday", "/remove-birthday"
                ],
                "descriptions": {
                    "/birthdays": "Show all birthdays for the current month",
                    "/next-birthdays": "Shows the next 10 upcoming birthdays",
                    "/birthday": "Show yours or another member's birthday",
                    "/set-birthday": "Sets yours or another member's birthday",
                    "/remove-birthday": "Remove yours or another member's birthday",
                }
            }
        }

        selected = self.values[0]
        if selected not in category_map:
            return

        cat = category_map[selected]
        
        em = discord.Embed(
            title=cat["title"],
            description=self._fmt(cat["paths"], cat["descriptions"]),
            color=v.style(interaction.guild.id)
        )
        em.set_thumbnail(url=self.client.user.avatar.url)

        view = discord.ui.View()
        view.add_item(BackBtn(self.client))
        await interaction.response.edit_message(embed=em, view=view)

class DropdownView(discord.ui.View):
    def __init__(self, client, guild_id, dash=None):
        super().__init__(timeout=None)
        self.client = client
        
        self.add_item(Dropdown(self.client, dash))
        self.add_item(discord.ui.Button(label="Invite", url="https://discord.com/oauth2/authorize?client_id=957234668627951640&permissions=8&scope=bot", row=2))
        self.add_item(discord.ui.Button(label="Support", url="https://discord.gg/T7zE4x4xbT", row=2))

class MiscHelp(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client: discord.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            dash = await v.dashboard(guild.id)
            self.client.add_view(DropdownView(self.client, guild.id, dash=dash))
       
    @commands.slash_command(description="A list of commands and utilities")
    async def help(self, ctx):
        em = discord.Embed(
            color=v.style(ctx.guild.id),
            title="BobCat Help Menu",
            description=(
                "Thanks for using **BobCat**"
                f"\n**BobCat Prefix:** `{self.client.command_prefix}`"
                "\nBobcat is a simple to use bot with entertainment, moderation, administration, and more."
            )
        )
        em.set_thumbnail(url=self.client.user.avatar.url)
        await ctx.respond(embed=em, view=DropdownView(self.client, ctx.guild, dash=await v.dashboard(ctx.guild)), ephemeral=False)

def setup(client):
    client.add_cog(MiscHelp(client))