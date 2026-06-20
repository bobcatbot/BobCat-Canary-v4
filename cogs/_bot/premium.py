import discord
from datetime import datetime
from discord.ext import commands, tasks
from modules import bot as v

class Premium(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.stop_premium.start()

    @tasks.loop(hours=24)
    async def stop_premium(self):
        for guild in self.client.guilds:
            try:
                config = v.db.get_server_config(guild, True)
                if not config:
                    continue

                premium = config['premium']

                if not premium.get('status'):
                    continue
                if premium.get('plan') != "trial":
                    continue
                if not premium.get('code_expiry'):
                    continue

                expiry_date = datetime.fromisoformat(str(premium['code_expiry']))

                if expiry_date <= datetime.now():
                    v.db.update_server_config(guild, True, key='premium.status', value=False)
                    v.db.update_server_config(guild, True, key='premium.active', value=False)
                    print(f"Premium expired for {guild.name} ({guild.id})")

            except Exception as e:
                print(f"⚠️ Error checking premium for {guild.name} ({guild.id}): {e}")

def setup(client):
    client.add_cog(Premium(client))