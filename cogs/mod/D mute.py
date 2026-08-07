import datetime
import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild
from .mod_utils.utils import can_moderate, send_member_dm, audit_log

DURATIONS = {
    "60-sec": (datetime.timedelta(seconds=60), "60 seconds"),
    "5-min": (datetime.timedelta(minutes=5), "5 minutes"),
    "10-min": (datetime.timedelta(minutes=10), "10 minutes"),
    "1-hour": (datetime.timedelta(hours=1), "1 hour"),
    "1-day": (datetime.timedelta(days=1), "1 day"),
    "1-week": (datetime.timedelta(weeks=1), "1 week"),
}

TIMEOUT_CHOICES = {
    "60 SECS": (datetime.timedelta(seconds=60), "60 seconds"),
    "5 MINS": (datetime.timedelta(minutes=5), "5 minutes"),
    "10 MINS": (datetime.timedelta(minutes=10), "10 minutes"),
    "1 HOUR": (datetime.timedelta(hours=1), "1 hour"),
    "1 DAY": (datetime.timedelta(days=1), "1 day"),
    "1 WEEK": (datetime.timedelta(weeks=1), "1 week"),
}

def get_mute_settings(guild: discord.Guild) -> dict:
    guild_config = Guild.get(str(guild.id)).run()

    if guild_config is None:
        return {}

    moderation = guild_config.dashboard.moderation or {}

    return (
        moderation
        .get("settings", {})
        .get("mute", {})
    )

class Mute(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(name="mute", description="Mutes a member in the server")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="The member you want to mute", required=True)
    @discord.option("reason", str, description="The reason for the mute", required=False)
    async def mute(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
        allowed, error_message = can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Mute failed",
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        reason = reason or "Unspecified"

        mute_settings = get_mute_settings(ctx.guild)
        mute_type = mute_settings.get("type", "timeout")
        mute_duration = mute_settings.get("duration", "10-min")
        dm_fields = mute_settings.get("dm", [])

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action="Muted",
            reason=reason,
            dm_fields=dm_fields,
        )

        duration_text = None

        if mute_type == "role":
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")

            if muted_role is None:
                muted_role = await ctx.guild.create_role(
                    name="Muted",
                    reason="Muted role created by BobCat",
                )
            if muted_role >= ctx.guild.me.top_role:
                return await ctx.respond(
                    embed=discord.Embed(title="❌ Mute failed", description="The Muted role is above or equal to my highest role.", color=v.error),
                    ephemeral=True,
                )
            if muted_role in member.roles:
                return await ctx.respond(
                    embed=discord.Embed(title="❌ Member already muted", color=v.error),
                    ephemeral=True,
                )

            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(
                        muted_role,
                        send_messages=False,
                        speak=False,
                        add_reactions=False,
                    )
                except (discord.Forbidden, discord.HTTPException):
                    continue

            await member.add_roles(
                muted_role,
                reason=f"{ctx.author}: {reason}",
            )
        else:
            timeout_data = DURATIONS.get(
                mute_duration,
                DURATIONS["10-min"],
            )
            duration, duration_text = timeout_data
            await member.timeout_for(
                duration,
                reason=f"{ctx.author}: {reason}",
            )

        embed = discord.Embed(description=f"**Reason:** {reason}", color=v.style(ctx.guild))
        embed.set_author(icon_url=member.display_avatar.url, name=f"{member} has been muted")
        if duration_text:
            embed.add_field(
                name="Duration",
                value=duration_text,
                inline=False,
            )
        await ctx.respond(embed=embed)

        logs = discord.Embed(
            color=v.style(ctx.guild),
        )
        logs.set_author(
            icon_url=member.display_avatar.url,
            name=f"[MUTE] {member}",
        )
        logs.add_field(
            name="User",
            value=f"{member.mention} (`{member.id}`)",
            inline=True,
        )
        logs.add_field(
            name="Moderator",
            value=ctx.author.mention,
            inline=True,
        )
        logs.add_field(
            name="Reason",
            value=reason,
            inline=False,
        )
        if duration_text:
            logs.add_field(
                name="Duration",
                value=duration_text,
                inline=False,
            )

        await audit_log(ctx, "ModerationMute", logs)

    @mute.error
    async def mute_error(self, ctx, error):
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Missing permission",
                    description=(
                        "You need the `Moderate Members` permission."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, commands.BotMissingPermissions):
            v.push_notification(
                ctx.guild,
                kind="error",
                title="BobCat cannot mute members",
                description=(
                    "The mute command failed because BobCat is missing "
                    "the Moderate Members permission."
                ),
                fix="Give BobCat the Moderate Members permission.",
            )

            return await ctx.respond(
                embed=discord.Embed(
                    description=(
                        "❌ I am missing the `Moderate Members` "
                        "permission.\n\n"
                        f"Need help?\n{v.docs}/moderation/mute"
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, discord.Forbidden):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Mute failed",
                    description=(
                        "Check my permissions and role position."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        raise original

class UnMute(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="unmute",
        description="Unmutes a member",
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member",
        discord.Member,
        description="The member to unmute",
        required=True,
    )
    async def unmute(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
    ):
        allowed, error_message = can_moderate(
            ctx.guild,
            ctx.author,
            member,
        )

        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Unmute failed",
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        mute_settings = Guild.get(ctx.guild.id).run().dashboard.moderation
        mute_type = mute_settings.get("type", "timeout")
        dm_fields = mute_settings.get("dm", [])

        if mute_type == "role":
            muted_role = discord.utils.get(
                ctx.guild.roles,
                name="Muted",
            )

            if muted_role is None or muted_role not in member.roles:
                return await ctx.respond(
                    embed=discord.Embed(
                        title="❌ Member is not muted",
                        color=v.error,
                    ),
                    ephemeral=True,
                )

            await member.remove_roles(
                muted_role,
                reason=f"Unmuted by {ctx.author}",
            )

        else:
            if member.timed_out_until is None:
                return await ctx.respond(
                    embed=discord.Embed(
                        title="❌ Member is not timed out",
                        color=v.error,
                    ),
                    ephemeral=True,
                )

            await member.remove_timeout(
                reason=f"Unmuted by {ctx.author}",
            )

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action="Unmuted",
            reason="Unspecified",
            dm_fields=dm_fields,
        )

        embed = discord.Embed(
            color=v.style(ctx.guild),
        )
        embed.set_author(
            icon_url=member.display_avatar.url,
            name=f"{member} has been unmuted",
        )
        await ctx.respond(embed=embed)

        logs = discord.Embed(
            color=v.style(ctx.guild),
        )
        logs.set_author(
            icon_url=member.display_avatar.url,
            name=f"[UNMUTE] {member}",
        )
        logs.add_field(
            name="User",
            value=f"{member.mention} (`{member.id}`)",
            inline=True,
        )
        logs.add_field(
            name="Moderator",
            value=ctx.author.mention,
            inline=True,
        )
        await audit_log(
            ctx,
            "ModerationUnmute",
            logs,
        )

    @unmute.error
    async def unmute_error(self, ctx, error):
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Missing permission",
                    description=(
                        "You need the `Moderate Members` permission."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, commands.BotMissingPermissions):
            v.push_notification(
                ctx.guild,
                kind="error",
                title="BobCat cannot unmute members",
                description=(
                    "The unmute command failed because BobCat is "
                    "missing the Moderate Members permission."
                ),
                fix="Give BobCat the Moderate Members permission.",
            )

            return await ctx.respond(
                embed=discord.Embed(
                    description=(
                        "❌ I am missing the `Moderate Members` "
                        "permission.\n\n"
                        f"Need help?\n{v.docs}/moderation/unmute"
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        raise original

class Timeout(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="timeout",
        description="Temporarily times out a member",
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member",
        discord.Member,
        description="The member to time out",
        required=True,
    )
    @discord.option(
        "duration",
        str,
        description="Duration of the timeout",
        required=True,
        choices=list(TIMEOUT_CHOICES.keys()),
    )
    @discord.option(
        "reason",
        str,
        description="Reason for the timeout",
        required=False,
    )
    async def timeout(
        self,
        ctx: discord.ApplicationContext,
        member: discord.Member,
        duration: str,
        reason: str = None,
    ):
        allowed, error_message = can_moderate(
            ctx.guild,
            ctx.author,
            member,
        )

        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Timeout failed",
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        timeout_data = TIMEOUT_CHOICES.get(duration)

        if timeout_data is None:
            return await ctx.respond(
                "❌ Invalid timeout duration.",
                ephemeral=True,
            )

        mute_settings = get_mute_settings(ctx.guild.id)
        dm_fields = mute_settings.get("dm", [])

        timeout_duration, duration_text = timeout_data
        reason = reason or "Unspecified"

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action="Timed out",
            reason=reason,
            dm_fields=dm_fields,
        )

        await member.timeout_for(
            timeout_duration,
            reason=f"{ctx.author}: {reason}",
        )

        timeout_end = discord.utils.utcnow() + timeout_duration

        embed = discord.Embed(
            description=f"**Reason:** {reason}",
            timestamp=timeout_end,
            color=v.style(ctx.guild),
        )
        embed.set_author(
            icon_url=member.display_avatar.url,
            name=f"{member} has been timed out for {duration_text}",
        )
        embed.set_footer(text="Timed out until")
        await ctx.respond(embed=embed)

        logs = discord.Embed(
            color=v.style(ctx.guild),
        )
        logs.set_author(
            icon_url=member.display_avatar.url,
            name=f"[TIMEOUT] {member}",
        )
        logs.add_field(
            name="User",
            value=f"{member.mention} (`{member.id}`)",
            inline=True,
        )
        logs.add_field(
            name="Moderator",
            value=ctx.author.mention,
            inline=True,
        )
        logs.add_field(
            name="Reason",
            value=reason,
            inline=False,
        )
        logs.add_field(
            name="Duration",
            value=duration_text,
            inline=False,
        )
        await audit_log(
            ctx,
            "ModerationMute",
            logs,
        )

    @timeout.error
    async def timeout_error(self, ctx, error):
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Missing permission",
                    description=(
                        "You need the `Moderate Members` permission."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, commands.BotMissingPermissions):
            v.push_notification(
                ctx.guild,
                kind="error",
                title="BobCat cannot time out members",
                description=(
                    "The timeout command failed because BobCat is "
                    "missing the Moderate Members permission."
                ),
                fix="Give BobCat the Moderate Members permission.",
            )

            return await ctx.respond(
                embed=discord.Embed(
                    description=(
                        "❌ I am missing the `Moderate Members` "
                        "permission.\n\n"
                        f"Need help?\n{v.docs}/moderation/timeout"
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        raise original

def setup(client):
    client.add_cog(Mute(client))
    client.add_cog(UnMute(client))
    client.add_cog(Timeout(client))