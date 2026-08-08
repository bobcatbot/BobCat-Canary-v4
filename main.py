import os
import time
import traceback
import discord
from bunnet import init_bunnet
from pymongo import MongoClient
from modules import bot as v
from modules.models import ALL_MODELS
from web_dashboard.index import run_dashboard

client = v.client

client.shard_uptime = {}
client.bunnet_initialized = False

def initialise_database() -> None:
    if client.bunnet_initialized:
        return

    max_attempts = 5
    base_delay = 2

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"🔄 Database connection attempt {attempt}/{max_attempts}...")

            mongo_client = MongoClient(
                v.mongoURI_db,
                serverSelectionTimeoutMS=15_000,
                connectTimeoutMS=15_000,
            )

            database = mongo_client["Data"]

            init_bunnet(
                database=database,
                document_models=ALL_MODELS,
            )

            # Force a real connection test.
            mongo_client.admin.command("ping")

            client.mongo_client = mongo_client
            client.bunnet_initialized = True

            print(f"✅ Database connected: {database.name}")
            print(f"✅ Bunnet initialised with {len(ALL_MODELS)} models")
            return

        except Exception as e:
            print(f"❌ Database connection attempt {attempt} failed: {e}")
            traceback.print_exc()

            if attempt == max_attempts:
                print("❌ All database connection attempts failed. Bot cannot start.")
                raise

            delay = base_delay * (2 ** (attempt - 1))
            print(f"⏳ Waiting {delay} seconds before retry...")
            time.sleep(delay)

def discover_extensions() -> list[str]:
    extensions = []
    for category in os.listdir("./cogs"):
        category_path = os.path.join("./cogs", category)
        if not os.path.isdir(category_path) or category.startswith("__"):
            continue
        for filename in os.listdir(category_path):
            if not filename.endswith(".py") or filename.startswith("__"):
                continue
            extensions.append(f"cogs.{category}.{filename[:-3]}")
    return sorted(extensions)

def load_extensions() -> None:
    extensions = discover_extensions()
    loaded = []
    failed = []
    for extension in extensions:
        try:
            client.load_extension(extension)
            loaded.append(extension)
        except Exception as error:
            failed.append((extension, error))
            print(f"❌ Failed to load {extension}")
            traceback.print_exc()
    print("=" * 50)
    print(f"Extensions loaded: {len(loaded)}")
    print(f"Extensions failed: {len(failed)}")
    if failed:
        print("Failed extensions:")
        for extension, error in failed:
            print(f"  - {extension}: {error}")
    print("=" * 50)

async def update_shard_presence() -> None:
    shard_count = max(len(client.shards), 1)
    for shard_id in client.shards:
        client.shard_uptime.setdefault(
            shard_id,
            discord.utils.utcnow(),
        )
        await client.change_presence(
            shard_id=shard_id,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"Shard {shard_id + 1}/{shard_count}",
            ),
        )

@client.event
async def on_ready():
    print("=" * 50)
    print(f"✅ Logged in as {client.user}")
    print(f"✅ Guilds: {len(client.guilds)}")
    print(f"✅ Shards: {len(client.shards)}")
    print("=" * 50)
    await update_shard_presence()

@client.event
async def on_shard_ready(shard_id: int):
    client.shard_uptime[shard_id] = discord.utils.utcnow()
    print(f"✅ Shard {shard_id} ready")

@client.event
async def on_shard_disconnect(shard_id: int):
    client.shard_uptime.pop(shard_id, None)
    print(f"⚠️ Shard {shard_id} disconnected")

@client.event
async def on_shard_resumed(shard_id: int):
    client.shard_uptime[shard_id] = discord.utils.utcnow()
    print(f"🔄 Shard {shard_id} resumed")

def start() -> None:
    print("=" * 50)
    print("Starting BobCat Bot")
    print("=" * 50)

    initialise_database()
    load_extensions()

    print("🌐 Starting dashboard")
    run_dashboard()

    print("🤖 Starting Discord client")
    client.run(v.token)

if __name__ == "__main__":
    start()