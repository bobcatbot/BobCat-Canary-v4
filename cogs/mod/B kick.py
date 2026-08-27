import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild
from .mod_utils.utils import can_moderate, send_member_dm, audit_log

class ModKick(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(name="kick", description="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @discord.option("member", discord.Member, description="The member you want to kick", required=True)
    @discord.option("reason", str, description="The reason for the kick", required=False)
    async def kick(self, ctx: discord.ApplicationContext, member: discord.Member, reason: str = None):
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
        dm_fields = mod_data["settings"]["kick"]["dm"]

        await send_member_dm(
            member=member,
            guild=ctx.guild,
            moderator=ctx.author,
            action="Kicked",
            reason=reason,
            dm_fields=dm_fields,
        )

        if v.PY_ENV == "production":
            await member.kick(reason=f"Kicked by {ctx.author} | {reason}")

        embed = discord.Embed(description=f"**Reason:** {reason}", color=v.style(ctx.guild))
        embed.set_author(icon_url=member.display_avatar.url, name=f"{member} has been kicked")
        await ctx.respond(embed=embed)

        logs = discord.Embed(color=v.style(ctx.guild))
        logs.set_author(icon_url=member.display_avatar.url, name=f"[KICK] {member}")
        logs.add_field(name="User", value=member.mention, inline=True)
        logs.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        logs.add_field(name="Reason", value=reason, inline=False)
        await audit_log(ctx, "ModerationKick", logs)

    @kick.error
    async def kick_error(self, ctx, error):
        original = getattr(error, "original", error)

        if isinstance(original, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title="❌ Missing permission", 
                description="You need the `Kick Members` permission.",
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        if isinstance(original, commands.BotMissingPermissions):
            await v.push_notification(
                ctx.guild, 
                kind="error", 
                title="BobCat cannot kick members",
                description="The kick command failed because BobCat is missing the Kick Members permission.",
            )
            embed = discord.Embed(
                description=(
                    "❌ I am missing the `Kick Members` permission."
                    f"\nNeed help?\n{v.docs}/moderation/kick"
                ),
                color=v.error,
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        embed = discord.Embed(title="❌ Kick command failed", description="An unexpected error occurred.", color=v.error)
        await ctx.respond(embed=embed, ephemeral=True)
        raise original

def setup(client):
    client.add_cog(ModKick(client))