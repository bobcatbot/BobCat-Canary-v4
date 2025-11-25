import discord

from dashboard.index import run_dashboard
from startup.loadcogs import loadcogs
from modules import bot as v

client = v.client

async def startup(client):
    run_dashboard()
    loadcogs(client)

async def chpr(client):
    import asyncio, json
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

                await asyncio.sleep(8)
        except ConnectionResetError:
            pass
    return chpr(client)

async def on_ready():
    client.loop.create_task(chpr(client))
    print(f'{client.user.name} has connected to Discord')
    print("Shards: ", len(client.shards))

client.add_listener(on_ready, "on_ready")

client.loop.create_task(startup(client))
client.run(v.token)