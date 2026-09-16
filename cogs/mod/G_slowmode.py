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
            return await ctx.respond(
                embed=discord.Embed(title="❌ Missing permission", description="You need the `Manage Channels` permission.", color=v.error),
                ephemeral=True
            )
        
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot set channel slowmode",
                description="The slowmode command failed because BobCat is missing the Manage Channels permission.",
                fix=f"{v.docs}/moderation/slowmode",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ I am missing the `Manage Channels` permission",
                    description=f"[Permissions Help]({v.docs}/moderation/slowmode)",
                    color=v.error,
                ),
                ephemeral=True
            )

        await ctx.respond(
            embed=discord.Embed(
                title="❌ Command failed",
                description="An unexpected error occurred. Please try again.",
                color=v.error,
            ),
            ephemeral=True,
        )
        raise error

def setup(client):
    client.add_cog(Slowmode(client))