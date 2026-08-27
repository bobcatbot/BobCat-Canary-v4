import discord
from discord.ext import commands
from modules import bot as v

class Slowmode(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

# slowmode [time|off]
    @commands.slash_command(name="slowmode", description="Sets the slowmode of a channel")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @discord.option("delay", description="Seconds you want to set the slowmode", required=True)
    async def slowmode(self, ctx, *, delay):
        if delay == "off":
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"{ctx.channel.mention} is no longer in slowmode"
            )
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.respond(embed=embed)
        
        await ctx.channel.edit(slowmode_delay=delay)
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"{ctx.channel.mention} is now in slowmode of **{delay} seconds** \n\n(Suggestion: Type /slowmode off when you want to disable slowmode)"
        )
        await ctx.respond(embed=embed)

# Error checking
    @slowmode.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title="❌ You are missing `Manage Channels` permission"
            )
            return await ctx.respond(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to set slowmode", description='Please give BobCat the "Manage Channels" permission')
            embed = discord.Embed(description=f"❌ I can't do that because I'm missing the `Manage Channels` permission.  \n\nNeed help?\n{v.docs}/moderation/slowmode", color=v.error)
            return await ctx.respond(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/slowmode",
                description="/slowmode [seconds]  \n\n**Arguments**\n`seconds`: time in SECONDS"
            )
            return await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Slowmode(client))