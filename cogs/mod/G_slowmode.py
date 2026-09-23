import discord
from discord.ext import commands
from modules import bot as v

class Slowmode(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

# slowmode [time|off]
    @commands.slash_command(
        name="slowmode",
        description=v.t.msg(None, "slowmode.cmd.description"),
        name_localizations=v.t.localizations("slowmode.cmd.name"),
        description_localizations=v.t.localizations("slowmode.cmd.description"),
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    @discord.option(
        "delay",
        description=v.t.msg(None, "slowmode.cmd.options.delay.description"),
        name_localizations=v.t.localizations("slowmode.cmd.options.delay.name"),
        description_localizations=v.t.localizations("slowmode.cmd.options.delay.description"),
        required=True,
    )
    async def slowmode(self, ctx, *, delay):
        if delay == "off":
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=v.t.msg(ctx.guild, "slowmode.off", channel=ctx.channel.mention)
            )
            await ctx.channel.edit(slowmode_delay=0)
            return await ctx.respond(embed=embed)

        await ctx.channel.edit(slowmode_delay=delay)
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=v.t.msg(ctx.guild, "slowmode.on", channel=ctx.channel.mention, delay=delay)
        )
        await ctx.respond(embed=embed)

# Error checking
    @slowmode.error
    async def slowmode_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "slowmode.errors.missing_perms_description"),
                    color=v.error,
                ),
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
                    title=v.t.msg(ctx.guild, "slowmode.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "slowmode.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/slowmode"),
                    color=v.error,
                ),
                ephemeral=True
            )

        await ctx.respond(
            embed=discord.Embed(
                title=v.t.msg(ctx.guild, "mod.common_errors.generic_title"),
                description=v.t.msg(ctx.guild, "mod.common_errors.generic_description"),
                color=v.error,
            ),
            ephemeral=True,
        )
        raise error

def setup(client):
    client.add_cog(Slowmode(client))