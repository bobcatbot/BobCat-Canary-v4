import discord
from modules import bot as v
from discord.ext import commands

class ServerButtons(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client

    @discord.ui.button(label='Infomation', style=discord.ButtonStyle.green, disabled=True)
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
            title=f"{interaction.guild.name}'s Infomation",
            description=(
                f"**Name:** {interaction.guild.name}\n > ID: {interaction.guild.id}"
                f"\n**Owner:** {interaction.guild.owner.mention}"
                f"\n**Created:** <t:{created}:R>"
                f"\n**Roles:** {len(interaction.guild.roles)}"
                f"\n**Members:** {members['total']}"
                f"\n**Channels:** {channels['total']}\n > Text: {channels['text']}\n > Voice: {channels['voice']}\n > Categories: {channels['categories']}"
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

        embed = discord.Embed(title=f"{interaction.guild.name}'s Avatar", color=v.style(interaction.guild.id))
        try:
            embed.set_image(url=interaction.guild.icon.url)
        except AttributeError:
            embed.description += f"I can't find {interaction.guild.name}'s avatar"
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
                title=f"{interaction.guild.name}'s Avatar"
            )
            embed.set_image(url=interaction.guild.banner.url)
        except AttributeError:
            embed = discord.Embed(
                color=v.style(interaction.guild.id),
                title="{0}'s Banner".format(interaction.guild.name),
                description="I can't find {0}'s banner".format(interaction.guild.name)
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
            title=f"{interaction.guild.name}'s Members",
            description=(
                f"**Members:** {len(interaction.guild.members)} \n> Humans: {members[0]} \n> Bots: {members[1]}"
                f"\n\n**Statuses** \n> 🟢 Online: {statuses[0]} \n> 🟠 Idle: {statuses[1]} \n> 🔴 DND: {statuses[2]} \n> ⚪ Offline: {statuses[3]}"
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
    
    @commands.slash_command(description="View information on your server")
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
            title=f"{ctx.guild.name}'s Infomation",
            description=(
                f"**Name:** {ctx.guild.name}\n > ID: {ctx.guild.id}"
                f"\n**Owner:** {ctx.guild.owner.mention}"
                f"\n**Created:** <t:{created}:R>"
                f"\n**Members:** {members['total']}"
                f"\n**Roles:** {len(ctx.guild.roles)}"
                f"\n**Channels:** {channels['total']}\n > Text: {channels['text']}\n > Voice: {channels['voice']}\n > Categories: {channels['categories']}"
            )
        )

        view = ServerButtons(self.client)
        view.message = await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(servercmd(client))