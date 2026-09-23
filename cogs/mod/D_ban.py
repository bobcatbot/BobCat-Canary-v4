import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild
from ._helpers import can_moderate, send_member_dm, audit_log

class Ban(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="ban",
        description=v.t.msg(None, "ban.cmd.description"),
        name_localizations=v.t.localizations("ban.cmd.name"),
        description_localizations=v.t.localizations("ban.cmd.description"),
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "ban.cmd.options.member.description"),
        name_localizations=v.t.localizations("ban.cmd.options.member.name"),
        description_localizations=v.t.localizations("ban.cmd.options.member.description"),
        required=True,
    )
    @discord.option(
        "reason", str,
        description=v.t.msg(None, "ban.cmd.options.reason.description"),
        name_localizations=v.t.localizations("ban.cmd.options.reason.name"),
        description_localizations=v.t.localizations("ban.cmd.options.reason.description"),
        required=False,
    )
    @discord.option(
        "delete_messages", int,
        description=v.t.msg(None, "ban.cmd.options.delete_messages.description"),
        name_localizations=v.t.localizations("ban.cmd.options.delete_messages.name"),
        description_localizations=v.t.localizations("ban.cmd.options.delete_messages.description"),
        required=False, min_value=0, max_value=7,
    )
    async def ban(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None, delete_messages: int = None):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "ban.failed_title"),
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        reason = reason or v.t.msg(ctx.guild, "mod.helpers.unspecified_reason")

        mod_data = (await Guild.get(str(ctx.guild.id))).dashboard.moderation
        dm_fields = mod_data.settings.ban.dm
        default_delete_days = mod_data.settings.ban.deleteMessageDays

        try:
            default_delete_days = int(default_delete_days)
        except (TypeError, ValueError):
            default_delete_days = 0

        delete_days = (
            default_delete_days
            if delete_messages is None
            else delete_messages
        )

        delete_days = max(0, min(int(delete_days), 7))

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.banned"),
            reason=reason,
            dm_fields=dm_fields,
        )

        if v.PY_ENV == "production":
            await ctx.guild.ban(
                user=member,
                reason=f"{ctx.author}: {reason}",
                delete_message_days=delete_days,
            )

        embed = discord.Embed(
            description=v.t.msg(ctx.guild, "ban.reason_delete_line", reason=reason, days=delete_days),
            color=v.style(ctx.guild),
        )
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "ban.success_author", member=member))
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "ban.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=member.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=reason, inline=False)
        logs.add_field(name=v.t.msg(ctx.guild, "ban.deleted_field"), value=v.t.msg(ctx.guild, "ban.deleted_value", days=delete_days), inline=False)
        await audit_log(ctx, "ModerationBan", logs)

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "ban.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot ban members",
                description="The ban command failed because BobCat is missing the Ban Members permission.",
                fix=f"{v.docs}/moderation/ban",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "ban.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "ban.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/ban"),
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

class UnBan(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="unban",
        description=v.t.msg(None, "unban.cmd.description"),
        name_localizations=v.t.localizations("unban.cmd.name"),
        description_localizations=v.t.localizations("unban.cmd.description"),
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @discord.option(
        "user_id", str,
        description=v.t.msg(None, "unban.cmd.options.user_id.description"),
        name_localizations=v.t.localizations("unban.cmd.options.user_id.name"),
        description_localizations=v.t.localizations("unban.cmd.options.user_id.description"),
        required=True,
    )
    @discord.option(
        "reason", str,
        description=v.t.msg(None, "unban.cmd.options.reason.description"),
        name_localizations=v.t.localizations("unban.cmd.options.reason.name"),
        description_localizations=v.t.localizations("unban.cmd.options.reason.description"),
        required=False,
    )
    async def unban(self, ctx: discord.ApplicationContext, user_id: str, reason: str = None):
        try:
            parsed_user_id = int(user_id.strip())
        except (TypeError, ValueError):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "unban.invalid_id_title"),
                    description=v.t.msg(ctx.guild, "unban.invalid_id_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        banned_user = None

        try:
            async for entry in ctx.guild.bans(limit=None):
                if entry.user.id == parsed_user_id:
                    banned_user = entry.user
                    break
        except discord.Forbidden:
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "unban.cannot_check_title"),
                    description=v.t.msg(ctx.guild, "unban.cannot_check_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if banned_user is None:
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "unban.not_found_title"),
                    description=v.t.msg(ctx.guild, "unban.not_found_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        reason = reason or v.t.msg(ctx.guild, "mod.helpers.unspecified_reason")

        if v.PY_ENV == "production":
            await ctx.guild.unban(
                banned_user,
                reason=f"{ctx.author}: {reason}",
            )

        embed = discord.Embed(
            description=v.t.msg(ctx.guild, "mod.helpers.reason_line", reason=reason),
            color=v.style(ctx.guild),
        )
        embed.set_author(icon_url=banned_user.display_avatar.url, name=v.t.msg(ctx.guild, "unban.success_author", user=banned_user))
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=banned_user.display_avatar.url, name=v.t.msg(ctx.guild, "unban.log_title", user=banned_user))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=f"{banned_user}", inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=reason, inline=False)
        await audit_log(ctx, "ModerationUnban", logs)

    @unban.error
    async def unban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "unban.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot unban members",
                description="The unban command failed because BobCat is missing the Ban Members permission.",
                fix=f"{v.docs}/moderation/unban",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "unban.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "unban.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/unban"),
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
    client.add_cog(Ban(client))
    client.add_cog(UnBan(client))