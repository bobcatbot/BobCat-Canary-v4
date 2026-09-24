import asyncio
import datetime
import discord
from collections import Counter
from discord.ext import commands
from modules import bot as v
from modules.models import PersonalInvite, InviteJoin

# A member who leaves within this window doesn't count towards their inviter's score.
FAKE_WINDOW = datetime.timedelta(hours=24)

def is_fake(join: InviteJoin) -> bool:
    return join.left_at is not None and join.left_at - join.joined_at < FAKE_WINDOW

async def enabled(guild_id) -> bool:
    dash = await v.dashboard(guild_id)
    return dash and dash.invite_tracker.status

async def get_scores(guild_id) -> Counter:
    scores = Counter()
    for join in await InviteJoin.find(InviteJoin.guild_id == str(guild_id)).to_list():
        if not is_fake(join):
            scores[join.inviter_id] += 1
    return scores

class InviteTracker(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client
        self.uses: dict[int, dict[str, int]] = {}  # guild_id -> {code: uses}
        self.locks: dict[int, asyncio.Lock] = {}

    def lock(self, guild_id: int) -> asyncio.Lock:
        return self.locks.setdefault(guild_id, asyncio.Lock())

    async def snapshot(self, guild: discord.Guild) -> dict[str, int]:
        try:
            invites = await guild.invites()
        except discord.Forbidden:
            invites = []
        self.uses[guild.id] = {i.code: i.uses for i in invites}
        return self.uses[guild.id]

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            await self.snapshot(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.snapshot(guild)

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        self.uses.setdefault(invite.guild.id, {})[invite.code] = invite.uses or 0

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        # Deleted the moment a single-use invite is consumed, so don't drop it before
        # on_member_join has had a chance to diff against it.
        await asyncio.sleep(5)
        self.uses.get(invite.guild.id, {}).pop(invite.code, None)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        async with self.lock(member.guild.id):
            before = self.uses.get(member.guild.id, {})
            # Snapshot even while disabled so the counts are current when it's turned back on.
            after = await self.snapshot(member.guild)
            if not await enabled(member.guild.id):
                return

            used = [code for code, uses in after.items() if uses > before.get(code, 0)]
            if len(used) != 1:
                return

            personal = await PersonalInvite.find_one(
                PersonalInvite.guild_id == str(member.guild.id),
                PersonalInvite.code == used[0],
            )
            if personal is None or personal.user_id == str(member.id):
                return

            await InviteJoin(
                id=f"{member.guild.id}_{member.id}",
                guild_id=str(member.guild.id),
                member_id=str(member.id),
                inviter_id=personal.user_id,
                code=personal.code,
                joined_at=datetime.datetime.now(datetime.timezone.utc),
            ).save()

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not await enabled(member.guild.id):
            return
        join = await InviteJoin.get(f"{member.guild.id}_{member.id}")
        if join is not None and join.left_at is None:
            join.left_at = datetime.datetime.now(datetime.timezone.utc)
            await join.save()

    # ── Slash commands ─────────────────────────────────────────────────────
    @commands.slash_command(description="Display your invite link and your invite stats")
    async def invites(self, ctx: discord.ApplicationContext):
        if not await enabled(ctx.guild.id):
            return await ctx.respond(embed=discord.Embed(description="Invite Tracker is disabled", color=v.error), ephemeral=True)
        if not ctx.guild.me.guild_permissions.manage_guild:
            return await ctx.respond("❌ I need the **Manage Server** permission to track invites.", ephemeral=True)

        doc_id = f"{ctx.guild.id}_{ctx.author.id}"
        personal = await PersonalInvite.get(doc_id)
        existing = {i.code for i in await ctx.guild.invites()}

        if personal is None or personal.code not in existing:
            channel = ctx.guild.system_channel or ctx.guild.text_channels[0]
            invite = await channel.create_invite(max_age=0, max_uses=0, unique=True, reason=f"Personal invite for {ctx.author}")
            self.uses.setdefault(ctx.guild.id, {})[invite.code] = 0
            personal = PersonalInvite(id=doc_id, guild_id=str(ctx.guild.id), user_id=str(ctx.author.id), code=invite.code)
            await personal.save()

        scores = await get_scores(ctx.guild.id)
        mine = scores[str(ctx.author.id)]
        # Everyone with a score plus the caller, so a brand-new member reads 1/1 rather than 1/0.
        ranked = set(scores) | {str(ctx.author.id)}
        rank = 1 + sum(1 for uid in ranked if scores[uid] > mine)

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"{ctx.author.display_name} invites",
            description=f"Invite Link ➡️ {v.web_url}/i/{personal.code}",
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🔄 Invites", value=f"{mine} invites", inline=True)
        embed.add_field(name="🏆 Ranking", value=f"{rank}/{len(ranked)}", inline=True)
        embed.set_footer(text="🔥 Share your invite link to progress in ranking")
        await ctx.respond(embed=embed, ephemeral=True)

    @commands.slash_command(name="invites-leaderboard", description="Display the invites leaderboard")
    async def invites_leaderboard(self, ctx: discord.ApplicationContext):
        if not await enabled(ctx.guild.id):
            return await ctx.respond(embed=discord.Embed(description="Invite Tracker is disabled", color=v.error), ephemeral=True)
        scores = await get_scores(ctx.guild.id)

        desc = ""
        for idx, (user_id, score) in enumerate(scores.most_common(10), start=1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"<@{user_id}>"
            desc += f"{medal} ● {name} ● {score}\n"

        embed = discord.Embed(
            title=f"🏆 {ctx.guild.name}'s Invite Leaderboard",
            description=desc or "No invites tracked yet!",
            color=v.style(ctx.guild.id),
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(description="Check who invited a particular member")
    @discord.option("member", discord.Member, description="Select a member")
    async def inviter(self, ctx: discord.ApplicationContext, member: discord.Member):
        if not await enabled(ctx.guild.id):
            return await ctx.respond(embed=discord.Embed(description="Invite Tracker is disabled", color=v.error), ephemeral=True)
        join = await InviteJoin.get(f"{ctx.guild.id}_{member.id}")
        if join is None:
            return await ctx.respond(f"I don't know who invited {member.mention}.", ephemeral=True)
        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"{member.mention} was invited by <@{join.inviter_id}>.",
            )
        )

def setup(client):
    client.add_cog(InviteTracker(client))
