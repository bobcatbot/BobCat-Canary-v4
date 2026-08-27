import discord
from datetime import datetime
from discord.ext import commands, tasks
from modules import bot as v
from modules.models import Guild

class Premium(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.stop_premium.start()

    def cog_unload(self):
        self.stop_premium.cancel()

    @tasks.loop(hours=24)
    async def stop_premium(self):
        # Find all guilds with active trial premium and expired code_expiry
        expired = await Guild.find({
            "premium.status": True,
            "premium.active": True,
            "premium.plan": "trial",
            "premium.code_expiry": {"$lte": datetime.now()}
        }).to_list()

        for doc in expired:
            doc.premium['status'] = False
            doc.premium['active'] = False
            await doc.save()
            guild = self.client.get_guild(int(doc.id))
            if guild:
                print(f"Premium expired for {guild.name} ({guild.id})")
            else:
                print(f"Premium expired for guild {doc.id} (not in cache)")

        # Optional: log count
        if expired:
            print(f"Expired {len(expired)} trial premium(s)")

def setup(client):
    client.add_cog(Premium(client))