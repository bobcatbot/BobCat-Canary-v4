import discord
from modules import bot as v
from discord.ext import commands
from modules.models import Guild

CATEGORIES = [
    {"key": "commands", "gate": None},
    {"key": "games", "gate": None},
    {"key": "mod", "gate": "moderation"},
    {"key": "leveling", "gate": "leveling"},
    {"key": "economy", "gate": "economy", "staff": True},  # staff_cmds shown only to moderate_members
    {"key": "giveaway", "gate": "giveaways"},
    {"key": "birthdays", "gate": "birthdays"},
]
CATEGORIES_BY_KEY = {cat["key"]: cat for cat in CATEGORIES}

class BackBtn(discord.ui.Button):
    def __init__(self, client, row=1):
        super().__init__(label=v.t.msg(None, "help.menu.back_button"), style=discord.ButtonStyle.blurple, row=row)
        self.client = client

    async def callback(self, interaction: discord.Interaction):
        em = discord.Embed(
            color=v.style(interaction.guild.id),
            title=v.t.msg(interaction.guild, "help.menu.title"),
            description=v.t.msg(interaction.guild, "help.menu.description", prefix="b!")
        )
        em.set_thumbnail(url=self.client.user.avatar.url)
        await interaction.response.edit_message(
            content=None, embed=em, view=DropdownView(self.client, interaction.guild)
        )

class Dropdown(discord.ui.Select):
    def __init__(self, client: discord.Bot, guild=None):
        self.client: discord.Bot = client
        self._mentions = self._build_mentions()

        # value= is the stable English key (CATEGORIES_BY_KEY lookup in the
        # callback), separate from label= which is the translated display
        # text - so category selection keeps working regardless of language.
        options = [
            discord.SelectOption(
                value=cat["key"],
                label=v.t.msg(guild, f"help.categories.{cat['key']}.name"),
                description=v.t.msg(guild, f"help.categories.{cat['key']}.menu"),
            )
            for cat in CATEGORIES
        ]

        super().__init__(
            placeholder=v.t.msg(guild, "help.menu.placeholder"),
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
        cat = CATEGORIES_BY_KEY.get(selected)
        if cat is None:
            return
        key = cat["key"]

        # Gate toggle-able modules against the guild's *current* dashboard
        gate = cat["gate"]
        if gate:
            dash = await v.dashboard(interaction.guild.id)
            module = getattr(dash, gate, None) if dash else None
            if not module or not module.get("status"):
                category_name = v.t.msg(interaction.guild, f"help.categories.{key}.name")
                return await interaction.response.send_message(
                    v.t.msg(interaction.guild, "help.menu.disabled", category=category_name),
                    ephemeral=True,
                )

        cmds = v.t.table(interaction.guild, f"help.categories.{key}.cmds")
        if cat.get("staff") and interaction.user.guild_permissions.moderate_members:
            cmds.update(v.t.table(interaction.guild, f"help.categories.{key}.staff_cmds"))

        em = discord.Embed(
            title=v.t.msg(interaction.guild, f"help.categories.{key}.title"),
            description=self._fmt(cmds),
            color=v.style(interaction.guild.id)
        )
        em.set_thumbnail(url=self.client.user.avatar.url)

        view = discord.ui.View()
        view.add_item(BackBtn(self.client))
        await interaction.response.edit_message(embed=em, view=view)

class DropdownView(discord.ui.View):
    def __init__(self, client, guild=None):
        super().__init__(timeout=None)
        self.client = client

        self.add_item(Dropdown(self.client, guild))
        self.add_item(discord.ui.Button(label=v.t.msg(guild, "help.menu.invite_button"), url="https://discord.com/oauth2/authorize?client_id=957234668627951640&permissions=8&scope=bot", row=2))
        self.add_item(discord.ui.Button(label=v.t.msg(guild, "help.menu.support_button"), url="https://discord.gg/T7zE4x4xbT", row=2))

class MiscHelp(commands.Cog):
    def __init__(self, client: discord.Bot):
        self.client: discord.Bot = client

    @commands.Cog.listener()
    async def on_ready(self):
        # No guild here (fires once at startup, not tied to any interaction) - this
        # registration only supplies click-behavior for messages sent before a
        # restart, it doesn't re-render their already-displayed text, so DEFAULT_LANG
        # is fine. Every *new* /help invocation below builds a fresh, guild-aware
        # DropdownView regardless of what this registered.
        self.client.add_view(DropdownView(self.client))

    @commands.slash_command(
        description=v.t.msg(None, "help.cmd.description"),
        name_localizations=v.t.localizations("help.cmd.name"),
        description_localizations=v.t.localizations("help.cmd.description"),
    )
    async def help(self, ctx):
        em = discord.Embed(
            color=v.style(ctx.guild.id),
            title=v.t.msg(ctx.guild, "help.menu.title"),
            description=v.t.msg(ctx.guild, "help.menu.description", prefix=self.client.command_prefix)
        )
        em.set_thumbnail(url=self.client.user.avatar.url)
        await ctx.respond(embed=em, view=DropdownView(self.client, ctx.guild), ephemeral=False)

def setup(client):
    client.add_cog(MiscHelp(client))