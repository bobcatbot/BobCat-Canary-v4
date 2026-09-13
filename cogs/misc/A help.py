import discord
from modules import bot as v
from discord.ext import commands
from modules.models import Guild

COMMANDS = {
    "Commands": {
        "menu": "All of bobcats commands",
        "title": "BobCat General Commands",
        "gate": None,
        "cmds": ["/help", "/invite", "/user", "/server"],
    },
    "Games": {
        "menu": "All of bobcats game commands",
        "title": "BobCat Game Commands",
        "gate": None,
        "cmds": ["/games", "/8ball", "/coinflip", "/diceroll", "/guess", "/rps", "/tictactoe"],
    },
    "Mod": {
        "menu": "All of bobcats moderation commands",
        "title": "BobCat Moderation Commands",
        "gate": "moderation",
        "cmds": [
            "/clear", "/kick", "/ban", "/unban", "/mute", "/unmute", "/warn", "/unwarn", "/warnings", "/slowmode",
            "/lockdown add channel", "/lockdown add server",
            "/lockdown remove channel", "/lockdown remove server",
        ],
    },
    "Leveling": {
        "menu": "All of bobcats leveling commands",
        "title": "BobCat Leveling Commands",
        "gate": "leveling",
        "cmds": ["/rank", "/leaderboard"],
    },
    "Economy": {
        "menu": "All of bobcats economy commands",
        "title": "BobCat Economy Commands",
        "gate": "economy",
        "cmds": [
            "/economy shop", "/economy balance", "/economy work", "/economy withdraw",
            "/economy deposit", "/economy buy", "/economy sell", "/economy inventory",
        ],
        "staff_cmds": ["/economy give-coins", "/economy remove-coins"],  # shown only to moderate_members
    },
    "Giveaway": {
        "menu": "All of bobcats giveaway commands",
        "title": "BobCat Giveaway Commands",
        "gate": "giveaways",
        "cmds": ["/giveaway create", "/giveaway end", "/giveaway reroll", "/giveaway list"],
    },
    "Birthdays": {
        "menu": "All of bobcats birthdays commands",
        "title": "BobCat Birthdays Commands",
        "gate": "birthdays",
        "cmds": ["/birthdays", "/next-birthdays", "/birthday", "/set-birthday", "/remove-birthday"],
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
        self._commands = self._build_command_index()

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

    def _build_command_index(self) -> dict[str, discord.SlashCommand]:
        """{'economy shop': <SlashCommand>} for every registered slash command,
        so COMMANDS only needs to list paths - names/descriptions/mentions
        all come straight from the real registration and can't drift out of
        sync with it."""
        index = {}
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
            index[" ".join(parts)] = command
        return index

    def _mention(self, name: str) -> str:
        cmd = self._commands.get(name)
        return f"</{name}:{cmd.qualified_id}>" if cmd else f"`/{name}`"

    def _fmt(self, paths: list[str], staff_paths: frozenset[str] = frozenset()) -> str:
        """Format a list of command paths (e.g. "/economy shop") into embed
        lines, pulling each one's description from the live command."""
        lines = []
        for path in paths:
            name = path.lstrip('/')
            cmd = self._commands.get(name)
            desc = cmd.description if cmd else ""
            if name in staff_paths and desc:
                desc = f"🔒 {desc}"
            lines.append(f"{self._mention(name)}{f' - {desc}' if desc else ''}")
        return "\n".join(lines)

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

        paths = list(cat["cmds"])
        staff_paths = frozenset()
        if "staff_cmds" in cat and interaction.user.guild_permissions.moderate_members:
            paths += cat["staff_cmds"]
            staff_paths = frozenset(p.lstrip('/') for p in cat["staff_cmds"])

        em = discord.Embed(
            title=cat["title"],
            description=self._fmt(paths, staff_paths),
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