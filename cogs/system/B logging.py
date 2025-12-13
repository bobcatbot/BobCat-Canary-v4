import discord
from discord.ext import commands
from datetime import datetime as d
from modules import bot as v

LOGGING_KEY = 'moderation.logging'
LOGGING_EVENTS = 'moderation.logging.events'

class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    ### Member Events ### 
    @commands.Cog.listener()
    async def on_member_join(self, member):
        status = v.dashboard(member.guild.id, f"{LOGGING_EVENTS}.MemberJoin")
        log_channel = v.dashboard(member.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        channel = self.client.get_channel(int(log_channel))

        roles = [role.mention for role in member.roles]
        roles.sort()
        role = " ".join(roles)
        
        embed = discord.Embed(
            color=0xFFFFFF,
            timestamp=d.now(),
            title="Member Joined",
            description=f"{member.mention}\n**Roles:**\n{role}"
        )
        try:
            embed.set_author(icon_url=member.avatar.url, name=member)
        except AttributeError:
            embed.set_author(name=member)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            bans = await member.guild.bans(limit=None).flatten()
            if any(ban.user.id == member.id for ban in bans):
                return
        except discord.Forbidden:
            return
        
        status = v.dashboard(member.guild.id, f"{LOGGING_EVENTS}.MemberLeave")
        log_channel = v.dashboard(member.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        channel = self.client.get_channel(int(log_channel))
        
        roles = [role.mention for role in member.roles]
        roles.sort()
        role = " ".join(roles)
        
        embed = discord.Embed(
            color=0xFFFFFF,
            timestamp=d.now(),
            title="Member Left",
            description=f"{member.mention}\n**Roles:**\n{role}"
        )
        try:
            embed.set_author(icon_url=member.avatar.url, name=member)
        except AttributeError:
            embed.set_author(name=member)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        status = v.dashboard(after.guild.id, f"{LOGGING_EVENTS}.MemberUpdate")
        log_channel = v.dashboard(after.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        channel = self.client.get_channel(int(log_channel))

        if before == after:
            return
        
        if before.display_name != after.display_name:
            embed = discord.Embed(
                color=0xfee75c,
                timestamp=d.now(),
                title="Nickname change",
                description=f"**Before:** {before.display_name}\n**After:** {after.display_name}"
            )
            try:
                embed.set_author(icon_url=after.avatar.url, name=after)
            except AttributeError:
                embed.set_author(name=after)
            embed.set_footer(text=f"User ID: {after.id}")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, member):
        status = v.dashboard(guild.id, f"{LOGGING_EVENTS}.MemberBan")
        log_channel = v.dashboard(guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        channel = self.client.get_channel(int(log_channel))

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Member banned",
            description=f"{member.mention}"
        )
        try:
            embed.set_author(icon_url=member.avatar.url, name=member)
        except AttributeError:
            embed.set_author(name=member.author)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_member_unban(self, guild, member):
        status = v.dashboard(guild.id, f"{LOGGING_EVENTS}.MemberUnban")
        log_channel = v.dashboard(guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        channel = self.client.get_channel(int(log_channel))
        
        embed = discord.Embed(
            color=0xFFFFFF,
            timestamp=d.now(),
            title="Member unbaned",
            description=f"{member.mention}"
        )
        try:
            embed.set_author(icon_url=member.avatar.url, name=member)
        except AttributeError:
            embed.set_author(name=member)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)
    
    ### Message Events ###
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild is None: # if this message deleted in dms
            return
        
        status = v.dashboard(message.guild.id, f"{LOGGING_EVENTS}.MessageDelete")
        log_channel = v.dashboard(message.guild.id, f"{LOGGING_KEY}.channel")
        bots = v.dashboard(message.guild.id, f"{LOGGING_KEY}.bots")
        if not status:
            return
        if not log_channel:
            return
        if bots and message.author.bot == True:
            return
        channel = self.client.get_channel(int(log_channel))

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Message Deleted",
            description=(
                f"**Channel:** {message.channel.mention} `{message.channel.id}`"
                f"\n**Author:** {message.author.mention} `{message.author.id}`"
                f"\n**Message:** ```\n- {message.content}\n```"
            )
        )
        try:
            embed.set_author(icon_url=message.author.avatar.url, name=message.author)
        except AttributeError:
            embed.set_author(name=message.author)
        embed.set_footer(text=f"ID: {message.author.id}")
        
        embeds = [embed]
        if message.embeds:
            for em in message.embeds:
                embeds.append(em)
        
        await channel.send(embeds=embeds)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot:
            return
        if before.content == after.content:
            return
        
        status = v.dashboard(after.guild.id, f"{LOGGING_EVENTS}.MessageEdit")
        log_channel = v.dashboard(after.guild.id, f"{LOGGING_KEY}.channel")
        bots = v.dashboard(after.guild.id, f"{LOGGING_KEY}.bots")
        if not status:
            return
        if not log_channel:
            return
        if bots and after.author.bot == True:
            return
        
        embed = discord.Embed(
            color=0xfaa71f,
            timestamp=d.now(),
            title="Message edited", 
            description=(
                f"**Author:** {after.author.mention} `{after.author.id}`"
                f"\n**Channel:** {after.channel.mention} `{after.channel.id}`"
                f"\n**Message:** {after.jump_url} `{after.id}`"
                f"\n\n**Content:** \n```\n- {before.content}\n``` ```\n+ {after.content}\n```"
            )
        )
        try:
            embed.set_author(icon_url=before.author.avatar.url, name=before.author)
        except AttributeError:
            embed.set_author(icon_url=before.author.default_avatar, name=before.author)
        embed.set_footer(text=f"ID: {before.author.id}")

        channel = self.client.get_channel(int(log_channel))
        await channel.send(embed=embed)

    ### Guild Events ###
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        status = v.dashboard(after.id, f"{LOGGING_EVENTS}.ServerUpdate")
        log_channel = v.dashboard(after.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        if before == after:
            return
        
        embed = discord.Embed(title="Server updated", color=0xfee75c)

        data = {}
        data[f"{after.id}"] = {}
        data[f"{after.id}"]["before"] = []
        data[f"{after.id}"]["after"] = []

        if before.icon != after.icon:
            embed.add_field(name="New Icon", value="** **")
            embed.set_image(url=after.icon.url)
        
        if before.name != after.name:
            data[f"{after.id}"]["before"].append(f"**Name:** {before.name}")
            data[f"{after.id}"]["after"].append(f"**Name:** {after.name}")
        
        if before.afk_channel != after.afk_channel:
            def formatAfkChannel(channel):
                return 'No inactive Channel' if channel.afk_channel == None else channel.afk_channel

            data[f"{after.id}"]["before"].append(f"**AFK Channel:** {formatAfkChannel(before)}")
            data[f"{after.id}"]["after"].append(f"**AFK Channel:** {formatAfkChannel(after)}")
        
        if before.afk_timeout != after.afk_timeout:
            def formatTime(x):
                return "minute" if x.afk_timeout == 60 else "minutes"
            
            data[f"{after.id}"]["before"].append(f"**AFK Timeout:** {(int(before.afk_timeout) / 60):.0f} {formatTime(before)}")
            data[f"{after.id}"]["after"].append(f"**AFK Timeout:**  {(int(after.afk_timeout) / 60):.0f} {formatTime(after)}")
        
        if before.verification_level != after.verification_level:
            data[f"{after.id}"]["before"].append(f"**Verification Level:** { str(before.verification_level).title() }")
            data[f"{after.id}"]["after"].append(f"**Verification Level:** { str(after.verification_level).title }")
        
        before_values = "\n".join([item for item in data[f"{after.id}"]["before"]])
        after_values = "\n".join([item for item in data[f"{after.id}"]["after"]])
        
        embed.add_field(name="Before", value=f"{ before_values }", inline=True)
        embed.add_field(name="After", value=f"{ after_values }", inline=True)            
        embed.set_footer(text=f"Channel ID: {after.id}")
        
        channel = self.client.get_channel(int(log_channel))
        await channel.send(embed=embed)
        del data[f"{after.id}"]
    
    ### Invite Events ###
    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        status = v.dashboard(invite.guild.id, f"{LOGGING_EVENTS}.ServerInviteCreate")
        log_channel = v.dashboard(invite.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        date = invite.expires_at
        expires_at = "Never" if invite.expires_at == None else date.strftime("%f")
        max_uses = "No limit" if invite.max_uses == 0 else f"{invite.max_uses} uses"

        embed = discord.Embed(
            color=0xfee75c,
            timestamp=d.now(),
            title="Invite Created"
        )
        embed.add_field(name="Invite Code", value=f"[{invite.code}]({invite.url})", inline=False)
        embed.add_field(name="Uses", value=f"{max_uses}", inline=False)
        embed.add_field(name="Expires", value=f"<t:{expires_at}:F>", inline=False)
        embed.add_field(name="Inviter", value=f"{invite.inviter.mention}", inline=False)
        embed.add_field(name="Channel", value=f"{invite.channel.mention}", inline=False)

        channel = self.client.get_channel(int(log_channel))
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        status = v.dashboard(invite.guild.id, f"{LOGGING_EVENTS}.ServerInviteDelete")
        log_channel = v.dashboard(invite.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        if invite.inviter == None:
            return
        
        date = invite.expires_at
        expires_at = "Never" if invite.expires_at == None else date.strftime("%f")
        max_uses = "No limit" if invite.max_uses == 0 else f"{invite.max_uses} uses"

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Invite Deleted"
        )
        embed.add_field(name="Invite Code", value=f"[{invite.code}]({invite.url})", inline=False)
        embed.add_field(name="Uses", value=f"{max_uses}", inline=False)
        embed.add_field(name="Expires", value=f"<t:{expires_at}:F>", inline=False)
        embed.add_field(name="Inviter", value=f"{invite.inviter.mention}", inline=False)
        embed.add_field(name="Channel", value=f"{invite.channel.mention}", inline=False)

        channel = self.client.get_channel(int(log_channel))
        await channel.send(embed=embed)
    
    ### Emoji Events ###
    #@commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        status = v.dashboard(guild.id, f"{LOGGING_KEY}.status")
        log_channel = v.dashboard(guild.id, f"{LOGGING_KEY}.channel")
        
        if status == "Enabled":
            embed = discord.Embed(
                color=0xEB459E,
                timestamp=d.now(),
                title="Emoji updated",
                description=f"**Before:** {before}\n**After:** {after}"
            )
            embed.set_footer(text=f"Emoji ID: {after.id}")
            channel = self.client.get_channel(int(log_channel))
            await channel.send(embed=embed)
    
    ### Channel Events ###
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        status = v.dashboard(channel.guild.id, f"{LOGGING_EVENTS}.ChannelCreate")
        log_channel = v.dashboard(channel.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        Channel = self.client.get_channel(int(log_channel))
        
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                color=0x57F287,
                timestamp=d.now(),
                title="Text channel created",
                description=f"**Name:** {channel.name}\n**Category:** {channel.category}"
            )
            embed.set_footer(text=f"Channel ID: {channel.id}")
            await Channel.send(embed=embed)
            return
        if isinstance(channel, discord.VoiceChannel):
            embed = discord.Embed(
                color=0x57F287,
                timestamp=d.now(),
                title="Voice channel created",
                description=f"**Name:** {channel.name}\n**Category:** {channel.category}"
            )
            embed.set_footer(text=f"Channel ID: {channel.id}")
            await Channel.send(embed=embed)
            return
        
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        status = v.dashboard(channel.guild.id, f"{LOGGING_EVENTS}.ChannelDelete")
        log_channel = v.dashboard(channel.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        Channel = self.client.get_channel(int(log_channel))
                
        if isinstance(channel, discord.TextChannel):
            embed = discord.Embed(
                color=0xED4245,
                timestamp=d.now(),
                title="Text channel deleted",
                description=f"**Name:** {channel.name}\n**Category:** {channel.category}"
            )
            embed.set_footer(text=f"Channel ID: {channel.id}")
            await Channel.send(embed=embed)
            return
        if isinstance(channel, discord.VoiceChannel):
            embed = discord.Embed(
                color=0xED4245,
                timestamp=d.now(),
                title="Voice channel deleted",
                description=f"**Name:** {channel.name}\n**Category:** {channel.category}"
            )
            embed.set_footer(text=f"Channel ID: {channel.id}")
            await Channel.send(embed=embed)
            return
        
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        status = v.dashboard(after.guild.id, f"{LOGGING_EVENTS}.ChannelUpdate")
        log_channel = v.dashboard(after.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
                
        channel = self.client.get_channel(int(log_channel))

        data = {}
        data[f"{after.guild.id}"] = {}
        data[f"{after.guild.id}"]["before"] = []
        data[f"{after.guild.id}"]["after"] = []

        if before.overwrites != after.overwrites:
            return

        if isinstance(after, discord.TextChannel):
            embed = discord.Embed(
                color=0xfee75c,
                timestamp=d.now(),
                title="Text channel updated",
            )

            if before.position != after.position:
                return
            if before.name != after.name:
                data[f"{after.guild.id}"]["before"].append(f"**Name:** {before.name}")
                data[f"{after.guild.id}"]["after"].append(f"**Name:** {after.name}")
            if before.topic != after.topic:
                data[f"{after.guild.id}"]["before"].append(f"**Topic:** {before.topic}")
                data[f"{after.guild.id}"]["after"].append(f"**Topic:** {after.topic}")
            if before.category != after.category:
                data[f"{after.guild.id}"]["before"].append(f"**Category:** {before.category}")
                data[f"{after.guild.id}"]["after"].append(f"**Category:** {after.category}")
            if before.slowmode_delay != after.slowmode_delay:
                data[f"{after.guild.id}"]["before"].append(f"**Slowmode:** {before.slowmode_delay} seconds")
                data[f"{after.guild.id}"]["after"].append(f"**Slowmode:** {after.slowmode_delay} seconds")
            
            before_values = "\n".join([item for item in data[f"{after.guild.id}"]["before"]])
            after_values = "\n".join([item for item in data[f"{after.guild.id}"]["after"]])
            
            embed.add_field(name="Before", value=f"{ before_values }", inline=True)
            embed.add_field(name="After", value=f"{ after_values }", inline=True)
            embed.set_footer(text=f"Channel ID: {after.id}")
            await channel.send(embed=embed)

            del data[f"{after.guild.id}"]
            return

        if isinstance(after, discord.VoiceChannel):
            embed = discord.Embed(
                color=0xfee75c,
                timestamp=d.now(),
                title="Voice channel updated",
            )
            
            if before.position != after.position:
                return
            if before.name != after.name:
                data[f"{after.guild.id}"]["before"].append(f"**Name:** {before.name}")
                data[f"{after.guild.id}"]["after"].append(f"**Name:** {after.name}")
            if before.bitrate != after.bitrate:
                data[f"{after.guild.id}"]["before"].append(f"**Bitrate:** {(before.bitrate / 1000):.0f}kbps")
                data[f"{after.guild.id}"]["after"].append(f"**Bitrate:** {(after.bitrate / 1000):.0f}kbps")
            if before.user_limit != after.user_limit:
                data[f"{after.guild.id}"]["before"].append(f"**User limit:** {before.user_limit} user")
                data[f"{after.guild.id}"]["after"].append(f"**User Limit:** {after.user_limit} user")
            if before.category != after.category:
                data[f"{after.guild.id}"]["before"].append(f"**Category:** {before.category}")
                data[f"{after.guild.id}"]["after"].append(f"**Category:** {after.category}")
            
            before_values = "\n".join([item for item in data[f"{after.guild.id}"]["before"]])
            after_values = "\n".join([item for item in data[f"{after.guild.id}"]["after"]])
            
            embed.add_field(name="Before", value=f"{ before_values }", inline=True)
            embed.add_field(name="After", value=f"{ after_values }", inline=True)
            embed.set_footer(text=f"Channel ID: {after.id}")
            await channel.send(embed=embed)
            return
        
    ### Role Events
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        status = v.dashboard(role.guild.id, f"{LOGGING_EVENTS}.RoleCreate")
        log_channel = v.dashboard(role.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        channel = self.client.get_channel(int(log_channel))

        embed = discord.Embed(
            color=0xFFFFFF,
            timestamp=d.now(),
            title="Role created",
            description=f"**Name:** {role.name}\n**Colour** {role.color}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}"
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        await channel.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        status = v.dashboard(role.guild.id, f"{LOGGING_EVENTS}.RoleDelete")
        log_channel = v.dashboard(role.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        channel = self.client.get_channel(int(log_channel))
        
        embed = discord.Embed(
            color=0x000000,
            timestamp=d.now(),
            title="Role deleted",
            description=f"**Name:** {role.name}\n**Colour** {role.color}\n**Mentionable:** {role.mentionable}\n**Displayed separately:** {role.hoist}"
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        await channel.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        status = v.dashboard(after.guild.id, f"{LOGGING_EVENTS}.RoleUpdate")
        log_channel = v.dashboard(after.guild.id, f"{LOGGING_KEY}.channel")
        if not status:
            return
        if not log_channel:
            return
        
        if before == after:
            return
                
        channel = self.client.get_channel(int(log_channel))
        
        embed = discord.Embed(
            color=0xfee75c,
            timestamp=d.now(),
            title=f'Role "{before.name}" updated',
        )

        data = {}
        data[f"{after.guild.id}"] = {}
        data[f"{after.guild.id}"]["before"] = []
        data[f"{after.guild.id}"]["after"] = []
        
        if before.position != after.position:
            return
        if before.name != after.name:
            data[f"{after.guild.id}"]["before"].append(f"**Name:** {before.name}")
            data[f"{after.guild.id}"]["after"].append(f"**Name:** {after.name}")
        if before.color != after.color:
            data[f"{after.guild.id}"]["before"].append(f"**Colour:** {before.color}")
            data[f"{after.guild.id}"]["after"].append(f"**Colour:** {after.color}")
        if before.hoist != after.hoist:
            data[f"{after.guild.id}"]["before"].append(f"**Separated:** {before.hoist}")
            data[f"{after.guild.id}"]["after"].append(f"**Separated:** {after.hoist}")
        if before.mentionable != after.mentionable:
            data[f"{after.guild.id}"]["before"].append(f"**Mentionable:** {before.mentionable}")
            data[f"{after.guild.id}"]["after"].append(f"**Mentionable:** {after.mentionable}")
                
        before_values = "\n".join([item for item in data[f"{after.guild.id}"]["before"]])
        after_values = "\n".join([item for item in data[f"{after.guild.id}"]["after"]])
        
        embed.add_field(name="Before", value=f"{ before_values }", inline=True)
        embed.add_field(name="After", value=f"{ after_values }", inline=True)
        embed.set_footer(text=f"Role ID: {after.id}")
        await channel.send(embed=embed)
    
def setup(client):
    client.add_cog(events(client))