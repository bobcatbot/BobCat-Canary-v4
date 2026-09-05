import asyncio
import discord
import traceback
import pathlib
from beanie import init_beanie
from pymongo import AsyncMongoClient
from datetime import datetime
from modules import bot as v
from modules.models import ALL_MODELS
from web_dashboard.index import serve_dashboard

client = v.client

client.shard_uptime = {}
client.beanie_initialized = False

async def initialise_database() -> None:
    if client.beanie_initialized:
        return

    max_attempts = 5
    base_delay = 2

    for attempt in range(1, max_attempts + 1):
        try:
            print(f"🔄 Database connection attempt {attempt}/{max_attempts}...")

            mongo_client = AsyncMongoClient(
                v.mongoURI_db,
                serverSelectionTimeoutMS=15_000,
                connectTimeoutMS=15_000,
            )

            database = mongo_client["Data"]

            await init_beanie(
                database=database,
                document_models=ALL_MODELS,
            )

            # Force a real connection test.
            await mongo_client.admin.command("ping")

            client.mongo_client = mongo_client
            client.beanie_initialized = True

            print(f"✅ Database connected: {database.name}")
            print(f"✅ Beanie initialised with {len(ALL_MODELS)} models")
            return

        except Exception as e:
            print(f"❌ Database connection attempt {attempt} failed: {e}")
            traceback.print_exc()

            if attempt == max_attempts:
                print("❌ All database connection attempts failed. Bot cannot start.")
                raise

            delay = base_delay * (2 ** (attempt - 1))
            print(f"⏳ Waiting {delay} seconds before retry...")
            await asyncio.sleep(delay)

def discover_extensions() -> list[str]:
    cogs_path = pathlib.Path(__file__).parent / "cogs"
    extensions = []
    for category_path in cogs_path.iterdir():
        if not category_path.is_dir() or category_path.name.startswith("__"):
            continue
        for file_path in category_path.glob("*.py"):
            # "__x.py" (dunder) and "_x.py" (single leading underscore) are
            # private helper modules for cogs in this category, not cogs
            # themselves - e.g. cogs/mod/_helpers.py, cogs/money/_shop.py.
            # Skip both so load_extension() isn't attempted on a module
            # with no setup() function.
            if file_path.name.startswith("_"):
                continue
            # Convert path to module name: cogs.category.filename
            rel_path = file_path.relative_to(cogs_path.parent)
            module_name = str(rel_path.with_suffix("")).replace("\\", ".")
            extensions.append(module_name)
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
    print("─" * 50)
    print(f"Extensions loaded: {len(loaded)}")
    print(f"Extensions failed: {len(failed)}")
    if failed:
        print("Failed extensions:")
        for extension, error in failed:
            print(f"  - {extension}: {error}")
    print("─" * 50)

async def update_shard_presence() -> None:
    """Update presence for all shards with rate limit handling"""
    shard_count = len(client.shards)
    for shard_id in client.shards:
        client.shard_uptime.setdefault(shard_id, discord.utils.utcnow())
        try:
            await client.change_presence(
                shard_id=shard_id,
                activity=discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{shard_id + 1}/{shard_count} shards • {len(client.guilds)} guilds",
                ),
            )
        except discord.HTTPException as e:
            print(f"Failed to update presence for shard {shard_id}: {e}")

@client.event
async def on_ready():
    print("─" * 50)
    print(f"✅ Logged in as {client.user}")
    print(f"✅ Guilds: {len(client.guilds)}")
    print(f"✅ Shards: {len(client.shards)}")
    print(f"✅ Started at: {datetime.now()}")
    print("─" * 50)
    await update_shard_presence()

@client.event
async def on_shard_ready(shard_id: int):
    print("─" * 50)
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

async def start() -> None:
    print("Starting BobCat Bot")
    print("─" * 60)

    await initialise_database()
    load_extensions()

    print("🌐 Starting Web Dashboard")
    print("🤖 Starting Discord client")

    # Both run as tasks on this same event loop — no separate thread,
    # no separate Motor/Beanie init, one shared set of model classes.
    async with client:
        await asyncio.gather(
            client.start(v.token),
            serve_dashboard(),
        )

if __name__ == "__main__":
    asyncio.run(start())