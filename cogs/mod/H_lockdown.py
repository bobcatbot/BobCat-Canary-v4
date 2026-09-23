import discord
from typing import Union
from discord.ext import commands
from modules import bot as v
from modules.models import Guild


class mod_lockdown(commands.Cog):
    def __init__(self, client):
        self.client = client

    lockdown = discord.SlashCommandGroup(
        name="lockdown",
        description=v.t.msg(None, "lockdown.group.description"),
        name_localizations=v.t.localizations("lockdown.group.name"),
        description_localizations=v.t.localizations("lockdown.group.description"),
    )
    lock = lockdown.create_subgroup(
        name="add",
        description=v.t.msg(None, "lockdown.add_group.description"),
        name_localizations=v.t.localizations("lockdown.add_group.name"),
        description_localizations=v.t.localizations("lockdown.add_group.description"),
    )
    unlock = lockdown.create_subgroup(
        name="remove",
        description=v.t.msg(None, "lockdown.remove_group.description"),
        name_localizations=v.t.localizations("lockdown.remove_group.name"),
        description_localizations=v.t.localizations("lockdown.remove_group.description"),
    )

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _missing_perms_embed(self, guild, perm: str) -> discord.Embed:
        return discord.Embed(
            color=v.error,
            title=v.t.msg(guild, "lockdown.missing_perms.title"),
            description=v.t.msg(guild, "lockdown.missing_perms.description", perm=perm),
        )

    def _bot_missing_perms_embed(self, guild, perm: str) -> discord.Embed:
        return discord.Embed(
            color=v.error,
            title=v.t.msg(guild, "lockdown.bot_missing_perms.title"),
            description=v.t.msg(guild, "lockdown.bot_missing_perms.description", perm=perm),
        )

    # ── Lock ──────────────────────────────────────────────────────────────────

    @lock.command(
        name="channel",
        description=v.t.msg(None, "lockdown.lock_channel.cmd.description"),
        name_localizations=v.t.localizations("lockdown.lock_channel.cmd.name"),
        description_localizations=v.t.localizations("lockdown.lock_channel.cmd.description"),
    )
    @discord.option(
        "channel",
        description=v.t.msg(None, "lockdown.lock_channel.cmd.options.channel.description"),
        name_localizations=v.t.localizations("lockdown.lock_channel.cmd.options.channel.name"),
        description_localizations=v.t.localizations("lockdown.lock_channel.cmd.options.channel.description"),
        required=True,
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def lockdown_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.ForumChannel],
    ):
        # Merge into existing overwrite so we don't wipe unrelated permission entries
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if isinstance(channel, discord.ForumChannel):
            # Forum channels use create_public_threads ("Create Posts") and
            # send_messages_in_threads ("Send Messages in Posts")
            overwrite.create_public_threads = False
            overwrite.send_messages_in_threads = False
        elif isinstance(channel, discord.VoiceChannel):
            overwrite.send_messages = False
            overwrite.connect = False
        else:
            overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                title=v.t.msg(ctx.guild, "lockdown.lock_channel.success_title", channel=channel.name),
                description=v.t.msg(ctx.guild, "lockdown.access_restored_desc"),
            )
        )

    @lockdown_channel.error
    async def lockdown_channel_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed(ctx.guild, v.t.msg(ctx.guild, "lockdown.perms.manage_channels")), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, kind="error", title="BobCat is missing permission to lockdown channels", description='Please give BobCat the "Manage Channels" permission')
            return await ctx.respond(embed=self._bot_missing_perms_embed(ctx.guild, v.t.msg(ctx.guild, "lockdown.perms.manage_channels")), ephemeral=True)

    @lock.command(
        name="server",
        description=v.t.msg(None, "lockdown.lock_server.cmd.description"),
        name_localizations=v.t.localizations("lockdown.lock_server.cmd.name"),
        description_localizations=v.t.localizations("lockdown.lock_server.cmd.description"),
    )
    @discord.option(
        "hidden", bool,
        description=v.t.msg(None, "lockdown.lock_server.cmd.options.hidden.description"),
        name_localizations=v.t.localizations("lockdown.lock_server.cmd.options.hidden.name"),
        description_localizations=v.t.localizations("lockdown.lock_server.cmd.options.hidden.description"),
        required=False,
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def lockdown_server(self, ctx: discord.ApplicationContext, hidden: bool = False):
        await ctx.defer()

        everyone: discord.Role = ctx.guild.default_role
        # Snapshot @everyone's permissions so unlock_server can restore them exactly.
        # Only saved if none is stored, so locking twice can't overwrite the real baseline.
        guild_doc = await Guild.get(str(ctx.guild.id))
        if guild_doc.lockdown_perms is None:
            guild_doc.lockdown_perms = everyone.permissions.value
            await guild_doc.save()
        new_perms = discord.Permissions(everyone.permissions.value)
        new_perms.update(send_messages=False, send_messages_in_threads=False, create_public_threads=False, connect=False)
        if hidden:
            new_perms.update(read_messages=False)
        await everyone.edit(permissions=new_perms, reason=f"Server lockdown by {ctx.author}")

        if hidden:
            public_overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            chan = await ctx.guild.create_text_channel(
                name="server-locked",
                overwrites=public_overwrites,
                reason=f"Server lockdown by {ctx.author}",
            )
            await chan.send(
                embed=discord.Embed(
                    color=v.red,
                    title=v.t.msg(ctx.guild, "lockdown.lock_server.locked_channel_title"),
                    description=v.t.msg(ctx.guild, "lockdown.lock_server.locked_channel_description"),
                )
            )
            desc = v.t.msg(ctx.guild, "lockdown.lock_server.hidden_desc")
        else:
            desc = v.t.msg(ctx.guild, "lockdown.access_restored_desc")

        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                title=v.t.msg(ctx.guild, "lockdown.lock_server.success_title"),
                description=desc,
            )
        )

    @lockdown_server.error
    async def lockdown_server_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed(ctx.guild, v.t.msg(ctx.guild, "lockdown.perms.manage_channels")), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, kind="error", title="BobCat is missing permission to lockdown the server", description='Please give BobCat the "Manage Channels" and "Manage Roles" permissions')
            perms = f"{v.t.msg(ctx.guild, 'lockdown.perms.manage_channels')} / {v.t.msg(ctx.guild, 'lockdown.perms.manage_roles')}"
            return await ctx.respond(embed=self._bot_missing_perms_embed(ctx.guild, perms), ephemeral=True)

    # ── Unlock ────────────────────────────────────────────────────────────────

    @unlock.command(
        name="channel",
        description=v.t.msg(None, "lockdown.unlock_channel.cmd.description"),
        name_localizations=v.t.localizations("lockdown.unlock_channel.cmd.name"),
        description_localizations=v.t.localizations("lockdown.unlock_channel.cmd.description"),
    )
    @discord.option(
        "channel",
        description=v.t.msg(None, "lockdown.unlock_channel.cmd.options.channel.description"),
        name_localizations=v.t.localizations("lockdown.unlock_channel.cmd.options.channel.name"),
        description_localizations=v.t.localizations("lockdown.unlock_channel.cmd.options.channel.description"),
        required=True,
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def unlock_channel(
        self,
        ctx: discord.ApplicationContext,
        channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.ForumChannel],
    ):
        # Reset to None (inherit from category/server) rather than forcing True
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        if isinstance(channel, discord.ForumChannel):
            overwrite.create_public_threads = None
            overwrite.send_messages_in_threads = None
        elif isinstance(channel, discord.VoiceChannel):
            overwrite.send_messages = None
            overwrite.connect = None
        else:
            overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                title=v.t.msg(ctx.guild, "lockdown.unlock_channel.success_title", channel=channel.name),
                description=v.t.msg(ctx.guild, "lockdown.unlock_channel.success_description"),
            )
        )

    @unlock_channel.error
    async def unlock_channel_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed(ctx.guild, v.t.msg(ctx.guild, "lockdown.perms.manage_channels")), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, kind="error", title="BobCat is missing permission to unlock channels", description='Please give BobCat the "Manage Channels" permission')
            return await ctx.respond(embed=self._bot_missing_perms_embed(ctx.guild, v.t.msg(ctx.guild, "lockdown.perms.manage_channels")), ephemeral=True)

    @unlock.command(
        name="server",
        description=v.t.msg(None, "lockdown.unlock_server.cmd.description"),
        name_localizations=v.t.localizations("lockdown.unlock_server.cmd.name"),
        description_localizations=v.t.localizations("lockdown.unlock_server.cmd.description"),
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def unlock_server(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        everyone: discord.Role = ctx.guild.default_role
        guild_doc = await Guild.get(str(ctx.guild.id))
        if guild_doc.lockdown_perms is not None:
            new_perms = discord.Permissions(guild_doc.lockdown_perms)
        else:
            # No snapshot (lockdown predates it) — fall back to re-enabling the bits lockdown turns off
            new_perms = discord.Permissions(everyone.permissions.value)
            new_perms.update(send_messages=True, read_messages=True, send_messages_in_threads=True, create_public_threads=True, connect=True)
        await everyone.edit(permissions=new_perms, reason=f"Server unlock by {ctx.author}")
        guild_doc.lockdown_perms = None
        await guild_doc.save()

        status_chan = discord.utils.get(ctx.guild.text_channels, name="server-locked")
        if status_chan:
            await status_chan.delete(reason="Lockdown lifted")

        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                title=v.t.msg(ctx.guild, "lockdown.unlock_server.success_title"),
                description=v.t.msg(ctx.guild, "lockdown.unlock_server.success_description"),
            )
        )

    @unlock_server.error
    async def unlock_server_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed(ctx.guild, v.t.msg(ctx.guild, "lockdown.perms.manage_channels")), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, kind="error", title="BobCat is missing permission to unlock the server", description='Please give BobCat the "Manage Channels" and "Manage Roles" permissions')
            perms = f"{v.t.msg(ctx.guild, 'lockdown.perms.manage_channels')} / {v.t.msg(ctx.guild, 'lockdown.perms.manage_roles')}"
            return await ctx.respond(embed=self._bot_missing_perms_embed(ctx.guild, perms), ephemeral=True)

def setup(client):
    client.add_cog(mod_lockdown(client))