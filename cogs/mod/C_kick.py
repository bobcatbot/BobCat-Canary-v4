import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild
from ._helpers import can_moderate, send_member_dm, audit_log

class ModKick(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="kick",
        description=v.t.msg(None, "kick.cmd.description"),
        name_localizations=v.t.localizations("kick.cmd.name"),
        description_localizations=v.t.localizations("kick.cmd.description"),
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @discord.option(
        "member", discord.Member,
        description=v.t.msg(None, "kick.cmd.options.member.description"),
        name_localizations=v.t.localizations("kick.cmd.options.member.name"),
        description_localizations=v.t.localizations("kick.cmd.options.member.description"),
        required=True,
    )
    @discord.option(
        "reason", str,
        description=v.t.msg(None, "kick.cmd.options.reason.description"),
        name_localizations=v.t.localizations("kick.cmd.options.reason.name"),
        description_localizations=v.t.localizations("kick.cmd.options.reason.description"),
        required=False,
    )
    async def kick(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "kick.failed_title"),
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        reason = reason or v.t.msg(ctx.guild, "mod.helpers.unspecified_reason")

        mod_data = (await Guild.get(str(ctx.guild.id))).dashboard.moderation
        dm_fields = mod_data.settings.kick.dm

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action=v.t.msg(ctx.guild, "mod.actions.kicked"),
            reason=reason,
            dm_fields=dm_fields,
        )

        if v.PY_ENV == "production":
            await member.kick(reason=f"Kicked by {ctx.author} | {reason}")

        embed = discord.Embed(description=v.t.msg(ctx.guild, "mod.helpers.reason_line", reason=reason), color=v.style(ctx.guild))
        embed.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "kick.success_author", member=member))
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=v.t.msg(ctx.guild, "kick.log_title", member=member))
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.user"), value=member.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.moderator"), value=ctx.author.mention, inline=True)
        logs.add_field(name=v.t.msg(ctx.guild, "mod.helpers.log_fields.reason"), value=reason, inline=False)
        await audit_log(ctx, "ModerationKick", logs)

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "mod.common_errors.missing_perms_title"),
                    description=v.t.msg(ctx.guild, "kick.errors.missing_perms_description"),
                    color=v.error,
                ),
                ephemeral=True
            )

        if isinstance(error, commands.BotMissingPermissions):
            # push_notification/docs link are dashboard-side, not player-facing chat -
            # left as-is, same as the original (untranslated, admin-facing tooling).
            await v.push_notification(
                ctx.guild, kind="error",
                title="BobCat cannot kick members",
                description="The kick command failed because BobCat is missing the Kick Members permission.",
                fix=f"{v.docs}/moderation/kick",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    title=v.t.msg(ctx.guild, "kick.errors.bot_missing_response_title"),
                    description=v.t.msg(ctx.guild, "kick.errors.bot_missing_response_description", docs=f"{v.docs}/moderation/kick"),
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
    client.add_cog(ModKick(client))