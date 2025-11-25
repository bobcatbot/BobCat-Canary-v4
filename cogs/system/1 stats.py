import json
import discord
from discord.ext import commands, tasks
from modules import bot as v

class Stats(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client


    @tasks.loop(hours=1)
    async def stats(self):
        for guild in self.client.guilds:
            # Get the guild object
            data = json.load(open("server.json"))["Dash"]["stats"]
            
            # Bots
            
            # Online members
            
            # Total Text channels
            
            # Total Voice channels
            
            # Total Categories

            # Total Roles

        ... # End
    
def setup(client):
    client.add_cog(Stats(client))