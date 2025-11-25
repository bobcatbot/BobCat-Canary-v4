import discord
from discord.ext import commands
from modules import bot as v

class mod_poll(commands.Cog):
    def __init__(self, client):
        self.client = client

# poll [message]
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def poll(self, ctx, *, message):
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title="<:news:901404652862570507> Poll",
            description=f'{message}'
        )

        await ctx.message.delete()
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('👍')
        await msg.add_reaction('👎')

# Error checking
    @poll.error
    async def poll_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(
                color=v.error,
                title="❌ You are missing `Manage Messages` permission"
            )
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/poll",
                description="b!poll [message] \n\n**Arguments**\n`message`: Displays the message in a embed",
            )
            return await ctx.send(embed=error)

def setup(client):
    client.add_cog(mod_poll(client))