import discord
from discord.ext import commands
from datetime import datetime as d
from modules import bot as v
from modules.models import Guild

class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    # ── Helper ────────────────────────────────────────────────────────────────
    async def _get_logging(self, guild_id: int):
        return (await Guild.get(str(guild_id))).dashboard.moderation.logging

    async def _get_log_channel(self, guild_id: int, event: str) -> discord.TextChannel | None:
        """Returns the log channel if the event is enabled, otherwise None."""
        logging = await self._get_logging(guild_id)

        if not logging.events.get(event, False):
            return None

        if not logging.channel:
            return None

        return self.client.get_channel(int(logging.channel))

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
            title=v.t.msg(member.guild, "logging.member_join.title"),
            description=v.t.msg(member.guild, "logging.member_join.description", member=member.mention, roles=roles or v.t.msg(member.guild, "logging.helpers.none"))
        )
        self._author(embed, member)
        embed.set_footer(text=v.t.msg(member.guild, "logging.helpers.id_footer", id=member.id))
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
            title=v.t.msg(member.guild, "logging.member_leave.title"),
            description=v.t.msg(member.guild, "logging.member_leave.description", member=member.mention, roles=roles or v.t.msg(member.guild, "logging.helpers.none"))
        )
        self._author(embed, member)
        embed.set_footer(text=v.t.msg(member.guild, "logging.helpers.id_footer", id=member.id))
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
                title=v.t.msg(after.guild, "logging.nickname_changed.title"),
                description=v.t.msg(after.guild, "logging.nickname_changed.description", before=before.display_name, after=after.display_name)
            )
            self._author(embed, after)
            embed.set_footer(text=v.t.msg(after.guild, "logging.helpers.user_id_footer", id=after.id))
            await channel.send(embed=embed)

        # Role changes
        added_roles = [r for r in after.roles if r not in before.roles]
        removed_roles = [r for r in before.roles if r not in after.roles]

        if added_roles or removed_roles:
            desc = ""
            if added_roles:
                desc += v.t.msg(after.guild, "logging.roles_updated.added", roles=' '.join(r.mention for r in added_roles))
            if removed_roles:
                desc += v.t.msg(after.guild, "logging.roles_updated.removed", roles=' '.join(r.mention for r in removed_roles))

            embed = discord.Embed(
                color=0xfee75c,
                timestamp=d.now(),
                title=v.t.msg(after.guild, "logging.roles_updated.title"),
                description=desc
            )
            self._author(embed, after)
            embed.set_footer(text=v.t.msg(after.guild, "logging.helpers.user_id_footer", id=after.id))
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.User):
        channel = await self._get_log_channel(guild.id, "MemberBan")
        if not channel:
            return

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title=v.t.msg(guild, "logging.member_banned.title"),
            description=f"{member.mention}"
        )
        self._author(embed, member)  # fixed: was member.author
        embed.set_footer(text=v.t.msg(guild, "logging.helpers.id_footer", id=member.id))
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.User):
        channel = await self._get_log_channel(guild.id, "MemberUnban")
        if not channel:
            return

        embed = discord.Embed(
            color=0x57F287,
            timestamp=d.now(),
            title=v.t.msg(guild, "logging.member_unbanned.title"),  # fixed: was "unbaned"
            description=f"{member.mention}"
        )
        self._author(embed, member)
        embed.set_footer(text=v.t.msg(guild, "logging.helpers.id_footer", id=member.id))
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
        if (await self._get_logging(message.guild.id)).bots and message.author.bot:
            return

        content = message.content or v.t.msg(message.guild, "logging.message_deleted.no_content")
        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title=v.t.msg(message.guild, "logging.message_deleted.title"),
            description=v.t.msg(
                message.guild, "logging.message_deleted.description",
                channel=message.channel.mention, channel_id=message.channel.id,
                author=message.author.mention, author_id=message.author.id,
                content=content[:1000],
            )
        )
        self._author(embed, message.author)
        embed.set_footer(text=v.t.msg(message.guild, "logging.helpers.message_id_footer", id=message.id))

        # Add attachments if present
        if message.attachments:
            attachment_urls = "\n".join([f"[{a.filename}]({a.url})" for a in message.attachments])
            embed.add_field(
                name=v.t.msg(message.guild, "logging.message_deleted.attachments_field"),
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

        if (await self._get_logging(after.guild.id)).bots and after.author.bot:
            return

        embed = discord.Embed(
            color=0xfaa71f,
            timestamp=d.now(),
            title=v.t.msg(after.guild, "logging.message_edited.title"),
            description=v.t.msg(
                after.guild, "logging.message_edited.description",
                author=after.author.mention, author_id=after.author.id,
                channel=after.channel.mention, channel_id=after.channel.id,
                jump_url=after.jump_url, before=before.content[:500], after=after.content[:500],
            )
        )
        self._author(embed, before.author)
        embed.set_footer(text=v.t.msg(after.guild, "logging.helpers.message_id_footer", id=after.id))

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
            before_vals.append(v.t.msg(after, "logging.server_updated.name", value=before.name))
            after_vals.append(v.t.msg(after, "logging.server_updated.name", value=after.name))
        if before.icon != after.icon:
            before_vals.append(v.t.msg(after, "logging.server_updated.icon_before"))
            after_vals.append(v.t.msg(after, "logging.server_updated.icon_after"))
        if before.afk_channel != after.afk_channel:
            before_vals.append(v.t.msg(after, "logging.server_updated.afk_channel", value=before.afk_channel or v.t.msg(after, "logging.helpers.none")))
            after_vals.append(v.t.msg(after, "logging.server_updated.afk_channel", value=after.afk_channel or v.t.msg(after, "logging.helpers.none")))
        if before.afk_timeout != after.afk_timeout:
            before_vals.append(v.t.msg(after, "logging.server_updated.afk_timeout", minutes=before.afk_timeout // 60))
            after_vals.append(v.t.msg(after, "logging.server_updated.afk_timeout", minutes=after.afk_timeout // 60))
        if before.verification_level != after.verification_level:
            before_vals.append(v.t.msg(after, "logging.server_updated.verification", value=str(before.verification_level).title()))
            after_vals.append(v.t.msg(after, "logging.server_updated.verification", value=str(after.verification_level).title()))

        if not before_vals:
            return  # Nothing worth logging changed

        empty = v.t.msg(after, "logging.server_updated.empty_fallback")
        embed = discord.Embed(color=0xfee75c, timestamp=d.now(), title=v.t.msg(after, "logging.server_updated.title"))
        embed.add_field(name=v.t.msg(after, "logging.helpers.before_field"), value="\n".join(before_vals) or empty, inline=True)
        embed.add_field(name=v.t.msg(after, "logging.helpers.after_field"), value="\n".join(after_vals) or empty, inline=True)

        if before.icon != after.icon and after.icon:
            embed.set_image(url=after.icon.url)

        embed.set_footer(text=v.t.msg(after, "logging.helpers.guild_id_footer", id=after.id))
        await channel.send(embed=embed)

    # ── Invite Events ─────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        channel = await self._get_log_channel(invite.guild.id, "ServerInviteCreate")
        if not channel:
            return

        expires = f"<t:{int(invite.expires_at.timestamp())}:F>" if invite.expires_at else v.t.msg(invite.guild, "logging.invite.expires_never")
        max_uses = v.t.msg(invite.guild, "logging.invite.max_uses_limit", uses=invite.max_uses) if invite.max_uses else v.t.msg(invite.guild, "logging.invite.max_uses_unlimited")

        embed = discord.Embed(color=0xfee75c, timestamp=d.now(), title=v.t.msg(invite.guild, "logging.invite_created.title"))
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.code_field"), value=v.t.msg(invite.guild, "logging.invite.code_value", code=invite.code, url=invite.url), inline=False)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.max_uses_field"), value=max_uses, inline=True)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.expires_field"), value=expires, inline=True)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.inviter_field"), value=invite.inviter.mention if invite.inviter else v.t.msg(invite.guild, "logging.invite.inviter_unknown"), inline=False)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.channel_field"), value=invite.channel.mention, inline=False)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        channel = await self._get_log_channel(invite.guild.id, "ServerInviteDelete")
        if not channel:
            return
        if not invite.inviter:
            return

        expires = f"<t:{int(invite.expires_at.timestamp())}:F>" if invite.expires_at else v.t.msg(invite.guild, "logging.invite.expires_never")
        max_uses = v.t.msg(invite.guild, "logging.invite.max_uses_limit", uses=invite.max_uses) if invite.max_uses else v.t.msg(invite.guild, "logging.invite.max_uses_unlimited")

        embed = discord.Embed(color=0xED4245, timestamp=d.now(), title=v.t.msg(invite.guild, "logging.invite_deleted.title"))
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.code_field"), value=v.t.msg(invite.guild, "logging.invite.code_value", code=invite.code, url=invite.url), inline=False)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.max_uses_field"), value=max_uses, inline=True)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.expires_field"), value=expires, inline=True)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.inviter_field"), value=invite.inviter.mention, inline=False)
        embed.add_field(name=v.t.msg(invite.guild, "logging.invite.channel_field"), value=invite.channel.mention, inline=False)
        await channel.send(embed=embed)

    # ── Channel Events ────────────────────────────────────────────────────────

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        log = await self._get_log_channel(channel.guild.id, "ChannelCreate")
        if not log:
            return

        kind = v.t.msg(channel.guild, "logging.helpers.kind_text") if isinstance(channel, discord.TextChannel) else v.t.msg(channel.guild, "logging.helpers.kind_voice") if isinstance(channel, discord.VoiceChannel) else v.t.msg(channel.guild, "logging.helpers.kind_channel")
        embed = discord.Embed(
            color=0x57F287,
            timestamp=d.now(),
            title=v.t.msg(channel.guild, "logging.channel_created.title", kind=kind),
            description=v.t.msg(channel.guild, "logging.channel_created.description", name=channel.mention, category=channel.category or v.t.msg(channel.guild, "logging.helpers.none"))
        )
        embed.set_footer(text=v.t.msg(channel.guild, "logging.helpers.channel_id_footer", id=channel.id))
        await log.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        log = await self._get_log_channel(channel.guild.id, "ChannelDelete")
        if not log:
            return

        kind = v.t.msg(channel.guild, "logging.helpers.kind_text") if isinstance(channel, discord.TextChannel) else v.t.msg(channel.guild, "logging.helpers.kind_voice") if isinstance(channel, discord.VoiceChannel) else v.t.msg(channel.guild, "logging.helpers.kind_channel")
        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title=v.t.msg(channel.guild, "logging.channel_deleted.title", kind=kind),
            description=v.t.msg(channel.guild, "logging.channel_deleted.description", name=channel.name, category=channel.category or v.t.msg(channel.guild, "logging.helpers.none"))
        )
        embed.set_footer(text=v.t.msg(channel.guild, "logging.helpers.channel_id_footer", id=channel.id))
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
            before_vals.append(v.t.msg(after.guild, "logging.channel_updated.name", value=before.name))
            after_vals.append(v.t.msg(after.guild, "logging.channel_updated.name", value=after.name))
        if before.category != after.category:
            before_vals.append(v.t.msg(after.guild, "logging.channel_updated.category", value=before.category or v.t.msg(after.guild, "logging.helpers.none")))
            after_vals.append(v.t.msg(after.guild, "logging.channel_updated.category", value=after.category or v.t.msg(after.guild, "logging.helpers.none")))

        if isinstance(after, discord.TextChannel):
            kind = v.t.msg(after.guild, "logging.helpers.kind_text")
            if before.topic != after.topic:
                before_vals.append(v.t.msg(after.guild, "logging.channel_updated.topic", value=before.topic or v.t.msg(after.guild, "logging.helpers.none")))
                after_vals.append(v.t.msg(after.guild, "logging.channel_updated.topic", value=after.topic or v.t.msg(after.guild, "logging.helpers.none")))
            if before.slowmode_delay != after.slowmode_delay:
                before_vals.append(v.t.msg(after.guild, "logging.channel_updated.slowmode", seconds=before.slowmode_delay))
                after_vals.append(v.t.msg(after.guild, "logging.channel_updated.slowmode", seconds=after.slowmode_delay))

        elif isinstance(after, discord.VoiceChannel):
            kind = v.t.msg(after.guild, "logging.helpers.kind_voice")
            if before.bitrate != after.bitrate:
                before_vals.append(v.t.msg(after.guild, "logging.channel_updated.bitrate", kbps=before.bitrate // 1000))
                after_vals.append(v.t.msg(after.guild, "logging.channel_updated.bitrate", kbps=after.bitrate // 1000))
            if before.user_limit != after.user_limit:
                before_vals.append(v.t.msg(after.guild, "logging.channel_updated.user_limit", value=before.user_limit))
                after_vals.append(v.t.msg(after.guild, "logging.channel_updated.user_limit", value=after.user_limit))
        else:
            kind = v.t.msg(after.guild, "logging.helpers.kind_channel")

        if not before_vals:
            return  # Nothing worth logging changed

        embed = discord.Embed(color=0xfee75c, timestamp=d.now(), title=v.t.msg(after.guild, "logging.channel_updated.title", kind=kind))
        embed.add_field(name=v.t.msg(after.guild, "logging.helpers.before_field"), value="\n".join(before_vals), inline=True)
        embed.add_field(name=v.t.msg(after.guild, "logging.helpers.after_field"), value="\n".join(after_vals), inline=True)
        embed.set_footer(text=v.t.msg(after.guild, "logging.helpers.channel_id_footer", id=after.id))
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
            title=v.t.msg(role.guild, "logging.role_created.title"),
            description=v.t.msg(
                role.guild, "logging.role_created.description",
                name=role.mention, color=role.colors.primary, mentionable=role.mentionable, hoisted=role.hoist,
            )
        )
        embed.set_footer(text=v.t.msg(role.guild, "logging.helpers.role_id_footer", id=role.id))
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        channel = await self._get_log_channel(role.guild.id, "RoleDelete")
        if not channel:
            return

        embed = discord.Embed(
            color=0xED4245,
            timestamp=d.now(),
            title=v.t.msg(role.guild, "logging.role_deleted.title"),
            description=v.t.msg(
                role.guild, "logging.role_deleted.description",
                name=role.name, color=role.colors.primary, mentionable=role.mentionable, hoisted=role.hoist,
            )
        )
        embed.set_footer(text=v.t.msg(role.guild, "logging.helpers.role_id_footer", id=role.id))
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
            before_vals.append(v.t.msg(after.guild, "logging.role_updated.name", value=before.name))
            after_vals.append(v.t.msg(after.guild, "logging.role_updated.name", value=after.name))
        if before.colors.primary != after.colors.primary:
            before_vals.append(v.t.msg(after.guild, "logging.role_updated.color", value=before.colors.primary))
            after_vals.append(v.t.msg(after.guild, "logging.role_updated.color", value=after.colors.primary))
        if before.hoist != after.hoist:
            before_vals.append(v.t.msg(after.guild, "logging.role_updated.hoisted", value=before.hoist))
            after_vals.append(v.t.msg(after.guild, "logging.role_updated.hoisted", value=after.hoist))
        if before.mentionable != after.mentionable:
            before_vals.append(v.t.msg(after.guild, "logging.role_updated.mentionable", value=before.mentionable))
            after_vals.append(v.t.msg(after.guild, "logging.role_updated.mentionable", value=after.mentionable))

        if not before_vals:
            return  # Nothing worth logging changed

        embed = discord.Embed(
            color=0xfee75c,
            timestamp=d.now(),
            title=v.t.msg(after.guild, "logging.role_updated.title", name=before.name)
        )
        embed.add_field(name=v.t.msg(after.guild, "logging.helpers.before_field"), value="\n".join(before_vals), inline=True)
        embed.add_field(name=v.t.msg(after.guild, "logging.helpers.after_field"), value="\n".join(after_vals), inline=True)
        embed.set_footer(text=v.t.msg(after.guild, "logging.helpers.role_id_footer", id=after.id))
        await channel.send(embed=embed)


def setup(client):
    client.add_cog(events(client))