import discord
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from discord.ext import commands, tasks
from pymongo import UpdateOne
from modules import bot as v
from modules.models import InsightsDaily

class Insights(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

        # (guild_id, "YYYY-MM-DD") -> Counter of dotted `$inc` paths
        self.buffer: defaultdict[tuple[str, str], Counter] = defaultdict(Counter)

        # (guild_id, date) -> user ids that spoke: `seen` is everyone counted this process (so an id is only
        # sent once), `pending` is the ones not yet written. Mongo's $addToSet dedupes across restarts.
        self.active_seen: defaultdict[tuple[str, str], set[int]] = defaultdict(set)
        self.active_pending: defaultdict[tuple[str, str], set[int]] = defaultdict(set)

        # guild_id -> pytz timezone, refreshed every flush (v.datetimes hits the database)
        self.timezones: dict[str, object] = {}

        # (guild_id, user_id) -> [channel_id, credited_until]
        self.voice_sessions: dict[tuple[str, int], list] = {}

        self.flush_loop.start()

    def cog_unload(self):
        self.flush_loop.cancel()

    # ── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _local(self, guild_id, now: datetime) -> datetime:
        """`now` in the guild's timezone."""
        guild_id = str(guild_id)
        if guild_id not in self.timezones:
            self.timezones[guild_id] = v.datetimes(guild_id)
        return now.astimezone(self.timezones[guild_id])

    def _day(self, guild_id, now: datetime) -> str:
        return self._local(guild_id, now).strftime("%Y-%m-%d")

    def _bump(self, guild_id, path: str, amount: float = 1, now: datetime | None = None):
        self.buffer[(str(guild_id), self._day(guild_id, now or self._now()))][path] += amount

    def _credit_voice(self, key: tuple[str, int], now: datetime):
        """Move the time a member has spent in voice since the last credit into the buffer."""
        channel_id, since = self.voice_sessions[key]
        minutes = (now - since).total_seconds() / 60
        if minutes > 0:
            self._bump(key[0], "voice_minutes", minutes, now)
            self._bump(key[0], f"voice_channels.{channel_id}", minutes, now)
        self.voice_sessions[key][1] = now

    # ── Listeners ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_ready(self):
        # Members already in voice when the bot (re)starts
        now = self._now()
        for guild in self.client.guilds:
            for channel in guild.voice_channels:
                for member in channel.members:
                    if not member.bot:
                        self.voice_sessions.setdefault((str(guild.id), member.id), [channel.id, now])

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        now = message.created_at
        self._bump(message.guild.id, "messages", now=now)
        self._bump(message.guild.id, f"hourly.{self._local(message.guild.id, now).hour}", now=now)
        self._bump(message.guild.id, f"channels.{message.channel.id}", now=now)

        # Message makeup
        if message.reference is not None:
            self._bump(message.guild.id, "replies", now=now)
        if message.attachments:
            self._bump(message.guild.id, "with_attachments", now=now)
        if "http://" in message.content or "https://" in message.content:
            self._bump(message.guild.id, "with_links", now=now)

        # Daily active users
        key = (str(message.guild.id), self._day(message.guild.id, now))
        if message.author.id not in self.active_seen[key]:
            self.active_seen[key].add(message.author.id)
            self.active_pending[key].add(message.author.id)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None or (payload.member is not None and payload.member.bot):
            return
        self._bump(payload.guild_id, "reactions")
        self._bump(payload.guild_id, f"emojis.{payload.emoji}")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not member.bot:
            self._bump(member.guild.id, "joins")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        self._bump(member.guild.id, "leaves")

        # Retention: how long they stayed
        if member.joined_at is not None:
            stayed = self._now() - member.joined_at
            bucket = ("1d" if stayed < timedelta(days=1) else
                      "7d" if stayed < timedelta(days=7) else
                      "30d" if stayed < timedelta(days=30) else "older")
            self._bump(member.guild.id, f"leave_age.{bucket}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot or before.channel == after.channel:
            return
        key = (str(member.guild.id), member.id)
        now = self._now()

        if key in self.voice_sessions:
            self._credit_voice(key, now)
            del self.voice_sessions[key]
        if after.channel is not None:
            self.voice_sessions[key] = [after.channel.id, now]

    @commands.Cog.listener()
    async def on_application_command_completion(self, ctx: discord.ApplicationContext):
        if ctx.guild is not None:
            self._bump(ctx.guild.id, f"commands.{ctx.command.qualified_name}")

    # ── Flush ───────────────────────────────────────────────────────────────
    @tasks.loop(seconds=30)
    async def flush_loop(self):
        now = self._now()
        self.timezones = {str(guild.id): v.datetimes(guild) for guild in self.client.guilds}
        for key in self.voice_sessions:
            self._credit_voice(key, now)

        buffer, self.buffer = self.buffer, defaultdict(Counter)
        pending, self.active_pending = self.active_pending, defaultdict(set)

        # guild_id -> {date: Counter} / {date: user ids}, so the per-guild loop below doesn't rescan them
        activity, active = defaultdict(dict), defaultdict(dict)
        for (guild_id, date), counts in buffer.items():
            activity[guild_id][date] = counts
        for (guild_id, date), user_ids in pending.items():
            active[guild_id][date] = user_ids

        daily = []
        for guild in self.client.guilds:
            guild_id = str(guild.id)
            days, users = activity.get(guild_id, {}), active.get(guild_id, {})
            today = self._day(guild_id, now)

            # Every day with buffered activity, plus today for the member_count / boost snapshot
            for date in days.keys() | users.keys() | {today}:
                update = {
                    "$setOnInsert": {"guild_id": guild_id, "date": date},
                    "$set": {
                        "member_count": guild.member_count,
                        "boosts": guild.premium_subscription_count,
                        "boost_tier": guild.premium_tier,
                    },
                }
                if counts := days.get(date):
                    update["$inc"] = dict(counts)
                if user_ids := users.get(date):
                    update["$addToSet"] = {"active_users": {"$each": [str(u) for u in user_ids]}}
                daily.append(UpdateOne({"_id": f"{guild_id}:{date}"}, update, upsert=True))

        # Only today's ids are worth remembering; older days are written and done
        for key in list(self.active_seen):
            if key[1] != self._day(key[0], now):
                del self.active_seen[key]

        try:
            if daily:
                await InsightsDaily.get_pymongo_collection().bulk_write(daily, ordered=False)
        except Exception:
            print("❌ Insights flush failed:")
            traceback.print_exc()

    @flush_loop.before_loop
    async def before_flush_loop(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(Insights(client))
