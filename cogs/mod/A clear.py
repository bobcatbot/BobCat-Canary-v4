import discord
from discord.ext import commands
from modules import bot as v

class ModClear(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="clear",
        description="Clears a certain number of messages",
    )
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    @discord.option(
        "amount",
        int,
        description="The number of messages to delete",
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
            description=f"✅ Cleared **{len(deleted)}** messages.",
            color=v.success,
        )

        await ctx.followup.send(embed=embed, ephemeral=True)

    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing permission", description="You need the `Manage Messages` permission.", color=v.error)
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
                    title="❌ I am missing the `Manage Messages` permission",
                    description=f"[Permissions Help]({v.docs}/moderation/clear)",
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
    client.add_cog(ModClear(client))