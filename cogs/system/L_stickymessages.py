import asyncio
import discord
from discord.ext import commands
from modules import bot as v
from modules.models import StickyState

class Sticky(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.locks: dict[int, asyncio.Lock] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Bots are skipped so the sticky we post ourselves can't retrigger this.
        if message.author.bot or message.guild is None:
            return

        dash = await v.dashboard(message.guild.id)
        if not dash or not dash.sticky_messages.status:
            return

        channel = message.channel
        entry = next((m for m in dash.sticky_messages.messages if m.channel_id == str(channel.id)), None)
        if entry is None:
            return

        # Two messages landing together would both delete the old sticky and both post a new one,
        # leaving a duplicate nobody tracks. The lock makes the second wait and replace the first's.
        async with self.locks.setdefault(channel.id, asyncio.Lock()):
            state_id = f"{message.guild.id}_{channel.id}"
            state = await StickyState.get(state_id)
            if state:
                try:
                    await channel.get_partial_message(int(state.message_id)).delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

            try:
                sent = await channel.send(entry.text)
            except discord.Forbidden:
                return

            if state:
                state.message_id = str(sent.id)
                await state.save()
            else:
                await StickyState(
                    id=state_id,
                    guild_id=str(message.guild.id),
                    channel_id=str(channel.id),
                    message_id=str(sent.id),
                ).insert()

def setup(client):
    client.add_cog(Sticky(client))
