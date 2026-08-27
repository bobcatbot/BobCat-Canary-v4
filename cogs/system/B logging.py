import discord
from discord.ext import commands
from datetime import datetime as d
from modules import bot as v
from modules.models import Guild

class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    # ── Helper ────────────────────────────────────────────────────────────────
    async def _get_logging(self, guild_id: int) -> dict:
        return (await Guild.get(str(guild_id))).dashboard.moderation["logging"]

    async def _get_log_channel(self, guild_id: int, event: str) -> discord.TextChannel | None:
        """Returns the log channel if the event is enabled, otherwise None."""
        logging = await self._get_logging(guild_id)

        if not logging["events"].get(event, False):
            return None

        log_channel = logging.get("channel")
        if not log_channel:
            return None

        return self.client.get_channel(int(log_channel))

    def _author(self, embed: discord.Embed, user: discord.User | discord.Member) -> discord.Embed:
        """Sets the embed author with avatar fallback."""
        avatar = user.avatar.url if user.avatar else user.default_avatar.url
        embed.set_author(icon_url=avatar, name=str(user))
        return embed

    # ── Member Events ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = await self._get_log_channel(member.guild.id, "MemberJoin")
        if not channel:
            return

        roles = " ".join(sorted(role.mention for role in member.roles if role.name != "@everyone"))

        embed = discord.Embed(
            color=0x57F287,
            timestamp=d.now(),
            title="Member Joined",
            description=f"{member.mention}\n**Roles:** {roles or 'None'}"
        )
        self._author(embed, member)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        # Skip if this was triggered by a ban (avoid double-logging)
        try:
            async for ban in member.guild.bans(limit=None):
                if ban.user.id == member.id:
                    return
        except (discord.Forbidden, discord.NotFound):
            return

        channel = await self._get_log_channel(member.guild.id, "MemberLeave")
        if not channel:
            return

        roles = " ".join(sorted(role.mention for role in member.roles if role.name != "@everyone"))

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Member Left",
            description=f"{member.mention}\n**Roles:** {roles or 'None'}"
        )
        self._author(embed, member)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        channel = await self._get_log_channel(after.guild.id, "MemberUpdate")
        if not channel:
            return

        # Nickname change
        if before.display_name != after.display_name:
            embed = discord.Embed(
                color=0xfee75c,
                timestamp=d.now(),
                title="Nickname Changed",
                description=f"**Before:** {before.display_name}\n**After:** {after.display_name}"
            )
            self._author(embed, after)
            embed.set_footer(text=f"User ID: {after.id}")
            await channel.send(embed=embed)

        # Role changes
        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]

        if added_roles or removed_roles:
            desc = ""
            if added_roles:
                desc += f"**Roles Added:** {' '.join(r.mention for r in added_roles)}\n"
            if removed_roles:
                desc += f"**Roles Removed:** {' '.join(r.mention for r in removed_roles)}"

            embed = discord.Embed(
                color=0xfee75c,
                timestamp=d.now(),
                title="Member Roles Updated",
                description=desc
            )
            self._author(embed, after)
            embed.set_footer(text=f"User ID: {after.id}")
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.User):
        channel = await self._get_log_channel(guild.id, "MemberBan")
        if not channel:
            return

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Member Banned",
            description=f"{member.mention}"
        )
        self._author(embed, member)  # fixed: was member.author
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.User):
        channel = await self._get_log_channel(guild.id, "MemberUnban")
        if not channel:
            return

        embed = discord.Embed(
            color=0x57F287,
            timestamp=d.now(),
            title="Member Unbanned",  # fixed: was "unbaned"
            description=f"{member.mention}"
        )
        self._author(embed, member)
        embed.set_footer(text=f"ID: {member.id}")
        await channel.send(embed=embed)

    # ── Message Events ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return

        channel = await self._get_log_channel(message.guild.id, "MessageDelete")
        if not channel:
            return

        # Skip bot messages if the setting says to
        if (await self._get_logging(message.guild.id)).get("bots", False) and message.author.bot:
            return

        content = message.content or "*[No text content]*"
        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Message Deleted",
            description=(
                f"**Channel:** {message.channel.mention} `{message.channel.id}`\n"
                f"**Author:** {message.author.mention} `{message.author.id}`\n"
                f"**Content:** ```{content[:1000]}```"
            )
        )
        self._author(embed, message.author)
        embed.set_footer(text=f"Message ID: {message.id}")

        # Add attachments if present
        if message.attachments:
            attachment_urls = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
            embed.add_field(
                name="📎 Attachments",
                value=attachment_urls[:1024],
                inline=False
            )
        
        # Also add image preview if it's an image
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image/'):
                embed.set_image(url=attachment.url)
                break

        embeds = [embed] + list(message.embeds)
        await channel.send(embeds=embeds[:10])  # Discord max is 10 embeds per message

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot:
            return
        if before.content == after.content:
            return
        if after.guild is None:
            return

        channel = await self._get_log_channel(after.guild.id, "MessageEdit")
        if not channel:
            return

        if (await self._get_logging(after.guild.id)).get("bots", False) and after.author.bot:
            return

        embed = discord.Embed(
            color=0xfaa71f,
            timestamp=d.now(),
            title="Message Edited",
            description=(
                f"**Author:** {after.author.mention} `{after.author.id}`\n"
                f"**Channel:** {after.channel.mention} `{after.channel.id}`\n"
                f"**Message:** {after.jump_url}\n\n"
                f"**Before:** ```{before.content[:500]}```\n"
                f"**After:** ```{after.content[:500]}```"
            )
        )
        self._author(embed, before.author)
        embed.set_footer(text=f"Message ID: {after.id}")

        await channel.send(embed=embed)

    # ── Guild Events ──────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        channel = await self._get_log_channel(after.id, "ServerUpdate")
        if not channel:
            return
        if before == after:
            return

        before_vals = []
        after_vals = []

        if before.name != after.name:
            before_vals.append(f"**Name:** {before.name}")
            after_vals.append(f"**Name:** {after.name}")
        if before.icon != after.icon:
            before_vals.append("**Icon:** *(changed)*")
            after_vals.append("**Icon:** *(see below)*")
        if before.afk_channel != after.afk_channel:
            before_vals.append(f"**AFK Channel:** {before.afk_channel or 'None'}")
            after_vals.append(f"**AFK Channel:** {after.afk_channel or 'None'}")
        if before.afk_timeout != after.afk_timeout:
            before_vals.append(f"**AFK Timeout:** {before.afk_timeout // 60}m")
            after_vals.append(f"**AFK Timeout:** {after.afk_timeout // 60}m")
        if before.verification_level != after.verification_level:
            before_vals.append(f"**Verification:** {str(before.verification_level).title()}")
            after_vals.append(f"**Verification:** {str(after.verification_level).title()}")

        if not before_vals:
            return  # Nothing worth logging changed

        embed = discord.Embed(color=0xfee75c, timestamp=d.now(), title="Server Updated")
        embed.add_field(name="Before", value="\n".join(before_vals) or "—", inline=True)
        embed.add_field(name="After", value="\n".join(after_vals) or "—", inline=True)

        if before.icon != after.icon and after.icon:
            embed.set_image(url=after.icon.url)

        embed.set_footer(text=f"Guild ID: {after.id}")
        await channel.send(embed=embed)

    # ── Invite Events ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        channel = await self._get_log_channel(invite.guild.id, "ServerInviteCreate")
        if not channel:
            return

        expires = f"<t:{int(invite.expires_at.timestamp())}:F>" if invite.expires_at else "Never"
        max_uses = f"{invite.max_uses} uses" if invite.max_uses else "No limit"

        embed = discord.Embed(color=0xfee75c, timestamp=d.now(), title="Invite Created")
        embed.add_field(name="Code", value=f"[{invite.code}]({invite.url})", inline=False)
        embed.add_field(name="Max Uses", value=max_uses, inline=True)
        embed.add_field(name="Expires", value=expires, inline=True)
        embed.add_field(name="Inviter", value=invite.inviter.mention if invite.inviter else "Unknown", inline=False)
        embed.add_field(name="Channel", value=invite.channel.mention, inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        channel = await self._get_log_channel(invite.guild.id, "ServerInviteDelete")
        if not channel:
            return
        if not invite.inviter:
            return

        expires = f"<t:{int(invite.expires_at.timestamp())}:F>" if invite.expires_at else "Never"
        max_uses = f"{invite.max_uses} uses" if invite.max_uses else "No limit"

        embed = discord.Embed(color=0xED4245, timestamp=d.now(), title="Invite Deleted")
        embed.add_field(name="Code", value=f"[{invite.code}]({invite.url})", inline=False)
        embed.add_field(name="Max Uses", value=max_uses, inline=True)
        embed.add_field(name="Expires", value=expires, inline=True)
        embed.add_field(name="Inviter", value=invite.inviter.mention, inline=False)
        embed.add_field(name="Channel", value=invite.channel.mention, inline=False)
        await channel.send(embed=embed)

    # ── Channel Events ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log = await self._get_log_channel(channel.guild.id, "ChannelCreate")
        if not log:
            return

        kind = "Text" if isinstance(channel, discord.TextChannel) else "Voice" if isinstance(channel, discord.VoiceChannel) else "Channel"
        embed = discord.Embed(
            color=0x57F287,
            timestamp=d.now(),
            title=f"{kind} Channel Created",
            description=f"**Name:** {channel.mention}\n**Category:** {channel.category or 'None'}"
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await log.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log = await self._get_log_channel(channel.guild.id, "ChannelDelete")
        if not log:
            return

        kind = "Text" if isinstance(channel, discord.TextChannel) else "Voice" if isinstance(channel, discord.VoiceChannel) else "Channel"
        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title=f"{kind} Channel Deleted",
            description=f"**Name:** {channel.name}\n**Category:** {channel.category or 'None'}"
        )
        embed.set_footer(text=f"Channel ID: {channel.id}")
        await log.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        log = await self._get_log_channel(after.guild.id, "ChannelUpdate")
        if not log:
            return

        # Skip permission overwrite and position-only changes
        if before.overwrites != after.overwrites:
            return
        if before.position != after.position:
            return

        before_vals = []
        after_vals = []

        if before.name != after.name:
            before_vals.append(f"**Name:** {before.name}")
            after_vals.append(f"**Name:** {after.name}")
        if before.category != after.category:
            before_vals.append(f"**Category:** {before.category or 'None'}")
            after_vals.append(f"**Category:** {after.category or 'None'}")

        if isinstance(after, discord.TextChannel):
            kind = "Text"
            if before.topic != after.topic:
                before_vals.append(f"**Topic:** {before.topic or 'None'}")
                after_vals.append(f"**Topic:** {after.topic or 'None'}")
            if before.slowmode_delay != after.slowmode_delay:
                before_vals.append(f"**Slowmode:** {before.slowmode_delay}s")
                after_vals.append(f"**Slowmode:** {after.slowmode_delay}s")

        elif isinstance(after, discord.VoiceChannel):
            kind = "Voice"
            if before.bitrate != after.bitrate:
                before_vals.append(f"**Bitrate:** {before.bitrate // 1000}kbps")
                after_vals.append(f"**Bitrate:** {after.bitrate // 1000}kbps")
            if before.user_limit != after.user_limit:
                before_vals.append(f"**User Limit:** {before.user_limit}")
                after_vals.append(f"**User Limit:** {after.user_limit}")
        else:
            kind = "Channel"

        if not before_vals:
            return  # Nothing worth logging changed

        embed = discord.Embed(color=0xfee75c, timestamp=d.now(), title=f"{kind} Channel Updated")
        embed.add_field(name="Before", value="\n".join(before_vals), inline=True)
        embed.add_field(name="After", value="\n".join(after_vals), inline=True)
        embed.set_footer(text=f"Channel ID: {after.id}")
        await log.send(embed=embed)

    # ── Role Events ───────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        channel = await self._get_log_channel(role.guild.id, "RoleCreate")
        if not channel:
            return

        embed = discord.Embed(
            color=0x57F287,
            timestamp=d.now(),
            title="Role Created",
            description=(
                f"**Name:** {role.mention}\n"
                f"**Color:** {role.colors.primary}\n"
                f"**Mentionable:** {role.mentionable}\n"
                f"**Hoisted:** {role.hoist}"
            )
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        channel = await self._get_log_channel(role.guild.id, "RoleDelete")
        if not channel:
            return

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title="Role Deleted",
            description=(
                f"**Name:** {role.name}\n"
                f"**Color:** {role.colors.primary}\n"
                f"**Mentionable:** {role.mentionable}\n"
                f"**Hoisted:** {role.hoist}"
            )
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        channel = await self._get_log_channel(after.guild.id, "RoleUpdate")
        if not channel:
            return

        # Skip position-only changes (Discord fires this constantly)
        if before.position != after.position:
            return

        before_vals = []
        after_vals = []

        if before.name != after.name:
            before_vals.append(f"**Name:** {before.name}")
            after_vals.append(f"**Name:** {after.name}")
        if before.colors.primary != after.colors.primary:
            before_vals.append(f"**Color:** {before.colors.primary}")
            after_vals.append(f"**Color:** {after.colors.primary}")
        if before.hoist != after.hoist:
            before_vals.append(f"**Hoisted:** {before.hoist}")
            after_vals.append(f"**Hoisted:** {after.hoist}")
        if before.mentionable != after.mentionable:
            before_vals.append(f"**Mentionable:** {before.mentionable}")
            after_vals.append(f"**Mentionable:** {after.mentionable}")

        if not before_vals:
            return  # Nothing worth logging changed

        embed = discord.Embed(
            color=0xfee75c,
            timestamp=d.now(),
            title=f'Role Updated: "{before.name}"'
        )
        embed.add_field(name="Before", value="\n".join(before_vals), inline=True)
        embed.add_field(name="After", value="\n".join(after_vals), inline=True)
        embed.set_footer(text=f"Role ID: {after.id}")
        await channel.send(embed=embed)


def setup(client):
    client.add_cog(events(client))