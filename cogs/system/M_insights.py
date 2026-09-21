import asyncio
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

        # guild ids with a backfill running
        self.backfilling: set[str] = set()

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

    @staticmethod
    def _message_paths(message: discord.Message, hour: int) -> list[str]:
        """The counters one message adds to. Shared by the live listener and backfill."""
        paths = ["messages", f"hourly.{hour}", f"channels.{message.channel.id}"]
        if message.reference is not None:
            paths.append("replies")
        if message.attachments:
            paths.append("with_attachments")
        if "http://" in message.content or "https://" in message.content:
            paths.append("with_links")
        return paths

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
        for path in self._message_paths(message, self._local(message.guild.id, now).hour):
            self._bump(message.guild.id, path, now=now)

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


    # ── Backfill ────────────────────────────────────────────────────────────
    async def _backfill(self, guild: discord.Guild, days: int, progress) -> dict:
        """Rebuild past days from what Discord still has: message history, current members' join
        dates, and the audit log's kicks/bans. Only days before today that have no data yet are
        written (so live counts are never overwritten). Days that already have data are skipped, so
        re-running only fills gaps, e.g. after asking for more days."""
        tz = v.datetimes(guild)
        today = datetime.now(tz).date()
        first = today - timedelta(days=days)
        after = tz.localize(datetime.combine(first, datetime.min.time()))
        guild_id = str(guild.id)

        collection = InsightsDaily.get_pymongo_collection()
        taken = {doc["date"] async for doc in collection.find(
            {"guild_id": guild_id, "date": {"$gte": first.isoformat()}}, {"date": 1})}

        def wanted(date: str) -> bool:
            return first.isoformat() <= date < today.isoformat() and date not in taken

        counts, users = defaultdict(Counter), defaultdict(set)

        # Messages
        me = guild.me
        candidates = [*guild.text_channels, *guild.threads]
        channels = [c for c in candidates
                    if (p := c.permissions_for(me)).view_channel and p.read_message_history]
        skipped = len(candidates) - len(channels)
        for done, channel in enumerate(channels, 1):
            try:
                async for message in channel.history(limit=None, after=after):
                    if message.author.bot:
                        continue
                    local = message.created_at.astimezone(tz)
                    date = local.date().isoformat()
                    if not wanted(date):
                        continue
                    for path in self._message_paths(message, local.hour):
                        counts[date][path] += 1
                    users[date].add(message.author.id)
            except discord.Forbidden:
                skipped += 1
            await progress(done, len(channels))

        # Joins: only people still in the server have a joined_at
        for member in guild.members:
            if not member.bot and member.joined_at is not None:
                date = member.joined_at.astimezone(tz).date().isoformat()
                if wanted(date):
                    counts[date]["joins"] += 1

        # Leaves: the audit log only records kicks and bans (about 45 days)
        audit_log = True
        try:
            for action in (discord.AuditLogAction.kick, discord.AuditLogAction.ban):
                async for entry in guild.audit_logs(limit=None, action=action, after=after):
                    if getattr(entry.target, "bot", False):
                        continue
                    date = entry.created_at.astimezone(tz).date().isoformat()
                    if wanted(date):
                        counts[date]["leaves"] += 1
        except discord.Forbidden:
            audit_log = False

        ops = []
        for date in counts.keys() | users.keys():
            fields = {**counts[date], "active_users": [str(u) for u in users[date]], "backfilled": True}
            ops.append(UpdateOne(
                {"_id": f"{guild_id}:{date}"},
                {"$set": fields, "$setOnInsert": {"guild_id": guild_id, "date": date}},
                upsert=True,
            ))
        if ops:
            await collection.bulk_write(ops, ordered=False)

        return {
            "days": len(ops),
            "messages": sum(c["messages"] for c in counts.values()),
            "channels": len(channels),
            "skipped": skipped,
            "audit_log": audit_log,
        }

    insights = discord.SlashCommandGroup("insights", "Server insights", guild_only=True)

    @insights.command(name="backfill", description="Fill in past days of insights from your message history")
    @commands.has_permissions(manage_guild=True)
    @discord.option("days", int, description="How many days back to fill (default 30)", required=False, min_value=1, max_value=90, default=30)
    async def backfill(self, ctx: discord.ApplicationContext, days: int = 30):
        guild_id = str(ctx.guild.id)
        if guild_id in self.backfilling:
            return await ctx.respond("A backfill is already running for this server.", ephemeral=True)

        self.backfilling.add(guild_id)
        await ctx.respond("⏳ Backfilling insights... this can take a while on busy servers.", ephemeral=True)

        loop, last_edit = asyncio.get_running_loop(), 0.0

        async def progress(done: int, total: int):
            nonlocal last_edit
            if loop.time() - last_edit < 5:
                return
            last_edit = loop.time()
            try:
                await ctx.interaction.edit_original_response(content=f"⏳ Scanning channels... {done}/{total}")
            except discord.HTTPException:
                pass

        try:
            result = await self._backfill(ctx.guild, days, progress)
        except Exception:
            traceback.print_exc()
            message = "❌ The backfill failed. Nothing was saved, so you can run it again."
        else:
            message = (
                f"✅ Backfilled **{result['days']}** days from **{result['messages']:,}** messages in {result['channels']} channels.\n"
                "Joins only include members who are still here, and leaves only include kicks and bans "
                + ("from the audit log (about the last 45 days)." if result["audit_log"] else "(I can't view the audit log, so none were added).")
            )
            if result["skipped"]:
                message += f"\n{result['skipped']} channels were skipped because I can't read their history."
        finally:
            self.backfilling.discard(guild_id)

        try:
            await ctx.interaction.edit_original_response(content=message)
        except discord.HTTPException:  # the interaction token expires after 15 minutes
            await ctx.channel.send(f"{ctx.author.mention} {message}")

    @backfill.error
    async def backfill_error(self, ctx: discord.ApplicationContext, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(title="❌ Missing permission", description="You need the `Manage Server` permission.", color=v.error),
                ephemeral=True,
            )
        raise error

def setup(client):
    client.add_cog(Insights(client))
