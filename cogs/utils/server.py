import discord
from modules import bot as v
from discord.ext import commands

class ServerButtons(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client

    @discord.ui.button(label='Information', style=discord.ButtonStyle.green, disabled=True)
    async def info(self, button: discord.ui.Button, interaction: discord.Interaction):
        for buttons in self.children:
            buttons.style=discord.ButtonStyle.gray
            buttons.disabled = False
        button.disabled = True
        button.style = discord.ButtonStyle.green

        created = f'{interaction.guild.created_at.timestamp()}'.split('.')[0]

        members = {
            "total": len(interaction.guild.members),
            "humans": len(list(filter(lambda m: not m.bot, interaction.guild.members))),
            "bots": len(list(filter(lambda m: m.bot, interaction.guild.members)))
        }
        channels = {
            "total": len(interaction.guild.channels),
            "text": len(interaction.guild.text_channels),
            "voice": len(interaction.guild.voice_channels),
            "categories": len(interaction.guild.categories)
        }

        embed = discord.Embed(
            color=v.style(interaction.guild.id),
            title=v.t.msg(interaction.guild, "server.info_embed.title", name=interaction.guild.name),
            description=v.t.msg(
                interaction.guild, "server.info_embed.description",
                name=interaction.guild.name, id=interaction.guild.id,
                owner=interaction.guild.owner.mention, created=created,
                roles=len(interaction.guild.roles), members=members['total'],
                channels=channels['total'], text=channels['text'],
                voice=channels['voice'], categories=channels['categories'],
            )
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Avatar', style=discord.ButtonStyle.gray)
    async def back(self, button: discord.ui.Button, interaction: discord.Interaction):
        for buttons in self.children:
            buttons.style=discord.ButtonStyle.gray
            buttons.disabled = False
        button.disabled = True
        button.style = discord.ButtonStyle.green

        embed = discord.Embed(title=v.t.msg(interaction.guild, "server.avatar_embed.title", name=interaction.guild.name), color=v.style(interaction.guild.id))
        try:
            embed.set_image(url=interaction.guild.icon.url)
        except AttributeError:
            embed.description += v.t.msg(interaction.guild, "server.avatar_embed.not_found", name=interaction.guild.name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Banner', style=discord.ButtonStyle.gray)
    async def banner(self, button: discord.ui.Button, interaction: discord.Interaction):
        for buttons in self.children:
            buttons.style=discord.ButtonStyle.gray
            buttons.disabled = False
        button.disabled = True
        button.style = discord.ButtonStyle.green
        try:
            embed = discord.Embed(
                color=v.style(interaction.guild.id),
                title=v.t.msg(interaction.guild, "server.banner_embed.title", name=interaction.guild.name)
            )
            embed.set_image(url=interaction.guild.banner.url)
        except AttributeError:
            embed = discord.Embed(
                color=v.style(interaction.guild.id),
                title=v.t.msg(interaction.guild, "server.banner_embed.title", name=interaction.guild.name),
                description=v.t.msg(interaction.guild, "server.banner_embed.not_found", name=interaction.guild.name)
            )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label='Members', style=discord.ButtonStyle.gray)
    async def memeber(self, button: discord.ui.Button, interaction: discord.Interaction):
        for buttons in self.children:
            buttons.style=discord.ButtonStyle.gray
            buttons.disabled = False
        button.disabled = True
        button.style = discord.ButtonStyle.green

        statuses = [
            len(list(filter(lambda m: str(m.status) == "online", interaction.guild.members))),
            len(list(filter(lambda m: str(m.status) == "idle", interaction.guild.members))),
            len(list(filter(lambda m: str(m.status) == "dnd", interaction.guild.members))),
            len(list(filter(lambda m: str(m.status) == "offline",  interaction.guild.members)))
        ]
        members = [
            len(list(filter(lambda m: not m.bot, interaction.guild.members))), # Humans
            len(list(filter(lambda m: m.bot, interaction.guild.members))) # Bots
        ]

        embed = discord.Embed(
            color=v.style(interaction.guild.id),
            title=v.t.msg(interaction.guild, "server.members_embed.title", name=interaction.guild.name),
            description=v.t.msg(
                interaction.guild, "server.members_embed.description",
                total=len(interaction.guild.members), humans=members[0], bots=members[1],
                online=statuses[0], idle=statuses[1], dnd=statuses[2], offline=statuses[3],
            )
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for buttons in self.children:
            buttons.disabled = True
        return await self.message.edit_original_response(view=self)
    
class servercmd(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(
        description=v.t.msg(None, "server.cmd.description"),
        name_localizations=v.t.localizations("server.cmd.name"),
        description_localizations=v.t.localizations("server.cmd.description"),
    )
    async def server(self, ctx):
        created = f'{ctx.guild.created_at.timestamp()}'.split('.')[0]

        members = {
            "total": len(ctx.guild.members),
            "humans": len(list(filter(lambda m: not m.bot, ctx.guild.members))),
            "bots": len(list(filter(lambda m: m.bot, ctx.guild.members)))
        }
        channels = {
            "total": len(ctx.guild.channels),
            "text": len(ctx.guild.text_channels),
            "voice": len(ctx.guild.voice_channels),
            "categories": len(ctx.guild.categories)
        }

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=v.t.msg(ctx.guild, "server.info_embed.title", name=ctx.guild.name),
            description=v.t.msg(
                ctx.guild, "server.info_embed.description",
                name=ctx.guild.name, id=ctx.guild.id,
                owner=ctx.guild.owner.mention, created=created,
                roles=len(ctx.guild.roles), members=members['total'],
                channels=channels['total'], text=channels['text'],
                voice=channels['voice'], categories=channels['categories'],
            )
        )

        view = ServerButtons(self.client)
        view.message = await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(servercmd(client))