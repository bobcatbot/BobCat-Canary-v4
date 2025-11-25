import discord
from ._utils.audit_log import audit_log
from modules import bot as v
from discord.ext import commands

class mod_kick(commands.Cog):
    def __init__(self, client):
        self.client = client
    
# kick [member] [reason]
    @commands.slash_command(name="kick", description="Kicks a member from the server")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @discord.option("member", discord.Member, description="The member you want to kick", required=True)
    @discord.option("reason", description="The reason for the kick", required=False)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        if member == ctx.guild.owner:
            error = discord.Embed(title="❌ You can't kick the owner of this server", color=v.error)
            return await ctx.respond(embed=error, ephemeral=True)
        
        if member == ctx.user:
           error = discord.Embed(title="❌ You can't kick yourself", color=v.error)
           return await ctx.respond(embed=error, ephemeral=True)
        
        reason = "Unspecified" if not reason else reason
        
        if v.PY_ENV == "production":
            await member.kick(reason=reason)
        
        embed = discord.Embed(description=f"**Reason:** {reason}", color=v.style(ctx.guild.id))
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been kicked")
        except AttributeError:
            embed.set_author(icon_url=member.default_avatar, name=f"{member} has been kicked")
        await ctx.respond(embed=embed)
        
        member_em = discord.Embed(title=f"You have been kicked", color=v.style(ctx.guild.id))
        moddm = v.dashboard(ctx.guild.id, "moderation.settings.kick.dm")
        if 'none' not in moddm:
            if "server" in moddm:
                member_em.add_field(name="Server", value=f"{ctx.guild.name}", inline=True)
            if "action" in moddm:
                member_em.add_field(name="Action", value="Kick", inline=True)
            if "moderator" in moddm:
                member_em.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            if "reason" in moddm:
                member_em.add_field(name="Reason", value=f"{reason}", inline=False)
            await member.send(embed=member_em)
        
        logs = discord.Embed(color=v.style(ctx.guild.id))
        try:
            logs.set_author(icon_url=member.avatar.url, name=f"[KICK] {member}")
        except AttributeError:
            logs.set_author(icon_url=member.default_avatar, name=f"[KICK] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"{reason}")
        await audit_log(self.client, ctx, 'ModerationKick', logs)

# Error checking
    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title="❌ Missing `Kick Members` permission"
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to kick members", fix="https://docs.bobcatbot.xyz/commands/moderation/kick")
            embed = discord.Embed(description="❌ I can't do that because I'm missing the `Kick Members` permission.  \n\nNeed help?\nhttps://docs.bobcatbot.xyz/commands/moderation/kick", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/kick",
                description="b!kick [member] {reason} \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`reason`: Reason for kick",
            )
            return await ctx.send(embed=embed)

def setup(client):
    client.add_cog(mod_kick(client))