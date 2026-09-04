import time
import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild, Starboard

DEFAULT_EMOJI = "⭐"
_CONFIG_CACHE_TTL = 30  # seconds

class JumpToMsg(discord.ui.View):
    def __init__(self, msg):
        super().__init__()
        button = discord.ui.Button(
            label="Jump to message",
            style=discord.ButtonStyle.link,
            url=msg.jump_url
        )
        self.add_item(button)

def _emoji_matches(emoji, configured: str) -> bool:
    """True when a reaction/payload emoji is the guild's configured star emoji.

    The dashboard emoji picker only emits native unicode emoji, so a simple
    string compare against the emoji name (unicode) or its full form (custom)
    covers every case.
    """
    configured = configured or DEFAULT_EMOJI
    return configured in (getattr(emoji, "name", None), str(emoji))

def _channel_is_nsfw(channel) -> bool:
    try:
        return bool(channel.is_nsfw())
    except AttributeError:
        return False

class starboard(commands.Cog):
    def __init__(self, client):
        self.client = client
        self._config_cache = {}  # guild_id -> (expires_at, config)

    async def _config(self, guild_id):
        """Return the guild's starboard config, cached briefly to keep the
        hot message-listener path off Mongo on every single message."""
        guild_id = str(guild_id)
        cached = self._config_cache.get(guild_id)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        doc = await Guild.get(guild_id)
        data = doc.dashboard.starboard if doc else {}
        self._config_cache[guild_id] = (time.monotonic() + _CONFIG_CACHE_TTL, data)
        return data

    @commands.Cog.listener()
    async def on_message(self, message):
        """Auto-star: react to every fresh message in the configured channels."""
        if message.author.bot or message.guild is None:
            return

        data = await self._config(message.guild.id)
        if not data.get("status") or data.get("locked"):
            return

        auto_channels = data.get("autoStar") or []
        if str(message.channel.id) not in [str(c) for c in auto_channels]:
            return

        emoji = data.get("emoji") or DEFAULT_EMOJI
        try:
            await message.add_reaction(emoji)
        except (discord.HTTPException, discord.Forbidden):
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member is None or payload.member.bot:
            return

        data = await self._config(payload.guild_id)

        starReaction = data.get("emoji") or DEFAULT_EMOJI
        starStatus = data.get("status")
        starChannel = data.get("channel")
        starLimit = data.get("limit")
        starJumpLink = data.get("jumpLink")
        starSelf = data.get("selfStar")
        starLocked = data.get("locked")
        starIgnore = [str(c) for c in (data.get("ignore") or [])]
        allowNsfw = data.get("allowNsfw")
        embedNsfwImages = data.get("embedNsfwImages")

        if not _emoji_matches(payload.emoji, starReaction):
            return
        if not starStatus or starLocked:
            return
        if not starChannel:
            return
        if str(payload.channel_id) in starIgnore:
            return
        if str(payload.channel_id) == str(starChannel):
            return

        starCount = 0

        guild = await v.client.fetch_guild(payload.guild_id)
        channel = await v.client.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        source_nsfw = _channel_is_nsfw(channel)
        if source_nsfw and not allowNsfw:
            return

        if not starSelf and payload.user_id == message.author.id:
            await message.remove_reaction(payload.emoji, payload.member)
            try:
                await payload.member.send("❌ You cannot star your own messages!")
            except discord.HTTPException:
                pass
            return

        for r in message.reactions:
            if _emoji_matches(r.emoji, starReaction):
                # Exclude the bot's own auto-star reaction (if any) from the
                # tally - it's a prompt to react, not a vote of its own.
                starCount += r.count - (1 if r.me else 0)

        embed = discord.Embed(
            color=0xeac02a,
            description=f"{message.content}",
            timestamp=message.created_at
        )
        embed.set_footer(text=f"{message.id}")

        try:
            embed.set_author(icon_url=message.author.avatar.url, name=f"{message.author}")
        except AttributeError:
            embed.set_author(name=f"{message.author}")

        if message.attachments and (not source_nsfw or embedNsfwImages):
            embed.set_image(url=message.attachments[0].url)

        result = await Starboard.find_one(
            Starboard.guild_id == str(guild.id),
            Starboard.root_message_id == str(message.id),
        )

        chan = await v.client.fetch_channel(int(starChannel))

        if starCount == int(starLimit) and result is None:
            star_message = await chan.send(
                content=f"{starReaction} **{starCount}** **|** {channel.mention}",
                embed=embed,
                view=JumpToMsg(message) if starJumpLink else None
            )

            await Starboard(
                guild_id=str(guild.id),
                root_message_id=str(message.id),
                star_message_id=str(star_message.id),
                stars=starCount,
            ).insert()
            return

        if starCount > int(starLimit) and result:
            star_message = await chan.fetch_message(int(result.star_message_id))
            await star_message.edit(content=f"{starReaction} **{starCount}** **|** {channel.mention}")

            result.stars = starCount
            await result.save()
            return

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        data = await self._config(payload.guild_id)

        starReaction = data.get("emoji") or DEFAULT_EMOJI
        starStatus = data.get("status")
        starChannel = data.get("channel")
        starLimit = data.get("limit")
        starLocked = data.get("locked")
        starIgnore = [str(c) for c in (data.get("ignore") or [])]

        if not _emoji_matches(payload.emoji, starReaction):
            return
        if not starStatus or starLocked:
            return
        if not starChannel:
            return
        if str(payload.channel_id) in starIgnore:
            return

        starCount = 0

        guild = v.client.get_guild(payload.guild_id)
        channel = v.client.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        for r in message.reactions:
            if _emoji_matches(r.emoji, starReaction):
                starCount += r.count - (1 if r.me else 0)

        result = await Starboard.find_one(
            Starboard.guild_id == str(guild.id),
            Starboard.root_message_id == str(message.id),
        )

        if result is None:
            return

        chan = v.client.get_channel(int(starChannel))

        if starCount < int(starLimit):
            star_message = await chan.fetch_message(int(result.star_message_id))
            await result.delete()

            await star_message.delete()
            return

        if starCount < result.stars:
            star_message = await chan.fetch_message(int(result.star_message_id))
            await star_message.edit(content=f"{starReaction} **{starCount}** **|** {channel.mention}")

            result.stars = starCount
            await result.save()
            return

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        data = await self._config(payload.guild_id)
        starChannel = data.get("channel")
        if not starChannel:
            return

        message = await v.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        guild = v.client.get_guild(payload.guild_id)

        chan = v.client.get_channel(int(starChannel))

        result = await Starboard.find_one(
            Starboard.guild_id == str(guild.id),
            Starboard.root_message_id == str(message.id),
        )

        if result is None:
            return

        star_message = await chan.fetch_message(int(result.star_message_id))
        await result.delete()

        await star_message.delete()


def setup(client):
    client.add_cog(starboard(client))
