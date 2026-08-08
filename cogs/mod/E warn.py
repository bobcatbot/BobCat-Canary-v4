import discord
from datetime import datetime, timezone
from discord.ext import commands

from modules import bot as v
from modules.models import Guild, Warning
from .mod_utils.utils import can_moderate, send_member_dm, audit_log

def get_member_warnings(
    guild: discord.Guild,
    member: discord.Member,
) -> list[Warning]:
    return Warning.find(
        Warning.guild_id == str(guild.id),
        Warning.user_id == str(member.id),
    ).run()

def add_member_warning(
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

    warning.insert()
    return warning

def delete_member_warning(
    guild: discord.Guild,
    member: discord.Member,
    case: str,
) -> Warning | None:
    warning = Warning.find_one(
        Warning.guild_id == str(guild.id),
        Warning.user_id == str(member.id),
        Warning.case == case,
    ).run()

    if warning is None:
        return None

    warning.delete()
    return warning

def clear_member_warnings(
    guild: discord.Guild,
    member: discord.Member,
) -> bool:
    warnings = get_member_warnings(guild, member)

    if not warnings:
        return False

    for warning in warnings:
        warning.delete()

    return True

class Warn(commands.Cog):
    def __init__(self, client):
        self.client = client

# Warn [Member] {reason}
    @commands.slash_command(name="warn", description="Warns a member from the server")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="The member you want to warn", required=True)
    @discord.option("reason", description="The reason for the warn", required=False)
    async def warn(self, ctx, member: discord.Member, *, reason=None):
        allowed, error_message = can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )

        reason = reason or "Unspecified"

        warning = add_member_warning(
            guild=ctx.guild,
            member=member,
            moderator=ctx.author,
            reason=reason,
        )

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=(
                f"**Reason:** {reason}\n"
                f"**Case:** `{warning.case}`"
            ),
        )
        embed.set_author(icon_url=member.avatar.url, name=f"{member} has been warned")
        await ctx.respond(embed=embed)

        dm_fields = Guild.get(str(ctx.guild.id)).run().dashboard.moderation["settings"]["warn"]["dm"]

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action="Warned",
            reason=reason,
            dm_fields=dm_fields,
        )

        logs = discord.Embed(color=v.style(ctx.guild.id))
        logs.set_author(icon_url=member.display_avatar.url, name=f"[WARN] {member}")
        logs.add_field(name="User", value=member.mention, inline=True)
        logs.add_field(name="Moderator", value=ctx.author.mention)
        logs.add_field(name="Reason", value=reason)
        logs.add_field(name="Case", value=f"`{warning.case}`")
        await audit_log(ctx, "ModerationWarn", logs)

    @warn.error
    async def warn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title=f"❌ Missing `Moderate Members` permission"
            )
            return await ctx.respond(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, kind="error", title="BobCat is missing permission to warn members", description='Please give BobCat the "Time out Members" permission')
            embed = discord.Embed(description=f"❌ I can't do that because I'm missing the `Time out Members` permission.  \n\nNeed help?\n{v.docs}/moderation/warn", color=v.error)
            return await ctx.respond(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/warn",
                description="/warn [Member] {reason} \n- Member: Mention | ID | Username | Username#tag \n- reason: reason for the warn"
            )
            return await ctx.respond(embed=embed)

class UnWarn(commands.Cog):
    def __init__(self, client):
        self.client = client
    
# Unwarn
    @commands.slash_command(name="unwarn", description="Unwarns a member from the server")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="The member you want to unwarn", required=True)
    @discord.option("case", description="The warn you want to remove", required=True)
    async def unwarn(self, ctx, member: discord.Member, case):
        allowed, error_message = can_moderate(ctx.guild, ctx.author, member)
        if not allowed:
            return await ctx.respond(
                embed=discord.Embed(
                    description=error_message,
                    color=v.error,
                ),
                ephemeral=True,
            )
        
        warnings = get_member_warnings(guild=ctx.guild, member=member)
        
        if not warnings or warnings is None:
            embed = discord.Embed(title="❌ This user has no warnings", color=v.error)
            return await ctx.respond(embed=embed)
        
        warning = delete_member_warning(guild=ctx.guild, member=member, case=case)
        # if warn is None:
        #     embed = discord.Embed(title="❌ Failed to get user warnings", color=v.error)
        #     return await ctx.respond(embed=embed)
        if not warning:
            embed = discord.Embed(title="❌ Invalid warn ID", color=v.error)
            return await ctx.respond(embed=embed)
        
        embed = discord.Embed(color=v.style(ctx.guild.id))
        embed.set_author(icon_url=member.display_avatar.url, name=f"{member} has been unwarned")
        embed.add_field(name="Infraction", value=f"{warning.reason} • `{warning.case}`", inline=False)
        await ctx.respond(embed=embed)

        dm_fields = Guild.get(str(ctx.guild.id)).run().dashboard.moderation["settings"]["warn"]["dm"]

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action="Unwarned",
            reason=warning.reason,
            dm_fields=dm_fields,
        )

        logs = discord.Embed(color=v.style(ctx.guild.id))
        logs.set_author(icon_url=member.display_avatar.url, name=f"[UNWARN] {member}")
        logs.add_field(name="User", value=member.mention, inline=True)
        logs.add_field(name="Moderator", value=ctx.author.mention)
        logs.add_field(name="Reason", value=f"Case `{warning.case}` removed")
        await audit_log(ctx, "ModerationUnwarn", logs)

    @unwarn.error
    async def unwarn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing `Moderate Members` permission",
                color=v.error,
            )
            return await ctx.respond(embed=embed)

        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(
                ctx.guild,
                kind="error",
                title="BobCat is missing permission to unwarn members",
                description=(
                    'Please give BobCat the "Moderate Members" permission'
                ),
            )

            embed = discord.Embed(
                description=(
                    "❌ I can't do that because I'm missing the "
                    "`Moderate Members` permission.\n\n"
                    f"Need help?\n{v.docs}/moderation/unwarn"
                ),
                color=v.error,
            )
            return await ctx.respond(embed=embed)

class Warnings(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(name="warnings", description="Shows the warnings of a member")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member,description="The member you want to see the warnings of", required=False)
    async def warnings(self, ctx, member: discord.Member = None):
        member = member or ctx.author

        warnings = get_member_warnings(guild=ctx.guild, member=member)

        if not warnings:
            embed = discord.Embed(color=v.style(ctx.guild.id))
            embed.set_author(icon_url=member.display_avatar.url, name=f"{member} has no warnings")
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
                f"`{warning.case}` • {created_at} • **{warning.reason}**"
            )

        embed = discord.Embed(color=v.style(ctx.guild.id))
        embed.set_author(icon_url=member.display_avatar.url, name=f"{member}'s warnings")
        embed.add_field(name="Total", value=f"{len(warnings)} warnings", inline=True)
        embed.add_field(name="Last 10 warnings", value="\n".join(warning_lines), inline=False)

        canInteract = not ctx.author.guild_permissions.moderate_members
        class Confirm(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(label="Yes", style=discord.ButtonStyle.red)
            async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return
                for child in self.children:
                    child.disabled = True

                clear_member_warnings(guild=ctx.guild, member=member)

                cleared_embed = discord.Embed(color=v.style(ctx.guild.id))
                cleared_embed.set_author(icon_url=member.display_avatar.url, name=f"{member} has no warnings")
                await interaction.response.edit_message(embed=cleared_embed, view=None)

            @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
            async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return
                for child in self.children:
                    child.disabled = True
                cancelled_embed = discord.Embed(description="**Cancelled**", color=v.error)
                await interaction.response.edit_message(embed=cancelled_embed, view=self)

        class Infractions(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(label="Remove all warnings", style=discord.ButtonStyle.red, disabled=canInteract)
            async def infractions(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return

                confirmation_embed = discord.Embed(
                    description=(
                        f"Are you sure you want to remove all of **{member}'s** warnings?"
                        "\n**This action is irreversible.**"
                    ),
                    color=v.error,
                )
                await interaction.response.send_message(embed=confirmation_embed, view=Confirm(), ephemeral=True)

        await ctx.respond(embed=embed, view=Infractions())

    @warnings.error
    async def warnings_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing `Moderate Members` permission", color=v.error)
            return await ctx.respond(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, kind="error", title="BobCat is missing permission to warn members", description='Please give BobCat the "Time out Members" permission')
            embed = discord.Embed(description=f"❌ I can't do that because I'm missing the `Time out Members` permission.\n\nNeed help?\n{v.docs}/moderation/warn", color=v.error)
            return await ctx.respond(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/warn",
                description="/warnings [Member] \n- Member: Mention | ID | Username | Username#tag"
            )
            return await ctx.respond(embed=embed)
        
def setup(client):
    client.add_cog(Warn(client))
    client.add_cog(UnWarn(client))
    client.add_cog(Warnings(client))