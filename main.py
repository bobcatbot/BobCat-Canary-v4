import os
import discord
from datetime import datetime
from modules import bot as v
from web_dashboard.index import run_dashboard

client = v.client

client.shard_uptime = {}  # {shard_id: datetime}

async def on_ready():
    print(f'{client.user.name} has connected to Discord')
    print("Shards: ", len(client.shards))

    for shard_id, shard in client.shards.items():
        if shard_id not in client.shard_uptime:
            client.shard_uptime[shard_id] = datetime.now()
        
        await client.change_presence(
            shard_id=shard_id,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Shard {shard_id}/{len(client.shards)}"
            )
        )
client.add_listener(on_ready, "on_ready")

@client.event
async def on_shard_ready(shard_id):
    client.shard_uptime[shard_id] = datetime.now()

@client.event
async def on_shard_disconnect(shard_id):
    client.shard_uptime.pop(shard_id, None)  # clear uptime when disconnected


def load_extensions():
    for foldername in os.listdir('./cogs'):
        for filename in os.listdir(f"./cogs/{foldername}"):
            if filename.endswith('.py'):
                ext = f'cogs.{foldername}.{filename[:-3]}'
                client.load_extension(ext)
                # print(f"{ext} -> loaded")

load_extensions()
run_dashboard()
client.run(v.token)