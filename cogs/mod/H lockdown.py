import discord
from typing import Union
from discord.ext import commands
from modules import bot as v


class mod_lockdown(commands.Cog):
    def __init__(self, client):
        self.client = client

    lockdown = discord.SlashCommandGroup(name="lockdown", description="Lockdown a channel/server")
    lock   = lockdown.create_subgroup(name="add",    description="Lockdown commands")
    unlock = lockdown.create_subgroup(name="remove", description="Unlock commands")

    # ── Shared helper ─────────────────────────────────────────────────────────

    def _missing_perms_embed(self, perm: str) -> discord.Embed:
        return discord.Embed(
            color=v.error,
            title="Missing Permission",
            description=f"❌ You are missing `{perm}` permission",
        )

    def _bot_missing_perms_embed(self, perm: str) -> discord.Embed:
        return discord.Embed(
            color=v.error,
            title="Missing Permission",
            description=f"❌ BobCat is missing `{perm}` permission",
        )

    # ── Lock ──────────────────────────────────────────────────────────────────

    @lock.command(name="channel", description="Lockdown a channel")
    @discord.option("channel", description="Channel to lockdown", required=True)
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
                title=f"🔒 #{channel.name} has been locked",
                description="You will gain access again once the lockdown is lifted.",
            )
        )

    @lockdown_channel.error
    async def lockdown_channel_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed("Manage Channels"), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to lockdown channels", description='Please give BobCat the "Manage Channels" permission')
            return await ctx.respond(embed=self._bot_missing_perms_embed("Manage Channels"), ephemeral=True)

    @lock.command(name="server", description="Lockdown the server")
    @discord.option("hidden", bool, description="Hide all channels from non-admins", required=False)
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def lockdown_server(self, ctx: discord.ApplicationContext, hidden: bool = False):
        await ctx.defer()

        everyone: discord.Role = ctx.guild.default_role
        # Snapshot the bits we're changing so unlock_server can restore them exactly
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
                    title="Server is currently locked",
                    description=(
                        "This server has been fully locked down by staff.\n"
                        "You will not be able to see or talk in channels until this is lifted.\n"
                        "**Please be patient.**"
                    ),
                )
            )
            desc = "All channels are now hidden. A temporary status channel has been created for announcements."
        else:
            desc = "You will gain access again once the lockdown is lifted."

        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                title="🔒 Server channels have been locked",
                description=desc,
            )
        )

    @lockdown_server.error
    async def lockdown_server_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed("Manage Channels"), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to lockdown the server", description='Please give BobCat the "Manage Channels" and "Manage Roles" permissions')
            return await ctx.respond(embed=self._bot_missing_perms_embed("Manage Channels / Manage Roles"), ephemeral=True)

    # ── Unlock ────────────────────────────────────────────────────────────────

    @unlock.command(name="channel", description="Unlock a channel")
    @discord.option("channel", description="Channel to unlock", required=True)
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
                title=f"🔓 #{channel.name} has been unlocked",
                description="Everyone now has access to this channel.",
            )
        )

    @unlock_channel.error
    async def unlock_channel_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed("Manage Channels"), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to unlock channels", description='Please give BobCat the "Manage Channels" permission')
            return await ctx.respond(embed=self._bot_missing_perms_embed("Manage Channels"), ephemeral=True)

    @unlock.command(name="server", description="Unlock the server")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def unlock_server(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        everyone: discord.Role = ctx.guild.default_role
        new_perms = discord.Permissions(everyone.permissions.value)
        # Only undo the specific bits lockdown set — don't grant new permissions
        new_perms.update(send_messages=True, read_messages=True, send_messages_in_threads=True, create_public_threads=True, connect=True)
        await everyone.edit(permissions=new_perms, reason=f"Server unlock by {ctx.author}")

        status_chan = discord.utils.get(ctx.guild.text_channels, name="server-locked")
        if status_chan:
            await status_chan.delete(reason="Lockdown lifted")

        await ctx.respond(
            embed=discord.Embed(
                color=v.style(ctx.guild.id),
                title="🔓 Server has been unlocked",
                description="All channels are accessible again.",
            )
        )

    @unlock_server.error
    async def unlock_server_error(self, ctx: discord.ApplicationContext, error: Exception):
        if isinstance(error, commands.MissingPermissions):
            return await ctx.respond(embed=self._missing_perms_embed("Manage Channels"), ephemeral=True)
        if isinstance(error, commands.BotMissingPermissions):
            await v.push_notification(ctx.guild, types="error", title="BobCat is missing permission to unlock the server", description='Please give BobCat the "Manage Channels" and "Manage Roles" permissions')
            return await ctx.respond(embed=self._bot_missing_perms_embed("Manage Channels / Manage Roles"), ephemeral=True)

def setup(client):
    client.add_cog(mod_lockdown(client))