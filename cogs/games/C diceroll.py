import discord
import random
import asyncio
from modules import bot as v
from discord.ext import commands

class GamesDiceroll(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(description="Rolls a 6 sided dice")
    async def diceroll(self, ctx):
        dice = ["1", "2", "3", "4", "5", "6"]

        msg = await ctx.respond(f"{ctx.user.name} throws their dice")
        await asyncio.sleep(2)
        await msg.edit_original_response(content=f"{ctx.user.name} rolled a **{random.choice(dice)}**")

def setup(client):
    client.add_cog(GamesDiceroll(client))