import json
import discord
from discord.ext import commands
from modules import bot as v

def author_is_mod(guild, user):
    with open("server.json", "r") as f:
        roles = json.load(f)['settings']

    # if user.guild_permissions.administrator:
    #     return True
    # if user == ctx.guild.owner:
    #     return True
    
    if not any(
        role in roles['admin_roles'] or 
        role in roles['moderator_roles'] 
        for role in user.roles
    ):
        return True
    return False

class mod_test(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client
    
    @commands.command()
    async def test(self, ctx):
        mod = author_is_mod(ctx.guild, ctx.author)
        if not mod:
            return await ctx.send("You do not have the correct permissions")
        
        await ctx.send("You have the correct permissions")

def setup(client):
    client.add_cog(mod_test(client))