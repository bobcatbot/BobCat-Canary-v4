import json
import discord
from discord.ext import commands
from datetime import datetime
from modules import bot as v
from ._utils.audit_log import audit_log

def get_member_warnings(self, guild: discord.Guild, member: discord.Member) -> list[dict]:
    data = v.db.get_server_config(guild)
    warnings = data['moderation']['warnings'].get(f'{member.id}')
    
    if warnings is None:
        return None
    return warnings

def add_member_warnings(self, guild: discord.Guild, member: discord.Member, reason: str) -> bool:
    warnings = self.get_member_warnings(guild=guild, member=member)
    
    if warnings is None:
        v.db.update_server_config(guild, key=f"moderation.warnings.{member.id}", value=[])
    
    warnings.append({"id": len(warnings) + 1, "reason": reason, "time": datetime.now()})
    v.db.update_server_config(guild, key=f"moderation.warnings.{member.id}", value=warnings)
    return True

def delete_member_warnings(self, guild: discord.Guild, member: discord.Member, case: int=None, warns: list=None) -> bool:
    warnings = self.get_member_warnings(guild=guild, member=member)
    
    if warnings is None:
        return None
    
    if case is not None:
        for idx, warn in enumerate(warnings, 1):
            if int(warn['id']) == int(case):
                warnings.pop(warnings.index(warn))
                v.db.update_server_config(guild, key=f"moderation.warnings.{member.id}", value=warnings)
                return warn
        return False
    
    if warns is not None:
        v.db.update_server_config(guild, key=f"moderation.warnings.{member.id}", value=[])
        return True
#

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
        if member == ctx.guild.owner:
            embed = discord.Embed(title="❌ You can't warn the owner of this server", color=v.error)
            return await ctx.send(embed=embed)        
        if member == ctx.user:
            embed = discord.Embed(title="❌ You can't warn yourself", color=v.error)
            return await ctx.send(embed=embed)
        
        reason = "Unspecified" if not reason else reason
        
        add_member_warnings(guild=ctx.guild, member=member, reason=reason)

        embed = discord.Embed(description=f"**Reason:** {reason}", color=v.style(ctx.guild.id))
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been warned")
        except AttributeError:
            embed.set_author(icon_url=member.default_avatar, name=f"{member} has been warned")
        await ctx.respond(embed=embed)
        
        member_em = discord.Embed(title=f"You have been warned", color=v.style(ctx.guild.id))
        moddm = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["warn"]["dm"]
        if not 'none' in moddm:
            if "server" in moddm:
                member_em.add_field(name="Server", value=f"{ctx.guild.name}", inline=True)
            if "action" in moddm:
                member_em.add_field(name="Action", value="Warn", inline=True)
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
            logs.set_author(icon_url=member.avatar.url, name=f"[WARN] {member}")
        except AttributeError:
            logs.set_author(icon_url=member.default_avatar, name=f"[WARN] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"{reason}")
        await audit_log(self.client, ctx, 'ModerationWarn', logs)
    
    @warn.error
    async def warn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title=f"❌ Missing `Moderate Members` permission"
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to warn members", description='Please give BobCat the "Time out Members" permission')
            embed = discord.Embed(description=f"❌ I can't do that because I'm missing the `Time out Members` permission.  \n\nNeed help?\n{v.docs}/moderation/warn", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/warn",
                description="/warn [Member] {reason} \n- Member: Mention | ID | Username | Username#tag \n- reason: reason for the warn"
            )
            return await ctx.send(embed=embed)

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
        if member == ctx.guild.owner:
            embed = discord.Embed(title=f"❌ You can't unwarn the owner of this server", color=v.error)
            return await ctx.respond(embed=embed)
        if member == ctx.author:
            embed = discord.Embed(title="❌ You can't unwarn yourself", color=v.error)
            return await ctx.respond(embed=embed)
        
        warnings = self.get_member_warnings(guild=ctx.guild, member=member)
        
        if not warnings or warnings is None:
            embed = discord.Embed(title="❌ This user has no warnings", color=v.error)
            return await ctx.respond(embed=embed)
        
        warn = delete_member_warnings(guild=ctx.guild, member=member, case=case)
        # if warn is None:
        #     embed = discord.Embed(title="❌ Failed to get user warnings", color=v.error)
        #     return await ctx.respond(embed=embed)
        if not warn:
            embed = discord.Embed(title="❌ Invalid warn ID", color=v.error)
            return await ctx.respond(embed=embed)
        
        embed = discord.Embed(color=v.style(ctx.guild.id))
        try:
            embed.set_author(icon_url=member.avatar.url, name=f"{member} has been unwarned")
        except AttributeError:
            embed.set_author(icon_url=member.default_avatar, name=f"{member} has been unwarned")
        embed.add_field(name="Infraction", value=f"{warn['reason']} • #{warn['id']}", inline=False)
        await ctx.respond(embed=embed)

        member_em = discord.Embed(title=f"You have been unwarned", color=v.style(ctx.guild.id))
        moddm = v.db.get_dash(ctx.guild.id)["moderation"]["settings"]["warn"]["dm"]
        if moddm:
            if "server" in moddm:
                member_em.add_field(name="Server", value=f"{ctx.guild.name}", inline=True)
            if "action" in moddm:
                member_em.add_field(name="Action", value="Unwarn", inline=True)
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
            logs.set_author(icon_url=member.avatar.url, name=f"[UNWARN] {member}")
        except AttributeError:
            logs.set_author(name=f"[UNWARN] {member}")
        logs.add_field(name="User", value=f"{member.mention}", inline=True)
        logs.add_field(name="Moderator", value=f"{ctx.author.mention}")
        logs.add_field(name="Reason", value=f"Case {case} removed")
        await audit_log(self.client, ctx, 'ModerationUnwarn', logs)
    
    @unwarn.error
    async def unwarn_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                color=v.error,
                title="❌ Missing `Time out Members` permission"
            )
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to unwarn members", description='Please give BobCat the "Time out Members" permission')
            embed = discord.Embed(description=f"❌ I can't do that because I'm missing the `Time out Members` permission.  \n\nNeed help?\n{v.docs}/moderation/unwarn", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/unwarn",
                description="/unwarn [Member] {reason} \n- Member: Mention | ID | Username | Username#tag \n- case_number: The warn you want to remove"
            )
            return await ctx.send(embed=embed)

class Warnings(commands.Cog):
    def __init__(self, client):
        self.client = client
# Warnings
    @commands.slash_command(name="warnings", description="Shows the warnings of a member")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_guild_permissions(moderate_members=True)
    @discord.option("member", discord.Member, description="The member you want to see the warnings of", required=False)
    async def warnings(self, ctx, member: discord.Member = None):
        member = ctx.author if not member else member

        warns = get_member_warnings(guild=ctx.guild, member=member)
        if warns is None:
            return await ctx.respond("Failed to get warnings data.")
        
        if not warns or len(warns) == 0:
            embed = discord.Embed(color=v.style(ctx.guild.id))
            try:
                embed.set_author(icon_url=member.avatar.url, name=f"{member} has no warnings")
            except AttributeError:
                embed.set_author(name=f"{member} has no warnings")
            return await ctx.respond(embed=embed)
        
        embed = discord.Embed(color=v.style(ctx.guild.id))
        try: embed.set_author(icon_url=member.avatar.url, name=f"{member}'s warnings")
        except AttributeError: embed.set_author(name=f"{member}'s warnings")
        
        embed.add_field(name="Total", value=f"{len(warns)} warnings", inline=True)
        embed.add_field(name="Last 10 warnings", value="", inline=False)

        for index, warn in enumerate(warns, 1):
            if index == 11:
                break
            
            time = discord.utils.format_dt(warn['time'], style="R")
                
            embed_dict = embed.to_dict()
            embed_dict["fields"][1]["value"] += f"#{warn['id']} • {time} • **{warn['reason']}**\n"
            embed = discord.Embed.from_dict(embed_dict)

        canInteract = True
        if ctx.author.guild_permissions.moderate_members:
            canInteract = False
        
        class Confirm(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
        
            @discord.ui.button(label="Yes", style=discord.ButtonStyle.blurple)
            async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return True
                for child in self.children:
                    child.disabled = True
                
                delete_member_warnings(guild=ctx.guild, member=member, warns=[])
                
                embed = discord.Embed(color=v.style(ctx.guild.id))
                try:
                    embed.set_author(icon_url=member.avatar.url, name=f"{member} has no warnings")
                except AttributeError:
                    embed.set_author(icon_url=member.default_avatar, name=f"{member} has no warnings")
                await interaction.edit_original_response(embed=embed, view=None)
            
            @discord.ui.button(label="No", style=discord.ButtonStyle.gray)
            async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return True
                for child in self.children:
                    child.disabled=True
                em = discord.Embed(description="**Canceled**", color=v.error)
                await interaction.response.edit_message(embed=em, view=self)
        
        class Infractions(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            
            @discord.ui.button(label="Remove all warnings", style=discord.ButtonStyle.red, disabled=canInteract)
            async def infractions(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not interaction.user.guild_permissions.moderate_members:
                    return True
                em = discord.Embed(description=f"Are you sure you want to remove all of **{member}'s** warnings \n**This action is irreversible**", color=v.error)
                await interaction.response.send_message(embed=em, view=Confirm(), ephemeral=True)
        await ctx.respond(embed=embed, view=Infractions())
    
    @warnings.error
    async def warnings_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(title="❌ Missing `Moderate Members` permission", color=v.error)
            return await ctx.send(embed=embed)
        
        if isinstance(error, commands.BotMissingPermissions):
            v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to warn members", description='Please give BobCat the "Time out Members" permission')
            embed = discord.Embed(description=f"❌ I can't do that because I'm missing the `Time out Members` permission.\n\nNeed help?\n{v.docs}/moderation/warn", color=v.error)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                color=v.error,
                title="Invalid Usage", url=f"{v.docs}/moderation/warn",
                description="/warnings [Member] \n- Member: Mention | ID | Username | Username#tag"
            )
            return await ctx.send(embed=embed)
        
def setup(client):
    client.add_cog(Warn(client))
    client.add_cog(UnWarn(client))
    client.add_cog(Warnings(client))
    