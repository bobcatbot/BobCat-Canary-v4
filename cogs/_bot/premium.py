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
        for guild in self.client.guilds:
            try:
                doc = Guild.get(str(guild.id)).run()
                if doc is None:
                    continue

                premium = doc.premium

                if not premium.get('status'):
                    continue
                if premium.get('plan') != "trial":
                    continue
                if not premium.get('code_expiry'):
                    continue

                expiry_date = datetime.fromisoformat(str(premium['code_expiry']))

                if expiry_date <= datetime.now():
                    doc.premium['status'] = False
                    doc.premium['active'] = False
                    doc.save()
                    print(f"Premium expired for {guild.name} ({guild.id})")

            except Exception as e:
                print(f"⚠️ Error checking premium for {guild.name} ({guild.id}): {e}")

def setup(client):
    client.add_cog(Premium(client))