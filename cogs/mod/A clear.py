import discord
from discord.ext import commands
from modules import bot as v

class mod_clear(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

# clear [amount]
    @commands.slash_command(name="clear", description="Clears a certain amount of messages")
    @commands.bot_has_guild_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    @discord.option("amount", description="The amount of messages you want to delete", required=True)
    async def clear(self, ctx: discord.ApplicationContext, amount):
        if int(amount) < 0:
            em = discord.Embed(title="❌ The amount must be positive!", color=v.error)
            return await ctx.respond(embed=em, ephemeral=True)
        
        if int(amount) > 150:
            em = discord.Embed(title="❌ You cannot delete more then 150 messages!", color=v.error)
            return await ctx.respond(embed=em, ephemeral=True)

        await ctx.channel.purge(limit=int(amount))
        await ctx.respond(f"Cleared {amount} messages", delete_after=7)

# Error checking
    @clear.error
    async def clear_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Messages` permission", color=v.error)
            return await ctx.respond(embed=error, ephemeral=True)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to manage messages", description='Please give BobCat the "Manage Messages" permission')
            error = discord.Embed(description=f"❌ I can't do that because I'm missing the `Manage Messages` permission.  \n\nNeed help?\n{v.docs}/moderation/clear", color=v.error)
            return await ctx.respond(embed=error, ephemeral=True)
        
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/clear",
                description="/clear [amount] \n\n**Arguments**\n`amount`: The amount of messages you want to delete",
            )
            return await ctx.respond(embed=error, ephemeral=True)

def setup(client):
    client.add_cog(mod_clear(client))