import io
import aiohttp
import discord
from discord.ext import commands
from modules import bot as v

class mod_emojis(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

# stealemoji [url] [name]
    # @commands.command(aliases=["addemoji", "ae", "ce", "createemoji"])
    # @commands.has_permissions(manage_emojis=True)
    # async def steal(self, ctx, emoji: discord.PartialEmoji):

    #     emoji_bytes = await emoji.read()
    #     await ctx.guild.create_custom_emoji(name=emoji.name, image=emoji_bytes)

    #     await ctx.send(f"Successfully created emoji")

    @commands.command(aliases=["addemoji", "ae", "ce", "createemoji"])
    @commands.has_permissions(manage_emojis=True)
    async def steal(self, ctx, url, *, name):
        guild = ctx.guild
        async with aiohttp.ClientSession() as ses:
            async with ses.get(url) as r:
                try:
                    img_or_gif = io.BytesIO(await r.read())
                    b_value = img_or_gif.getvalue()

                    if r.status in range(200, 299):
                        emojis = await guild.create_custom_emoji(image=b_value, name=name)
                        await ctx.message.delete()
                        await ctx.send(f"Successfully created emoji: <:{name}:{emojis.id}>")
                        return
                    else:
                        await ctx.send(f'❌ Error when making request | {r.status} response.')
                        return
                except discord.HTTPException:
                    error = discord.Embed(title="❌ File size is too big!", color=v.error)
                    await ctx.send(embed=error)

# Error checking
    @steal.error
    async def createemoji_error(self, ctx, error):
        if isinstance(error, commands.PartialEmojiConversionFailure):
            error = discord.Embed(
                color=v.error,
                title="Invalid Emoji", 
                description="❌ Please provide a valid emoji from a server not a default emoji"
            )
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(
                color=v.error,
                title="Invalid Permission", 
                description="❌ You are missing `Manage Emojis` permission"
            )
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://www.docs.bobcatbot.xyz/moderation/emoji",
                description="b!steal [url] [name]  \n\n**Arguments**\n`url`: Emoji url \n`name`: A name for the emoji",
            )
            return await ctx.send(embed=embed)

def setup(client):
    client.add_cog(mod_emojis(client))