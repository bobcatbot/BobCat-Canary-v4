import discord
from modules import bot as v
from discord.ext import commands
from modules.models import Guild

COMMANDS = {
    "Commands": {
        "menu": "All of bobcats commands",
        "title": "BobCat General Commands",
        "gate": None,
        "cmds": {
            "/help": "The command you used to get here!",
            "/invite": "Invite BobCat to your server",
            "/user": "Get information about a user",
            "/server": "Get information about a server",
        }
    },
    "Games": {
        "menu": "All of bobcats game commands",
        "title": "BobCat Game Commands",
        "gate": None,
        "cmds": {
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
        "menu": "All of bobcats moderation commands",
        "title": "BobCat Moderation Commands",
        "gate": "moderation",
        "cmds": {
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
        "menu": "All of bobcats leveling commands",
        "title": "BobCat Leveling Commands",
        "gate": "leveling",
        "cmds": {
            "/rank": "Shows your or a member's level and XP",
            "/leaderboard": "Shows the leaderboard",
        }
    },
    "Economy": {
        "menu": "All of bobcats economy commands",
        "title": "BobCat Economy Commands",
        "gate": "economy",
        "cmds": {
            "/economy shop": "Browse the shop",
            "/economy balance": "Shows your balance",
            "/economy work": "Earn coins",
            "/economy withdraw": "Withdraw coins from the bank",
            "/economy deposit": "Deposit coins to the bank",
            "/economy buy": "Buy an item from the shop",
            "/economy sell": "Sell an item from your inventory",
            "/economy inventory": "Shows your inventory",
        },
        "staff_cmds": { # shown only to moderate_members
            "/economy give-coins": "🔒 Give coins to a user",
            "/economy remove-coins": "🔒 Remove coins from a user",
        },
    },
    "Giveaway": {
        "menu": "All of bobcats giveaway commands",
        "title": "BobCat Giveaway Commands",
        "gate": "giveaways",
        "cmds": {
            "/giveaway create": "Create a giveaway",
            "/giveaway end": "End a giveaway",
            "/giveaway reroll": "Reroll a giveaway",
            "/giveaway list": "List all giveaways",
            # "/giveaway delete": "Delete a giveaway",
        }
    },
    "Birthdays": {
        "menu": "All of bobcats birthdays commands",
        "title": "BobCat Birthdays Commands",
        "gate": "birthdays",
        "cmds": {
            "/birthdays": "Show all birthdays for the current month",
            "/next-birthdays": "Shows the next 10 upcoming birthdays",
            "/birthday": "Show yours or another member's birthday",
            "/set-birthday": "Sets yours or another member's birthday",
            "/remove-birthday": "Remove yours or another member's birthday",
        }
    }
}

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
            content=None, embed=em, view=DropdownView(self.client)
        )

class Dropdown(discord.ui.Select):
    def __init__(self, client: discord.Bot):
        self.client: discord.Bot = client
        self._mentions = self._build_mentions()

        options = [
            discord.SelectOption(label=name, description=cat["menu"])
            for name, cat in COMMANDS.items()
        ]

        super().__init__(
            placeholder="Browse Categories",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="menu"
        )

    def _build_mentions(self) -> dict[str, str]:
        """{'economy shop': '</economy shop:123>'} for every registered slash command."""
        mentions = {}
        for command in self.client.walk_application_commands():
            if not isinstance(command, discord.SlashCommand):
                continue
            parts = []
            c = command
            while c.parent:
                parts.append(c.parent.name)
                c = c.parent
            parts.reverse()
            parts.append(command.name)
            full_name = " ".join(parts)
            mentions[full_name] = f"</{full_name}:{command.qualified_id}>"
        return mentions

    def _mention(self, name: str) -> str:
        return self._mentions.get(name, f"`/{name}`")

    def _fmt(self, cmds: dict[str, str]) -> str:
        """Format an ordered {path: description} mapping into embed lines."""
        return "\n".join(
            f"{self._mention(path.lstrip('/'))}{f' - {desc}' if desc else ''}"
            for path, desc in cmds.items()
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        cat = COMMANDS.get(selected)
        if cat is None:
            return

        # Gate toggle-able modules against the guild's *current* dashboard
        gate = cat["gate"]
        if gate:
            dash = await v.dashboard(interaction.guild.id)
            module = getattr(dash, gate, None) if dash else None
            if not module or not module.get("status"):
                return await interaction.response.send_message(
                    f"❌ The **{selected}** module is disabled for this server.",
                    ephemeral=True,
                )

        cmds = dict(cat["cmds"])
        if "staff_cmds" in cat and interaction.user.guild_permissions.moderate_members:
            cmds.update(cat["staff_cmds"])

        em = discord.Embed(
            title=cat["title"],
            description=self._fmt(cmds),
            color=v.style(interaction.guild.id)
        )
        em.set_thumbnail(url=self.client.user.avatar.url)

        view = discord.ui.View()
        view.add_item(BackBtn(self.client))
        await interaction.response.edit_message(embed=em, view=view)

class DropdownView(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client
        
        self.add_item(Dropdown(self.client))
        self.add_item(discord.ui.Button(label="Invite", url="https://discord.com/oauth2/authorize?client_id=957234668627951640&permissions=8&scope=bot", row=2))
        self.add_item(discord.ui.Button(label="Support", url="https://discord.gg/T7zE4x4xbT", row=2))

class MiscHelp(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client: discord.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        self.client.add_view(DropdownView(self.client))
       
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
        await ctx.respond(embed=em, view=DropdownView(self.client), ephemeral=False)

def setup(client):
    client.add_cog(MiscHelp(client))