import discord
import random
from modules import bot as v
from discord.ext import commands

class GamesCoinfilp(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        description=v.t.msg(None, "coinflip.cmd.description"),
        name_localizations=v.t.localizations("coinflip.cmd.name"),
        description_localizations=v.t.localizations("coinflip.cmd.description"),
    )
    async def coinflip(self, ctx):
        coin = [v.t.msg(ctx.guild, "coinflip.heads"), v.t.msg(ctx.guild, "coinflip.tails")]
        await ctx.respond(v.t.msg(ctx.guild, "coinflip.result", user=ctx.author.name, result=random.choice(coin)))

def setup(client):
    client.add_cog(GamesCoinfilp(client))