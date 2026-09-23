import datetime
import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild, MuteSettingsConfig
from ._helpers import can_moderate, send_member_dm, audit_log

# The 2nd tuple element is a mod.durations.<key> translation key, not display
# text - DURATIONS/TIMEOUT_CHOICES keys themselves stay fixed English (they're
# either a dashboard config value or the option's `value=` sent back to the
# bot), only the displayed duration text is looked up per-guild from that key.
DURATIONS = {
    "60-sec": (datetime.timedelta(seconds=60), "sixty_sec"),
    "5-min": (datetime.timedelta(minutes=5), "five_min"),
    "10-min": (datetime.timedelta(minutes=10), "ten_min"),
    "1-hour": (datetime.timedelta(hours=1), "one_hour"),
    "1-day": (datetime.timedelta(days=1), "one_day"),
    "1-week": (datetime.timedelta(weeks=1), "one_week"),
}

TIMEOUT_CHOICES = {
    "60 SECS": (datetime.timedelta(seconds=60), "sixty_sec"),
    "5 MINS": (datetime.timedelta(minutes=5), "five_min"),
    "10 MINS": (datetime.timedelta(minutes=10), "ten_min"),
    "1 HOUR": (datetime.timedelta(hours=1), "one_hour"),
    "1 DAY": (datetime.timedelta(days=1), "one_day"),
    "1 WEEK": (datetime.timedelta(weeks=1), "one_week"),
}

async def get_mute_settings(guild: discord.Guild) -> MuteSettingsConfig:
    guild_config = await Guild.get(str(guild.id))
    if guild_config is None:
        return MuteSettingsConfig()
    return guild_config.dashboard.moderation.settings.mute

class Mute(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="mute",
        description=v.t.msg(None, "mute.cmd.description"),
        name_localizations=v.t.localizations("mute.cmd.name"),
        description_localizations=v.t.localizations("mute.cmd.description"),
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "mute.cmd.options.member.description"),
        name_localizations=v.t.localizations("mute.cmd.options.member.name"),
        description_localizations=v.t.localizations("mute.cmd.options.member.description"),
        required=True,
    )
    @discord.option(
        "reason", str,
        description=v.t.msg(None, "mute.cmd.options.reason.description"),
        name_localizations=v.t.localizations("mute.cmd.options.reason.name"),
        description_localizations=v.t.localizations("mute.cmd.options.reason.description"),
        required=False,
    )
    async def mute(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "mute.failed_title"), description=error_message, color=v.error), ephemeral=True)

        reason = reason or v.t.msg(ctx.guild, "mod.helpers.unspecified_reason")

        mute_settings = await get_mute_settings(ctx.guild)
        mute_type = mute_settings.type or "timeout"
        mute_duration = mute_settings.duration or "10-min"
        dm_fields = mute_settings.dm

        duration_text = None

        if mute_type == "role":
            # "Muted" is a persistent Discord role name looked up across calls -
            # deliberately not translated (changing it per-guild-language would
            # risk creating a duplicate role every time the language differs).
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if muted_role is None:
                muted_role = await ctx.guild.create_role(name="Muted", reason="Muted role created by BobCat")
            if muted_role >= ctx.guild.me.top_role:
                return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "mute.failed_title"), description=v.t.msg(ctx.guild, "mute.role_above_mine"), color=v.error), ephemeral=True)
            if muted_role in member.roles:
                return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "mute.already_muted_title"), color=v.error), ephemeral=True)

            for channel in ctx.guild.channels:
                try:
                    await channel.set_permissions(muted_role, send_messages=False, speak=False, add_reactions=False)
                except (discord.Forbidden, discord.HTTPException):
                    continue

            await member.add_roles(muted_role, reason=f"{ctx.author}: {reason}")

        else:
            duration, duration_key = DURATIONS.get(mute_duration, DURATIONS["10-min"])
            duration_text = v.t.msg(ctx.guild, f"mod.durations.{duration_key}")
            await member.timeout_for(
                duration,
                reason=f"{ctx.author}: {reason}"
            )

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.muted"),
            reason=reason,
            dm_fields=dm_fields,
        )

        embed = discord.Embed(description=v.t.msg(ctx.guild, "mod.helpers.reason_line", reason=reason), color=v.style(ctx.guild))
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "mute.success_author", member=member))
        if duration_text:
            embed.add_field(name=v.t.msg(ctx.guild, "mod.helpers.duration_field"), value=duration_text, inline=False)
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "mute.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=f"{member.mention} (`{member.id}`)", inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=reason, inline=False)
        if duration_text:
            logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.duration_field"), value=duration_text, inline=False)
        await audit_log(ctx, "ModerationMute", logs)

    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "mute.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot mute members",
                description="The mute command failed because BobCat is missing the Time out Members permission.",
                fix=f"{v.docs}/moderation/mute",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mute.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "mute.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/mute"),
                    color=v.error,
                ),
                ephemeral=True
            )

        await ctx.respond(
            embed=discord.Embed(
                title=v.t.msg(ctx.guild, "mod.common_errors.generic_title"),
                description=v.t.msg(ctx.guild, "mod.common_errors.generic_description"),
                color=v.error,
            ),
            ephemeral=True,
        )
        raise error

class UnMute(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="unmute",
        description=v.t.msg(None, "unmute.cmd.description"),
        name_localizations=v.t.localizations("unmute.cmd.name"),
        description_localizations=v.t.localizations("unmute.cmd.description"),
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "unmute.cmd.options.member.description"),
        name_localizations=v.t.localizations("unmute.cmd.options.member.name"),
        description_localizations=v.t.localizations("unmute.cmd.options.member.description"),
        required=True,
    )
    async def unmute(self, ctx: discord.ApplicationContext, member: discord.Member):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "unmute.failed_title"), description=error_message, color=v.error), ephemeral=True)

        mute_settings = await get_mute_settings(ctx.guild)
        mute_type = mute_settings.type or "timeout"
        dm_fields = mute_settings.dm

        if mute_type == "role":
            muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
            if muted_role is None or muted_role not in member.roles:
                return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "unmute.not_muted_title"), color=v.error), ephemeral=True)
            await member.remove_roles(muted_role, reason=f"Unmuted by {ctx.author}")

        else:
            if member.timed_out_until is None:
                return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "unmute.not_timed_out_title"), color=v.error), ephemeral=True)
            await member.timeout(None, reason=f"Unmuted by {ctx.author}")

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.unmuted"),
            reason=v.t.msg(ctx.guild, "mod.helpers.unspecified_reason"),
            dm_fields=dm_fields,
        )

        embed = discord.Embed(color=v.style(ctx.guild))
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "unmute.success_author", member=member))
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "unmute.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=f"{member.mention} (`{member.id}`)", inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention, inline=True)
        await audit_log(ctx, "ModerationUnmute", logs)

    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "unmute.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot unmute members",
                description="The unmute command failed because BobCat is missing the Time out Members permission.",
                fix=f"{v.docs}/moderation/unmute",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "unmute.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "unmute.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/unmute"),
                    color=v.error,
                ),
                ephemeral=True
            )

        await ctx.respond(
            embed=discord.Embed(
                title=v.t.msg(ctx.guild, "mod.common_errors.generic_title"),
                description=v.t.msg(ctx.guild, "mod.common_errors.generic_description"),
                color=v.error,
            ),
            ephemeral=True,
        )
        raise error

class Timeout(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="timeout",
        description=v.t.msg(None, "timeout.cmd.description"),
        name_localizations=v.t.localizations("timeout.cmd.name"),
        description_localizations=v.t.localizations("timeout.cmd.description"),
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "timeout.cmd.options.member.description"),
        name_localizations=v.t.localizations("timeout.cmd.options.member.name"),
        description_localizations=v.t.localizations("timeout.cmd.options.member.description"),
        required=True,
    )
    @discord.option(
        "duration", str,
        description=v.t.msg(None, "timeout.cmd.options.duration.description"),
        name_localizations=v.t.localizations("timeout.cmd.options.duration.name"),
        description_localizations=v.t.localizations("timeout.cmd.options.duration.description"),
        required=True,
        # choice value= stays the fixed TIMEOUT_CHOICES key (what comes back as
        # `duration` below); only the picker's displayed name= is translated.
        choices=[
            discord.OptionChoice(
                name=v.t.msg(None, f"mod.durations.{translation_key}"),
                value=raw_key,
                name_localizations=v.t.localizations(f"mod.durations.{translation_key}"),
            )
            for raw_key, (_, translation_key) in TIMEOUT_CHOICES.items()
        ],
    )
    @discord.option(
        "reason", str,
        description=v.t.msg(None, "timeout.cmd.options.reason.description"),
        name_localizations=v.t.localizations("timeout.cmd.options.reason.name"),
        description_localizations=v.t.localizations("timeout.cmd.options.reason.description"),
        required=False,
    )
    async def timeout(self, ctx: discord.ApplicationContext, member: discord.Member, duration: str, reason: str = None):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(embed=discord.Embed(title=v.t.msg(ctx.guild, "timeout.failed_title"), description=error_message, color=v.error), ephemeral=True)

        timeout_data = TIMEOUT_CHOICES.get(duration)
        if timeout_data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "timeout.invalid_duration"), ephemeral=True)

        mute_settings = await get_mute_settings(ctx.guild)
        dm_fields = mute_settings.dm

        timeout_duration, duration_key = timeout_data
        duration_text = v.t.msg(ctx.guild, f"mod.durations.{duration_key}")
        reason = reason or v.t.msg(ctx.guild, "mod.helpers.unspecified_reason")

        await member.timeout_for(
            timeout_duration,
            reason=f"{ctx.author}: {reason}"
        )

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.timed_out"),
            reason=reason,
            dm_fields=dm_fields
        )

        timeout_end = discord.utils.utcnow() + timeout_duration

        embed = discord.Embed(
            color=v.style(ctx.guild),
            description=v.t.msg(ctx.guild, "mod.helpers.reason_line", reason=reason),
            timestamp=timeout_end,
        )
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "timeout.success_author", member=member, duration=duration_text))
        embed.set_footer(text=v.t.msg(ctx.guild, "timeout.footer"))
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "timeout.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=f"{member.mention} (`{member.id}`)", inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=reason, inline=False)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.duration_field"), value=duration_text, inline=False)
        await audit_log(ctx, "ModerationMute", logs)

    @timeout.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "timeout.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot time out members",
                description="The timeout command failed because BobCat is missing the Time out Members permission.",
                fix=f"{v.docs}/moderation/timeout",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "timeout.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "timeout.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/timeout"),
                    color=v.error,
                ),
                ephemeral=True
            )

        await ctx.respond(
            embed=discord.Embed(
                title=v.t.msg(ctx.guild, "mod.common_errors.generic_title"),
                description=v.t.msg(ctx.guild, "mod.common_errors.generic_description"),
                color=v.error,
            ),
            ephemeral=True,
        )
        raise error

def setup(client):
    client.add_cog(Mute(client))
    client.add_cog(UnMute(client))
    client.add_cog(Timeout(client))