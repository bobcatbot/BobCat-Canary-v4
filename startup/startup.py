import discord
import asyncio, json
from discord.ext import commands

from modules import bot as v
from dashboard.index import run_dashboard
from .loadcogs import loadcogs

async def startup(client):
    run_dashboard()
    loadcogs(client)
  
    await client.wait_until_ready()
    client.loop.create_task(chpr(client))
    print(f'{client.user.name} has connected to Discord')
    print('Shards: ', client.shard_count)

async def chpr(client):
    statuses = json.load(open("modules/status.json"))['status']
    
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            activity_types = {
                "Watching": discord.ActivityType.watching,
                "Listening": discord.ActivityType.listening,
                "Playing": discord.ActivityType.playing,
                "Streaming": discord.ActivityType.streaming,
                "Competing": discord.ActivityType.competing
            }
            
            for status in statuses:
                await client.change_presence(activity=discord.Activity(
                    type=activity_types.get(f"{status['type']}".capitalize()), 
                    name=f"{status.get('name')}".format(client=client, guilds=len(client.guilds), users=len(client.users))
                ))

                await asyncio.sleep(10)
        except ConnectionResetError:
            pass
    return chpr(client)