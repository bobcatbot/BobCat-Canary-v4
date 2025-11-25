import discord
from discord.ext import commands
from ._utils.audit_log import audit_log
from modules import bot as v

class Ban(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

    @commands.slash_command(name="ban", description="Bans a member from the server", guild_ids=v.guild_ids)
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @discord.option("member", discord.Member, description="The member you want to ban", required=True)
    @discord.option("reason", description="The reason for the ban", required=False)
    @discord.option("delete_messages", int, description="The amount of days of messages to delete", required=False)
    async def ban(self, ctx, member: discord.Member, *, reason=None, delete_messages=None):
        if member == ctx.guild.owner:
            error = discord.Embed(title="❌ You can't ban the owner of this server", color=v.error)
            return await ctx.respond(embed=error, ephemeral=True)
        
        if member == ctx.user:
            error = discord.Embed(title="❌ You can't ban yourself", color=v.error)
            return await ctx.respond(embed=error, ephemeral=True)
        
        reason = "Unspecified" if not reason else reason

        if v.PY_ENV == "production":
            deleteMessages = v.dashboard(ctx.guild.id, "moderation.settings.ban.deleteMessageDays") if not delete_messages else delete_messages
            await ctx.guild.ban(user=member, reason=reason, delete_message_days=int(deleteMessages))
        
        embed = discord.Embed(description=f"**Reason:** {reason}", color=v.style(ctx.guild.id))
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been banned")
        except AttributeError:
            embed.set_author(icon_url=member.default_avatar, name=f"{member} has been banned")
        await ctx.respond(embed=embed)

        member_em = discord.Embed(title=f"You have been banned", color=v.style(ctx.guild.id))
        moddm = v.dashboard(ctx.guild.id, "moderation.settings.ban.dm")
        if member.bot:
            return
        if 'none' not in moddm:
            if "server" in moddm:
                member_em.add_field(name="Server", value=f"{ctx.guild.name}", inline=True)
            if "action" in moddm:
                member_em.add_field(name="Action", value="Ban", inline=True)
            if "moderator" in moddm:
                member_em.add_field(name="Moderator", value=f"{ctx.author.mention}", inline=True)
            if "reason" in moddm:
                member_em.add_field(name="Reason", value=f"{reason}", inline=False)
            await member.send(embed=member_em)
        
        logs = discord.Embed(color=v.style(ctx.guild.id))
        try:
            logs.set_author(icon_url=member.avatar.url, name=f"[BAN] {member}")
        except AttributeError:
            logs.set_author(icon_url=member.default_avatar, name=f"[BAN] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"{reason}")
        await audit_log(self.client, ctx, 'ModerationBan', logs)
    
    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing `Ban Members` permission", color=v.error)
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to ban members", fix="https://docs.bobcatbot.xyz/commands/moderation/ban")
            embed = discord.Embed(description="❌ I can't do that because I'm missing the `Ban Members` permission.  \n\nNeed help?\nhttps://docs.bobcatbot.xyz/commands/moderation/ban")
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/ban",
                description="b!ban [member] {reason} \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`reason`: reason for the ban",
            )
            return await ctx.send(embed=embed)

class UnBan(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

    @commands.slash_command(name="unban", description="Unbans a member from the server")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @discord.option("member", discord.Member, description="The member you want to unban", required=True)
    async def unban(self, ctx, member: discord.Member):
        try:
            if v.PY_ENV == "production":
                await ctx.guild.unban(user=member)
            
            embed = discord.Embed(color=v.style(ctx.guild.id))
            try: 
                embed.set_author(icon_url=member.avatar.url, name=f"{member} has been unbanned")
            except AttributeError:
                embed.set_author(icon_url=member.default_avatar, name=f"{member} has been unbanned")
            await ctx.send(embed=embed)
            
            logs = discord.Embed(color=v.style(ctx.guild.id))
            try:
                logs.set_author(icon_url=member.avatar.url, name=f"[UNBAN] {member}")
            except AttributeError:
                logs.set_author(icon_url=member.default_avatar, name=f"[UNBAN] {member}")
            logs.add_field(name="User", value=f"{member.mention}", inline=True)
            logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
            await audit_log(self.client, ctx, 'ModerationUnban', logs)
        
        except discord.errors.NotFound:
            embed = discord.Embed(title="❌ User was not banned or does not exist!", color=v.style(ctx.guild.id))
            return await ctx.send(embed=embed, view=None)
    
    @unban.error
    async def unban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title="❌ Missing `Ban Members` permission"
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to unban members", fix="https://docs.bobcatbot.xyz/commands/moderation/unban")
            embed = discord.Embed(description="❌ I can't do that because I'm missing the `Ban Members` permission.  \n\nNeed help?\nhttps://docs.bobcatbot.xyz/commands/moderation/unban")
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/unban",
                description="b!unban [member] \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag",
            )
            return await ctx.send(embed=embed)

class MassBan(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

    # This is a normal command not a slash command
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def massban(self, ctx, members, *, reason=None):
        # if member == ctx.guild.owner:
        #     embed = discord.Embed(title="❌ You can't ban the owner of this server - Skipping", color=v.error)
        #     return await ctx.send(embed=embed)

        # if ctx.message.author in member:
        #     embed = discord.Embed(title="❌ You can't ban yourself - Skipping", color=v.error)
        #     #return await ctx.send(embed=embed)
        
        reason = "Unspecified" if not reason else reason

        member = members.split(",")
        usrs = ""
        for mem in member:
            user = ctx.guild.get_member(int(mem))
            usrs += str(user.mention) + "\n"
            
            await user.ban(reason=reason)
        
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"{len(member)} members banned"
        )
        embed.set_author(icon_url=self.client.user.avatar.url, name=f"[MASSBAN] {len(member)} members")
        await ctx.send(embed=embed)
        
        logs = discord.Embed(color=v.style(ctx.guild.id))
        try:
            logs.set_author(icon_url=member.avatar.url, name=f"[BAN] {member}")
        except AttributeError:
            logs.set_author(name=f"[MASSBAN] {len(member)}")
        logs.add_field(name="Users", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"{reason}")
        await audit_log(self.client, ctx, logs)
    
    @massban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing `Ban Members` permission", color=v.error)
            return await ctx.send(embed=embed)
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url="https://docs.bobcatbot.xyz/commands/moderation/ban",
                description="b!massban [member] {reason} \n\n**Arguments**\n`member`: User ID [How to use ids](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-)\n`reason`: reason for the mass ban",
            )
            return await ctx.send(embed=embed)

def setup(client):
    client.add_cog(Ban(client))
    client.add_cog(UnBan(client))
    client.add_cog(MassBan(client))