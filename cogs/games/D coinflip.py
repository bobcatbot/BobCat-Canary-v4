import discord
import random
from modules import bot as v
from discord.ext import commands

class GamesCoinfilp(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(description="Lets you flip a coin for Heads/Tails")
    async def coinflip(self, ctx):
        coin = ["Heads", "Tales"]
        await ctx.respond(f"{ctx.author.name} has fliped **{random.choice(coin)}**")

def setup(client):
    client.add_cog(GamesCoinfilp(client))