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
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    @discord.option(
        "amount",
        int,
        description="The number of messages to delete",
        required=True,
        min_value=1,
        max_value=150,
    )
    async def clear(
        self,
        ctx: discord.ApplicationContext,
        amount: int,
    ):
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
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing permission",
                description="You need the `Manage Messages` permission.",
                color=v.error,
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        if isinstance(original, commands.BotMissingPermissions):
            v.push_notification(
                ctx.guild,
                kind="error",
                title="BobCat cannot manage messages",
                description=(
                    "The clear command failed because BobCat is missing "
                    "the Manage Messages permission."
                ),
            )

            embed = discord.Embed(
                description=(
                    "❌ I am missing the `Manage Messages` permission."
                    f"\nNeed help?\n{v.docs}/moderation/clear"
                ),
                color=v.error,
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="❌ Clear command failed",
            description="An unexpected error occurred while deleting messages.",
            color=v.error,
        )

        await ctx.respond(embed=embed, ephemeral=True)
        raise original

def setup(client):
    client.add_cog(ModClear(client))