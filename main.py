import os
import asyncio
# from dashboard.index import run_dashboard
from modules import bot as v

client = v.client

async def on_ready():
    # client.loop.create_task(chpr(client))
    print(f'{client.user.name} has connected to Discord')
    print("Shards: ", len(client.shards))

client.add_listener(on_ready, "on_ready")

def load_extensions():
    for foldername in os.listdir('./cogs'):
        for filename in os.listdir(f"./cogs/{foldername}"):
            if filename.endswith('.py'):
                client.load_extension(f'cogs.{foldername}.{filename[:-3]}')
                # print(f"/cogs/{foldername}/{filename} -> loaded")

async def main():
    async with client:
        # run_dashboard()
        load_extensions()
        await client.start(v.token)
asyncio.run(main())