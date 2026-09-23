import discord
from discord.ext import commands
from modules import bot as v

class ModClear(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="clear",
        description=v.t.msg(None, "clear.cmd.description"),
        name_localizations=v.t.localizations("clear.cmd.name"),
        description_localizations=v.t.localizations("clear.cmd.description"),
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    @discord.option(
        "amount",
        int,
        description=v.t.msg(None, "clear.cmd.options.amount.description"),
        name_localizations=v.t.localizations("clear.cmd.options.amount.name"),
        description_localizations=v.t.localizations("clear.cmd.options.amount.description"),
        required=True,
        min_value=1,
        max_value=150,
    )
    async def clear(self, ctx: discord.ApplicationContext, amount: int):
        await ctx.defer(ephemeral=True)

        deleted = await ctx.channel.purge(
            limit=amount,
            reason=f"Clear command used by {ctx.author}",
        )

        embed = discord.Embed(
            description=v.t.msg(ctx.guild, "clear.cleared", count=len(deleted)),
            color=v.success,
        )

        await ctx.followup.send(embed=embed, ephemeral=True)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                description=v.t.msg(ctx.guild, "clear.errors.missing_perms_description"),
                color=v.error,
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot manage messages",
                description="The clear command failed because BobCat is missing the Manage Messages permission.",
                fix=f"{v.docs}/moderation/clear",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "clear.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "clear.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/clear"),
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
    client.add_cog(ModClear(client))