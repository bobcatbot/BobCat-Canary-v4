import json
import discord
from discord.ext import commands, tasks
from modules import bot as v

class Stats(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client

        # Define counter handlers as a mapping to avoid repetitive if-blocks
        self.COUNTER_HANDLERS = {
            "botCount":    lambda guild: sum(1 for m in guild.members if m.bot),
            "humanCount":  lambda guild: sum(1 for m in guild.members if not m.bot),
            "onlineCount": lambda guild: sum(1 for m in guild.members if m.status != discord.Status.offline),
            "textCount":   lambda guild: sum(1 for c in guild.channels if isinstance(c, discord.TextChannel)),
            "voiceCount":  lambda guild: sum(1 for c in guild.channels if isinstance(c, discord.VoiceChannel)),
            "roleCount":   lambda guild: len(guild.roles),
        }
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.stats.start()

    @tasks.loop(hours=1)
    async def stats(self):
        CLIENT_GUILDS = [self.client.get_guild(v.btz_gid)]
        
        for guild in CLIENT_GUILDS:
            # Load config once per guild, not once per counter
            data = json.load(open("server.json"))["Dash"]["stats"]
            counters = data['counters']

            for counter in counters:
                target = counter["target"]
                handler = self.COUNTER_HANDLERS.get(target)

                if handler is None:
                    # print(f"Unknown counter target '{target}' — skipping.")
                    continue

                count = handler(guild)

                channel = self.client.get_channel(int(counter["channel_id"])) if counter["channel_id"] else None
                
                if channel is None:
                    # print(f"Channel not found for counter '{target}'.")
                    continue

                await channel.edit(name=counter["text"].format(count=count))
            # End
        # End

def setup(client):
    client.add_cog(Stats(client))