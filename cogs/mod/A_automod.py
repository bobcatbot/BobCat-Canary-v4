import re
import time
import datetime
import discord
from collections import defaultdict, deque
from discord.ext import commands, tasks

from modules import bot as v
from modules.models import Guild, Warning, AntiLinkConfig, AntiSpamConfig, GhostPingConfig, ExcessiveCapsConfig
from ._helpers import can_moderate, send_member_dm, audit_log
from ._scam_domains import SCAM_DOMAINS

INVITE_RE = re.compile(r"(?:discord\.gg|discord(?:app)?\.com/invite)/\S+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"(?:https?://)?([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+)", re.IGNORECASE)

MUTE_DURATION = datetime.timedelta(minutes=10)
GHOST_PING_MAX_AGE = 600  # hard cap (seconds) on how long an unresolved mention is tracked, regardless of per-guild delete_window


async def get_automod_config(guild: discord.Guild) -> tuple[AntiLinkConfig, AntiSpamConfig, GhostPingConfig, ExcessiveCapsConfig]:
    guild_config = await Guild.get(str(guild.id))
    if guild_config is None:
        return AntiLinkConfig(), AntiSpamConfig(), GhostPingConfig(), ExcessiveCapsConfig()
    automod = guild_config.dashboard.moderation.automod
    return automod.antilink, automod.antispam, automod.ghostping, automod.caps

def extract_domains(content: str) -> set[str]:
    return {match.group(1).lower() for match in DOMAIN_RE.finditer(content)}

def caps_percentage(content: str) -> float:
    """Share of alphabetic characters that are uppercase, 0-100. Non-letters
    (numbers, punctuation, emoji, spaces) don't count either way."""
    letters = [c for c in content if c.isalpha()]
    if not letters:
        return 0.0
    upper = sum(1 for c in letters if c.isupper())
    return (upper / len(letters)) * 100

def is_whitelisted(channel: discord.abc.GuildChannel, roles: list[discord.Role], config) -> bool:
    if str(channel.id) in config.whitelist_channels:
        return True
    role_ids = {str(role.id) for role in roles}
    return bool(role_ids & set(config.whitelist_roles))


async def apply_action(guild: discord.Guild, member: discord.Member, moderator: discord.Member, action: str, reason: str, dm: list[str]) -> str | None:
    """Runs the warn/mute/kick/ban side of an automod action and DMs the member.
    Returns the human-readable action label, or None if nothing happened
    (action is "delete", the member is immune, or the action failed)."""
    if action == "delete":
        return None

    allowed, _ = await can_moderate(guild, moderator, member)
    if not allowed:
        return None

    action_label = None
    try:
        if action == "warn":
            action_label = v.t.msg(guild, "mod.actions.warned")
            await Warning(
                guild_id=str(guild.id),
                user_id=str(member.id),
                case=v.uuid(8, strCase="upper/lower/nums"),
                reason=reason,
                moderator_id=str(moderator.id),
            ).insert()

        elif action == "mute":
            action_label = v.t.msg(guild, "mod.actions.muted")
            await member.timeout_for(MUTE_DURATION, reason=reason)

        elif action == "kick":
            action_label = v.t.msg(guild, "mod.actions.kicked")
            await member.kick(reason=reason)

        elif action == "ban":
            action_label = v.t.msg(guild, "mod.actions.banned")
            await member.ban(reason=reason)
    except (discord.Forbidden, discord.HTTPException):
        return None

    if action_label is None:
        return None

    await send_member_dm(
        member=member,
        guild=guild,
        moderator=moderator,
        action=action_label,
        reason=reason,
        dm_fields=dm,
    )

    return action_label

def build_log_embed(guild: discord.Guild, member: discord.Member, reason: str, action_label: str, log_title_key: str, channel: discord.abc.GuildChannel | None = None) -> discord.Embed:
    """log_title_key is a full mod.<category>.log_title translation key
    (e.g. "automod.antilink.log_title"), not a bare tag string - the
    bracketed tag itself ("ANTILINK" etc.) stays baked into that template,
    same convention as kick/ban/mute's own "[KICK] {member}" style keys."""
    logs = discord.Embed(color=v.style(guild), description=v.t.msg(guild, "mod.helpers.reason_line", reason=reason))
    logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(guild, log_title_key, member=member))
    logs.add_field(name=v.t.msg(guild, "mod.helpers.log_fields.user"), value=f"{member.mention} (`{member.id}`)", inline=True)
    if channel is not None:
        logs.add_field(name=v.t.msg(guild, "automod.channel_field"), value=channel.mention, inline=True)
    logs.add_field(name=v.t.msg(guild, "mod.helpers.dm_fields.action"), value=action_label, inline=True)
    logs.set_footer(icon_url="https://cdn.discordapp.com/emojis/957251535425900545.webp?size=56", text=v.t.msg(guild, "automod.log_footer"))
    return logs

async def punish(message: discord.Message, config, reason: str, event: str, log_title: str):
    guild = message.guild
    member = message.author
    moderator = guild.me

    try:
        await message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

    action_label = await apply_action(guild, member, moderator, config.action, reason, config.dm)
    if action_label is None:
        return

    logs = build_log_embed(guild, member, reason, action_label, log_title, message.channel)
    await audit_log(message, event, logs)


class AntiLink(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        antilink, *_ = await get_automod_config(message.guild)
        if not antilink.status:
            return

        if is_whitelisted(message.channel, message.author.roles, antilink):
            return

        content = message.content

        if antilink.block_invites and INVITE_RE.search(content):
            await punish(message, antilink, v.t.msg(message.guild, "automod.antilink.invite_reason"), "ModerationAntiLink", "automod.antilink.log_title")
            return

        if antilink.block_scam_links:
            domains = extract_domains(content)
            if domains & SCAM_DOMAINS:
                await punish(message, antilink, v.t.msg(message.guild, "automod.antilink.scam_reason"), "ModerationAntiLink", "automod.antilink.log_title")
                return


class AntiSpam(commands.Cog):
    def __init__(self, client):
        self.client = client
        # (guild_id, user_id) -> deque[timestamp]
        self.history: dict[tuple[int, int], deque] = defaultdict(deque)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        _, antispam, *_ = await get_automod_config(message.guild)
        if not antispam.status:
            return

        if is_whitelisted(message.channel, message.author.roles, antispam):
            return

        key = (message.guild.id, message.author.id)
        now = time.monotonic()
        bucket = self.history[key]
        bucket.append(now)

        while bucket and now - bucket[0] > antispam.interval:
            bucket.popleft()

        if len(bucket) < antispam.threshold:
            return

        bucket.clear()
        await punish(message, antispam, v.t.msg(message.guild, "automod.antispam.reason"), "ModerationAntiSpam", "automod.antispam.log_title")


class GhostPing(commands.Cog):
    """Catches users who ping someone then delete or edit-out the mention
    before anyone can react to it."""

    def __init__(self, client):
        self.client = client
        # message_id -> {guild_id, channel_id, author_id, timestamp, mention_count}
        self.pending: dict[int, dict] = {}
        self.cleanup_pending.start()

    def cog_unload(self):
        self.cleanup_pending.cancel()

    @tasks.loop(minutes=5)
    async def cleanup_pending(self):
        cutoff = time.monotonic() - GHOST_PING_MAX_AGE
        stale = [mid for mid, data in self.pending.items() if data["timestamp"] < cutoff]
        for mid in stale:
            self.pending.pop(mid, None)

    @cleanup_pending.before_loop
    async def before_cleanup_pending(self):
        await self.client.wait_until_ready()

    @staticmethod
    def _has_mention(message: discord.Message) -> bool:
        return bool(message.mentions or message.role_mentions or message.mention_everyone)

    @staticmethod
    def _mention_count(message: discord.Message) -> int:
        return len(message.mentions) + len(message.role_mentions) + (1 if message.mention_everyone else 0)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        if not self._has_mention(message):
            return

        _, _, ghostping, _ = await get_automod_config(message.guild)
        if not ghostping.status:
            return

        if is_whitelisted(message.channel, message.author.roles, ghostping):
            return

        self.pending[message.id] = {
            "guild_id": message.guild.id,
            "channel_id": message.channel.id,
            "author_id": message.author.id,
            "timestamp": time.monotonic(),
            "mention_count": self._mention_count(message),
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.id not in self.pending:
            return
        if self._has_mention(after):
            return  # mention is still there, not a ghost ping
        await self._trigger(before.id)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.message_id not in self.pending:
            return
        await self._trigger(payload.message_id)

    async def _trigger(self, message_id: int):
        data = self.pending.pop(message_id, None)
        if data is None:
            return

        guild = self.client.get_guild(data["guild_id"])
        if guild is None:
            return

        _, _, ghostping, _ = await get_automod_config(guild)
        if not ghostping.status:
            return

        if time.monotonic() - data["timestamp"] > ghostping.delete_window:
            return

        member = guild.get_member(data["author_id"])
        if member is None:
            return  # they've already left, nothing to punish

        moderator = guild.me
        reason = v.t.msg(guild, "automod.ghostping.reason", count=data['mention_count'])

        action_label = await apply_action(guild, member, moderator, ghostping.action, reason, ghostping.dm)
        if action_label is None:
            return

        channel = guild.get_channel(data["channel_id"])

        logs = build_log_embed(guild, member, reason, action_label, "automod.ghostping.log_title", channel)
        await audit_log(guild, "ModerationGhostPing", logs)


class ExcessiveCaps(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        *_, caps = await get_automod_config(message.guild)
        if not caps.status:
            return

        if is_whitelisted(message.channel, message.author.roles, caps):
            return

        content = message.content
        if len(content) < caps.min_length:
            return

        if caps_percentage(content) < caps.threshold:
            return

        await punish(message, caps, v.t.msg(message.guild, "automod.caps.reason"), "ModerationCaps", "automod.caps.log_title")


def setup(client):
    client.add_cog(AntiLink(client))
    client.add_cog(AntiSpam(client))
    client.add_cog(GhostPing(client))
    client.add_cog(ExcessiveCaps(client))