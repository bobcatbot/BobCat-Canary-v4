import discord
import json
from discord.ext import commands
from modules import bot as v

class Sticky(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client: discord.Client = client
        # Cache only message IDs for fast deletion
        self.cache = {}

    async def cog_load(self):
        """
        Sync cache from database when the cog loads.
        """
        all_configs = v.db.get_all_server_config()

        for guild_id, config in all_configs.items():
            sticky = config.get("sticky_messages", {})
            messages = sticky.get("messages", [])

            for entry in messages:
                cid = int(entry["channel_id"])
                mid = entry.get("message_id")
                if mid:
                    self.cache[cid] = mid

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        guild = message.guild
        channel = message.channel

        cooonnfig = json.load(open('server.json'))
        config = cooonnfig['Dash']
        sticky_root = config.get("sticky_messages", {})
        messages = sticky_root.get("messages", [])

        print(messages)

        # Find sticky for this channel
        sticky_entry = next((m for m in messages if m["channel_id"] == str(channel.id) and m["status"] is True), None)
        if not sticky_entry:
            return

        text = sticky_entry["text"]

        # Delete old sticky
        old_id = sticky_entry.get("message_id")
        if old_id:
            try:
                old_message = await channel.fetch_message(int(old_id))
                await old_message.delete()
            except discord.NotFound:
                pass

        # Send new sticky
        new_msg = await channel.send(text)

        # Update DB entry
        sticky_entry["message_id"] = str(new_msg.id)

        # Save back to Mongo DB
        sticky_root["messages"] = messages
        config["sticky_messages"] = sticky_root
        # v.db.update_server_config(guild, config)

        # save back to local file
        with open('server.json', 'w') as f:
            json.dump(cooonnfig, f, indent=2)
        
        # Cache update
        self.cache[channel.id] = new_msg.id


    # ============================================================
    # Commands
    # ============================================================

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def sticky(self, ctx, *, text: str = None):
        """
        Set or view the sticky message.
        """
        if text:
            self.sticky_text = text
            await ctx.send("✅ Sticky message updated.")
        else:
            await ctx.send(f"**📌 Current sticky message:**\n{self.sticky_text}")

def setup(client):
    client.add_cog(Sticky(client))