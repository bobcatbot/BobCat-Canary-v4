import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild
from .mod_utils.utils import can_moderate, send_member_dm, audit_log

class Ban(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(name="ban", description="Bans a member from the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @discord.option("member", discord.Member, description="The member you want to ban", required=True)
    @discord.option("reason", str, description="The reason for the ban", required=False)
    @discord.option("delete_messages", int, description="The number of previous message days to delete", required=False, min_value=0, max_value=7)
    async def ban(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None, delete_messages: int = None):
        allowed, error_message = await can_moderate(ctx.guild, ctx.author, member)
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

        mod_data = (await Guild.get(str(ctx.guild.id))).dashboard.moderation
        dm_fields = mod_data["settings"]["ban"]["dm"]
        default_delete_days = mod_data["settings"]["ban"]["deleteMessageDays"]

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
            action="Banned",
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
            description=(
                f"**Reason:** {reason}\n"
                f"**Deleted message history:** {delete_days} day(s)"
            ),
            color=v.style(ctx.guild),
        )
        embed.set_author(icon_url=member.display_avatar.url, name=f"{member} has been banned")
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=f"[BAN] {member}")
        logs.add_field(name="User", value=member.mention, inline=True)
        logs.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        logs.add_field(name="Reason", value=reason, inline=False)
        logs.add_field(name="Deleted messages", value=f"{delete_days} day(s)", inline=False)
        await audit_log(ctx, "ModerationBan", logs)

    @ban.error
    async def ban_error(self, ctx, error):
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Missing permission",
                    description=(
                        "You need the `Ban Members` permission."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, kind="error", title="BobCat cannot ban members",
                description="The ban command failed because BobCat is missing the Ban Members permission.",
            )
            return await ctx.respond(
                embed=discord.Embed(
                    description=(
                        "❌ I am missing the `Ban Members` permission."
                        f"\n\nNeed help?\n{v.docs}/moderation/ban"
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, discord.Forbidden):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Ban failed",
                    description=(
                        "I could not ban that user. Check my role "
                        "position and permissions."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        raise original

class UnBan(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="unban",
        description="Unbans a user from the server",
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @discord.option(
        "user_id",
        str,
        description="The ID of the user you want to unban",
        required=True,
    )
    @discord.option(
        "reason",
        str,
        description="The reason for the unban",
        required=False,
    )
    async def unban(
        self,
        ctx: discord.ApplicationContext,
        user_id: str,
        reason: str = None,
    ):
        try:
            parsed_user_id = int(user_id.strip())
        except (TypeError, ValueError):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Invalid user ID",
                    description="Please provide a valid Discord user ID.",
                    color=v.error,
                ),
                ephemeral=True,
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
                    title="❌ Unable to check bans",
                    description=(
                        "I do not have permission to view the ban list."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if banned_user is None:
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ User not found",
                    description="That user is not currently banned.",
                    color=v.error,
                ),
                ephemeral=True,
            )

        reason = reason or "Unspecified"

        if v.PY_ENV == "production":
            await ctx.guild.unban(
                banned_user,
                reason=f"{ctx.author}: {reason}",
            )

        embed = discord.Embed(
            description=f"**Reason:** {reason}",
            color=v.style(ctx.guild),
        )
        embed.set_author(
            icon_url=banned_user.display_avatar.url,
            name=f"{banned_user} has been unbanned",
        )
        await ctx.respond(embed=embed)

        logs = discord.Embed(
            color=v.style(ctx.guild),
        )
        logs.set_author(
            icon_url=banned_user.display_avatar.url,
            name=f"[UNBAN] {banned_user}",
        )
        logs.add_field(
            name="User",
            value=f"{banned_user} (`{banned_user.id}`)",
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
        await audit_log(
            ctx,
            "ModerationUnban",
            logs,
        )

    @unban.error
    async def unban_error(self, ctx, error):
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            return await ctx.respond(
                embed=discord.Embed(
                    title="❌ Missing permission",
                    description=(
                        "You need the `Ban Members` permission."
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        if isinstance(original, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild,
                kind="error",
                title="BobCat cannot unban members",
                description=(
                    "The unban command failed because BobCat is "
                    "missing the Ban Members permission."
                ),
                fix=(
                    "Give BobCat the Ban Members permission."
                ),
            )

            return await ctx.respond(
                embed=discord.Embed(
                    description=(
                        "❌ I am missing the `Ban Members` "
                        "permission.\n\n"
                        f"Need help?\n{v.docs}/moderation/unban"
                    ),
                    color=v.error,
                ),
                ephemeral=True,
            )

        raise original

def setup(client):
    client.add_cog(Ban(client))
    client.add_cog(UnBan(client))