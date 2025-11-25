import discord
from modules import bot as v
from discord.ext import commands

class ModDashboard(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

    @commands.slash_command(name="dashboard", description="View and edit your server's settings", guild_ids=v.guild_ids)
    @discord.default_permissions(manage_guild=True)
    async def dashboard(self, ctx):
        url = f"https://bobcatcanary.botdash.pro/g/{ctx.guild.id}"
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Open dashboard", url=url, style=discord.ButtonStyle.url))

        embed=discord.Embed(
            color=v.blurple,
            description=f"You can edit `{ctx.guild.name}'s` settings below"
        )
        await ctx.respond(content=None, embed=embed, view=view)

    @dashboard.error
    async def dashboard_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ Missing `Manage Server` permissions", color=v.error)
            await ctx.respond(embed=error, ephemeral=True)
        
        if isinstance(error, commands.BotMissingPermissions):
            error = discord.Embed(title="❌ I don't have permission to use this command", color=v.error)
            await ctx.respond(embed=error, ephemeral=True)

def setup(client):
    client.add_cog(ModDashboard(client))