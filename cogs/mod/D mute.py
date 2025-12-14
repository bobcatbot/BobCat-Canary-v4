import discord
import datetime
from modules import bot as v
from discord.ext import commands
from ._utils.audit_log import audit_log

class Mute(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client
# mute [member] {reason}
    @commands.slash_command(name="mute", description="Mutes a member in the server")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="The member you want to mute", required=True)
    @discord.option("reason", description="The reason for the mute", required=False)
    async def mute(self, ctx, member: discord.Member, *, reason=None):
        if member == ctx.guild.owner:
            error = discord.Embed(title="❌ You can't mute the owner of this server", color=v.error)
            return await ctx.respond(embed=error, ephemeral=True)
        
        if member == ctx.user:
            error = discord.Embed(title="❌ You can't mute yourself", color=v.error)
            return await ctx.repsond(embed=error, ephemeral=True)

        reason = "Unspecified" if not reason else reason

        muteType = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["mute"]["type"]
        if muteType == "role":
            mutedRole = discord.utils.get(ctx.guild.roles, name="Muted")
            
            if not mutedRole:
                await ctx.guild.create_role(name="Muted")
                mutedRole = discord.utils.get(ctx.guild.roles, name="Muted")
            
            if mutedRole in member.roles:
                embed = discord.Embed(
                    color=v.error,
                    title="❌ You cannot mute someone who is already muted."
                )
                return await ctx.send(embed=embed)

            for channel in ctx.guild.channels:
                await channel.set_permissions(mutedRole, speak=False, send_messages=False)
            await member.add_roles(mutedRole, reason=reason)
            message = ""
        
        if muteType == "timeout":
            muteTime = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["mute"]["duration"]
            if muteTime == "60-sec": time, duration = datetime.timedelta(seconds=60), "60 seconds"  # 60 SEC
            if muteTime == "5-min":  time, duration = datetime.timedelta(minutes=5), "5 minutes"  # 5 MIN
            if muteTime == "10-min": time, duration = datetime.timedelta(minutes=10), "10 minutes"  # 10 MIN
            if muteTime == "1-hour": time, duration = datetime.timedelta(hours=1), "1 hour"  # 1 HOUR
            if muteTime == "1-day":  time, duration = datetime.timedelta(days=1), "1 day"  # 1 DAY
            if muteTime == "1-week": time, duration = datetime.timedelta(weeks=1), "1 week"  # 1 WEEK
            
            try:
                await member.timeout_for(time, reason=reason)
            except discord.Forbidden:
                return await ctx.resond(f"failed to timeout {member.name}. \nTry and remove all roles from the user and try again later.")
            message = f"They have now been muted for {duration}."
        
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"**Reason:** {reason}"
        )
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been muted")
        except AttributeError:
            embed.set_author(icon_url=member.default_avatar, name=f"{member} has been muted")
        
        if message != "":
            embed.add_field(name="Note", value=message)
        else:
            pass
        await ctx.respond(embed=embed)
        
        member_em = discord.Embed(title=f"You have been muted", color=v.style(ctx.guild.id))
        moddm = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["mute"]["dm"]
        if moddm:
            if "server" in moddm:
                member_em.add_field(name="Server", value=f"{ctx.guild.name}", inline=True)
            if "action" in moddm:
                member_em.add_field(name="Action", value="Mute", inline=True)
            if "moderator" in moddm:
                member_em.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            if "reason" in moddm:
                member_em.add_field(name="Reason", value=f"{reason}", inline=False)
            
            try:
                await member.send(embed=member_em)
            except discord.Forbidden:
                pass
        
        # Audit log
        logs = discord.Embed(color=v.style(ctx.guild.id))
        try:
            logs.set_author(icon_url=member.avatar.url, name=f"[MUTE] {member}")
        except AttributeError:
            logs.set_author(icon_url=member.default_avatar, name=f"[MUTE] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"{reason}")
        await audit_log(self.client, ctx, 'ModerationMute', logs)
    
    @mute.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing `Moderate Members (timeout)` permission", color=v.error)
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to mute members", fix="https://docs.bobcatbot.xyz/commands/moderation/mute")
            embed = discord.Embed(description="❌ I can't do that because I'm missing the `Moderate Members (timeout)` permission.  \n\nNeed help?\nhttps://docs.bobcatbot.xyz/commands/moderation/mute", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/mute",
                description="b!mute [member] {reason} \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n `reason`: reason for the mute"
            )
            return await ctx.send(embed=embed)

class UnMute(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client
    # Unmute [member]
    @commands.slash_command(name="unmute", description="Unmute a member")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="Member to unmute", required=True)
    async def unmute(self, ctx, member: discord.Member):
        
        muteType = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["mute"]["type"]
        if muteType == "role":
            mutedRole = discord.utils.get(ctx.guild.roles, name="Muted")
            if not mutedRole in member.roles:
                embed = discord.Embed(
                    color=v.error,
                    title="❌ You cannot unmute someone who is not muted."
                )
                return await ctx.msg.edit(embed=embed, view=None)
            
            mutedRole = discord.utils.get(ctx.guild.roles, name="Muted")
            await member.remove_roles(mutedRole)
        
        if muteType == "timeout":
            await member.remove_timeout()
        
        embed = discord.Embed(color=v.style(ctx.guild.id))
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been unmuted")
        except AttributeError:
            embed.set_author(icon_url=member.default_avatar, name=f"{member} has been unmuted")
        await ctx.respond(embed=embed)

        member_em = discord.Embed(title=f"You have been unmuted", color=v.style(ctx.guild.id))
        moddm = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["mute"]["dm"]
        if 'none' not in moddm:
            if "server" in moddm:
                member_em.add_field(name="Server", value=f"{ctx.guild.name}", inline=True)
            if "action" in moddm:
                member_em.add_field(name="Action", value="Unmute", inline=True)
            if "moderator" in moddm:
                member_em.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            if "reason" in moddm:
                member_em.add_field(name="Reason", value=f"Unspecified", inline=False)
            
            try:
                await member.send(embed=member_em)
            except discord.Forbidden:
                pass

        # Audit log
        logs = discord.Embed(color=v.style(ctx.guild.id))
        try:
            logs.set_author(icon_url=member.avatar.url, name=f"[UNMUTE] {member}")
        except AttributeError:
            logs.set_author(icon_url=member.default_avatar, name=f"[UNMUTE] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        await audit_log(self.client, ctx, 'ModerationUnmute', logs)
    
    @unmute.error
    async def unmute_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing `Moderate Members (timeout)` permission", color=v.error)
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to unmute members", fix="https://docs.bobcatbot.xyz/commands/moderation/unmute")
            embed = discord.Embed(description="❌ I can't do that because I'm missing the `Moderate Members (timeout)` permission.  \n\nNeed help?\nhttps://docs.bobcatbot.xyz/commands/moderation/unmute", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/unmute",
                description="b!unmute [member] \n- member: Mention | ID | Username | Username#tag"
            )
            return await ctx.send(embed=embed)

class Timeout(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client
# Timeout
    @commands.slash_command(name="timeout", description="Temporarily mute a member")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="Member to mute", required=True)
    @discord.option("duration", str, description="Duration of the mute", required=True, choices=["60 SECS", "5 MINS", "10 MINS", "1 HOUR", "1 DAY", "1 WEEK"])
    @discord.option("reasons", str, description="Reason for the mute", required=False)
    async def timeout(self, ctx, member: discord.Member, duration, *, reasons=None):
        current_time = datetime.datetime.now()

        match duration:
            case "60 SECS":
                time_added = datetime.timedelta(seconds=60)
                timestr = "60 seconds"
            case "5 MINS":
                time_added = datetime.timedelta(minutes=5)
                timestr = "5 minutes"
            case "10 MINS":
                time_added = datetime.timedelta(minutes=10)
                timestr = "10 minutes"
            case "1 HOUR":
                time_added = datetime.timedelta(hours=1)
                timestr = "1 hour"
            case "1 DAY":
                time_added = datetime.timedelta(days=1)
                timestr = "1 day"
            case "1 WEEK":
                time_added = datetime.timedelta(weeks=1)
                timestr = "1 week"
            case _:
                pass

        reason = "Unspecified" if not reasons else reasons
        await member.timeout_for( time_added, reason=reason )
        
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f'**Reason:** {reason}',
            timestamp=current_time+time_added,
        )
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been timed out for {timestr}")
        except AttributeError:
            embed.set_author(name=f"{member} has been timed out {timestr}")
        embed.set_footer(text="Timed out until")
        ctx.msg = await ctx.respond(embed=embed)

        # Audit log
        logs = discord.Embed(color=v.style(ctx.guild.id))
        try:
            logs.set_author(icon_url=member.avatar.url, name=f"[TIMEOUT] {member}")
        except AttributeError:
            logs.set_author(name=f"[TIMEOUT] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"{reason}")
        logs.add_field(name="Duration", value=f"{timestr}")
        await audit_log(self.client, ctx, logs)
    
    @timeout.error
    async def timeout_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ You are missing `Moderate Members` permission", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to timeout members", fix="https://docs.bobcatbot.xyz/commands/moderation/timeout")
            embed = discord.Embed(description="❌ I can't do that because I'm missing the `Moderate Members (timeout)` permission.  \n\nNeed help?\nhttps://docs.bobcatbot.xyz/commands/moderation/timeout", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/timeout",
                description="b!timeout [member] [time] \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`time`: 60s, 300s, 1hr, 1d, 1w"
            )
            return await ctx.send(embed=embed)

def setup(client):
    client.add_cog(Mute(client))
    client.add_cog(UnMute(client))
    client.add_cog(Timeout(client))