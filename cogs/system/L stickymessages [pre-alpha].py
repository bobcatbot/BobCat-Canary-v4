import discord
import json
from discord.ext import commands
from modules import bot as v

class Sticky(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.cache = {}  # channel_id -> message_id

    # ------------------------------------------------------------
    # Sync cache to DB (optional)
    # ------------------------------------------------------------
    # @commands.Cog.listener()
    async def on_ready(self):
        all_configs = v.db.get_all_server_config()
        for guild_id, config in all_configs.items():
            sticky = config.get("sticky_messages", {})
            for entry in sticky.get("messages", []):
                cid = int(entry["channel_id"])
                mid = entry.get("message_id")
                if mid:
                    self.cache[cid] = mid

    # ------------------------------------------------------------
    # Sticky logic
    # ------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return

        channel = message.channel

        # Load config inline
        with open("server.json", "r") as f:
            config = json.load(f)

        sticky_root = config["Dash"]["sticky_messages"]
        messages = sticky_root.get("messages", [])

        # Find sticky for this channel
        sticky_entry = next(
            (m for m in messages if m["channel_id"] == str(channel.id) and m["status"]),
            None
        )
        if not sticky_entry:
            return

        text = sticky_entry["text"]

        # Remove previous sticky
        old_id = sticky_entry.get("message_id")
        if old_id:
            try:
                old_msg = await channel.fetch_message(int(old_id))
                await old_msg.delete()
            except discord.NotFound:
                pass

        # Post new sticky
        new_msg = await channel.send(text)
        sticky_entry["message_id"] = str(new_msg.id)

        # Save config inline
        sticky_root["messages"] = messages
        config["Dash"]["sticky_messages"] = sticky_root

        with open("server.json", "w") as f:
            json.dump(config, f, indent=2)

        # Cache
        self.cache[channel.id] = new_msg.id

    # ------------------------------------------------------------
    # Sticky command
    # ------------------------------------------------------------
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def sticky(self, ctx, *, text: str = None):
        """
        Set, show, or remove a sticky message in this channel.
        Usage:
            !sticky             -> show sticky
            !sticky text here   -> set sticky
            !sticky remove      -> remove sticky
        """
        channel = ctx.channel

        # Load config inline
        with open("server.json", "r") as f:
            config = json.load(f)

        sticky_root = config["Dash"]["sticky_messages"]
        messages = sticky_root.get("messages", [])

        # Find existing sticky
        sticky_entry = next(
            (m for m in messages if m["channel_id"] == str(channel.id)),
            None
        )

        # --------------------------------------------------------
        # Remove sticky
        # --------------------------------------------------------
        if text and text.lower() in ["remove", "delete", "off"]:
            if sticky_entry:
                messages.remove(sticky_entry)

                sticky_root["messages"] = messages
                config["Dash"]["sticky_messages"] = sticky_root

                with open("server.json", "w") as f:
                    json.dump(config, f, indent=2)

                return await ctx.send("🗑️ Sticky removed from this channel.")
            else:
                return await ctx.send("⚠️ There is no sticky message in this channel.")

        # --------------------------------------------------------
        # Show sticky
        # --------------------------------------------------------
        if text is None:
            if sticky_entry:
                return await ctx.send(f"📌 **Current sticky:**\n{sticky_entry['text']}")
            else:
                return await ctx.send("ℹ️ No sticky message set for this channel.")

        # --------------------------------------------------------
        # Set sticky
        # --------------------------------------------------------
        if sticky_entry:
            sticky_entry["text"] = text
            sticky_entry["status"] = True
            sticky_entry["message_id"] = None  # refresh next message
        else:
            messages.append({
                "channel_id": str(channel.id),
                "text": text,
                "message_id": None,
                "status": True
            })

        sticky_root["messages"] = messages
        config["Dash"]["sticky_messages"] = sticky_root

        with open("server.json", "w") as f:
            json.dump(config, f, indent=2)

        await ctx.send("✅ Sticky saved. It will update after the next message.")

def setup(client):
    client.add_cog(Sticky(client))