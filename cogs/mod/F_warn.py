import discord
from datetime import datetime, timezone
from discord.ext import commands

from modules import bot as v
from modules.models import Guild, Warning
from ._helpers import can_moderate, send_member_dm, audit_log

async def get_member_warnings(
    guild: discord.Guild,
    member: discord.Member,
) -> list[Warning]:
    return await Warning.find(
        Warning.guild_id == str(guild.id),
        Warning.user_id == str(member.id),
    ).to_list()

async def add_member_warning(
    guild: discord.Guild,
    member: discord.Member,
    moderator: discord.Member,
    reason: str,
) -> Warning:
    warning = Warning(
        guild_id=str(guild.id),
        user_id=str(member.id),
        case=v.uuid(8, strCase="upper/lower/nums"),
        reason=reason,
        moderator_id=str(moderator.id),
        created_at=datetime.now(timezone.utc),
    )

    await warning.insert()
    return warning

async def delete_member_warning(
    guild: discord.Guild,
    member: discord.Member,
    case: str,
) -> Warning | None:
    warning = await Warning.find_one(
        Warning.guild_id == str(guild.id),
        Warning.user_id == str(member.id),
        Warning.case == case,
    )

    if warning is None:
        return None

    await warning.delete()
    return warning

async def clear_member_warnings(
    guild: discord.Guild,
    member: discord.Member,
) -> bool:
    warnings = await get_member_warnings(guild, member)

    if not warnings:
        return False

    for warning in warnings:
        await warning.delete()

    return True

class Warn(commands.Cog):
    def __init__(self, client):
        self.client = client

# Warn [Member] {reason}
    @commands.slash_command(
        name="warn",
        description=v.t.msg(None, "warn.cmd.description"),
        name_localizations=v.t.localizations("warn.cmd.name"),
        description_localizations=v.t.localizations("warn.cmd.description"),
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "warn.cmd.options.member.description"),
        name_localizations=v.t.localizations("warn.cmd.options.member.name"),
        description_localizations=v.t.localizations("warn.cmd.options.member.description"),
        required=True,
    )
    @discord.option(
        "reason",
        description=v.t.msg(None, "warn.cmd.options.reason.description"),
        name_localizations=v.t.localizations("warn.cmd.options.reason.name"),
        description_localizations=v.t.localizations("warn.cmd.options.reason.description"),
        required=False,
    )
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        reason = reason or v.t.msg(ctx.guild, "mod.helpers.unspecified_reason")

        warning = await add_member_warning(
            guild=ctx.guild,
            member=member,
            moderator=ctx.author,
            reason=reason,
        )

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=v.t.msg(ctx.guild, "warn.reason_case_line", reason=reason, case=warning.case),
        )
        embed.set_author(icon_url=member.avatar.url, name=v.t.msg(ctx.guild, "warn.success_author", member=member))
        await ctx.respond(embed=embed)

        dm_fields = (await Guild.get(str(ctx.guild.id))).dashboard.moderation.settings.warn.dm

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.warned"),
            reason=reason,
            dm_fields=dm_fields,
        )

        logs = discord.Embed(color=v.style(ctx.guild.id))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "warn.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=member.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=reason)
        logs.add_field(name=v.t.msg(ctx.guild, "warn.case_field"), value=v.t.msg(ctx.guild, "warn.case_value", case=warning.case))
        await audit_log(ctx, "ModerationWarn", logs)

    @warn.error
    async def warn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed = discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "warn.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot warn members",
                description="The warn command failed because BobCat is missing the Time out Members permission.",
                fix=f"{v.docs}/moderation/warn",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "warn.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "warn.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/warn"),
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

class UnWarn(commands.Cog):
    def __init__(self, client):
        self.client = client
    
# Unwarn
    @commands.slash_command(
        name="unwarn",
        description=v.t.msg(None, "unwarn.cmd.description"),
        name_localizations=v.t.localizations("unwarn.cmd.name"),
        description_localizations=v.t.localizations("unwarn.cmd.description"),
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "unwarn.cmd.options.member.description"),
        name_localizations=v.t.localizations("unwarn.cmd.options.member.name"),
        description_localizations=v.t.localizations("unwarn.cmd.options.member.description"),
        required=True,
    )
    @discord.option(
        "case",
        description=v.t.msg(None, "unwarn.cmd.options.case.description"),
        name_localizations=v.t.localizations("unwarn.cmd.options.case.name"),
        description_localizations=v.t.localizations("unwarn.cmd.options.case.description"),
        required=True,
    )
    async def unwarn(self, ctx, member: discord.Member, case):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        warnings = await get_member_warnings(guild=ctx.guild, member=member)

        if not warnings or warnings is None:
            embed = discord.Embed(title=v.t.msg(ctx.guild, "unwarn.no_warnings_title"), color=v.error)
            return await ctx.respond(embed=embed)

        warning = await delete_member_warning(guild=ctx.guild, member=member, case=case)
        # if warn is None:
        #     embed = discord.Embed(title="❌ Failed to get user warnings", color=v.error)
        #     return await ctx.respond(embed=embed)
        if not warning:
            embed = discord.Embed(title=v.t.msg(ctx.guild, "unwarn.invalid_case_title"), color=v.error)
            return await ctx.respond(embed=embed)

        embed = discord.Embed(color=v.style(ctx.guild.id))
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "unwarn.success_author", member=member))
        embed.add_field(name=v.t.msg(ctx.guild, "unwarn.infraction_field"), value=v.t.msg(ctx.guild, "unwarn.infraction_value", reason=warning.reason, case=warning.case), inline=False)
        await ctx.respond(embed=embed)

        dm_fields = (await Guild.get(str(ctx.guild.id))).dashboard.moderation.settings.warn.dm

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.unwarned"),
            reason=warning.reason,
            dm_fields=dm_fields,
        )

        logs = discord.Embed(color=v.style(ctx.guild.id))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "unwarn.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=member.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=v.t.msg(ctx.guild, "unwarn.log_reason_removed", case=warning.case))
        await audit_log(ctx, "ModerationUnwarn", logs)

    @unwarn.error
    async def unwarn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "unwarn.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot unwarn members",
                description="The unwarn command failed because BobCat is missing the Time out Members permission.",
                fix=f"{v.docs}/moderation/unwarn",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "unwarn.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "unwarn.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/unwarn"),
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

class Warnings(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="warnings",
        description=v.t.msg(None, "warnings.cmd.description"),
        name_localizations=v.t.localizations("warnings.cmd.name"),
        description_localizations=v.t.localizations("warnings.cmd.description"),
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "warnings.cmd.options.member.description"),
        name_localizations=v.t.localizations("warnings.cmd.options.member.name"),
        description_localizations=v.t.localizations("warnings.cmd.options.member.description"),
        required=False,
    )
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        warnings = await get_member_warnings(guild=ctx.guild, member=member)

        if not warnings:
            embed = discord.Embed(color=v.style(ctx.guild.id))
            embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "warnings.no_warnings_author", member=member))
            return await ctx.respond(embed=embed)

        warnings = sorted(
            warnings,
            key=lambda warning: warning.created_at,
            reverse=True,
        )

        warning_lines = []

        for warning in warnings[:10]:
            created_at = discord.utils.format_dt(
                warning.created_at,
                style="R",
            )
            warning_lines.append(
                v.t.msg(ctx.guild, "warnings.line_format", case=warning.case, time=created_at, reason=warning.reason)
            )

        embed = discord.Embed(color=v.style(ctx.guild.id))
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "warnings.author_title", member=member))
        embed.add_field(name=v.t.msg(ctx.guild, "warnings.total_field"), value=v.t.msg(ctx.guild, "warnings.total_value", count=len(warnings)), inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "warnings.last10_field"), value="\n".join(warning_lines), inline=False)

        # Both view classes are (re)defined per-invocation, not at module level
        # like the rps/ttt button views - ctx is captured by closure, so unlike
        # those, these button labels CAN follow the guild's language.
        canInteract = not ctx.author.guild_permissions.moderate_members
        class Confirm(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(label=v.t.msg(ctx.guild, "warnings.buttons.yes"), style=discord.ButtonStyle.red)
            async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return
                for child in self.children:
                    child.disabled = True

                await clear_member_warnings(guild=ctx.guild, member=member)

                cleared_embed = discord.Embed(color=v.style(ctx.guild.id))
                cleared_embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "warnings.no_warnings_author", member=member))
                await interaction.response.edit_message(embed=cleared_embed, view=None)

            @discord.ui.button(label=v.t.msg(ctx.guild, "warnings.buttons.no"), style=discord.ButtonStyle.gray)
            async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return
                for child in self.children:
                    child.disabled = True
                cancelled_embed = discord.Embed(description=v.t.msg(ctx.guild, "warnings.cancelled_description"), color=v.error)
                await interaction.response.edit_message(embed=cancelled_embed, view=self)

        class Infractions(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(label=v.t.msg(ctx.guild, "warnings.buttons.remove_all"), style=discord.ButtonStyle.red, disabled=canInteract)
            async def infractions(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return

                confirmation_embed = discord.Embed(
                    description=v.t.msg(ctx.guild, "warnings.confirm_description", member=member),
                    color=v.error,
                )
                await interaction.response.send_message(embed=confirmation_embed, view=Confirm(), ephemeral=True)

        await ctx.respond(embed=embed, view=Infractions())

    @warnings.error
    async def warnings_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "warnings.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot warn members",
                description="The warnings command failed because BobCat is missing the Time out Members permission.",
                fix=f"{v.docs}/moderation/warnings",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "warnings.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "warnings.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/warnings"),
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
    client.add_cog(Warn(client))
    client.add_cog(UnWarn(client))
    client.add_cog(Warnings(client))