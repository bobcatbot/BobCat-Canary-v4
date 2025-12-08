import discord
import asyncio
from discord.ext import commands
from modules import bot as v

class TempVoice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.channel_creation_lock = {}  # prevents duplicate channels if event fires twice

    # ------------------------------------------------------
    #   EVENT: Voice state update
    # ------------------------------------------------------
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        # ======================================================
        # CREATE
        # ======================================================
        if after.channel:
            await self.handle_join(member, after.channel)

        # ======================================================
        # DELETE
        # ======================================================
        if before.channel:
            await self.handle_leave(before.channel)


    # ------------------------------------------------------
    #   JOINS HUB  → CREATE TEMP CHANNEL
    # ------------------------------------------------------
    async def handle_join(self, member: discord.Member, hub_channel: discord.VoiceChannel):

        hubs = v.db.get_dash(hub_channel.guild)['temporary_channels']['hubs']
        tempvoice_db = v.db.get_server_config(hub_channel.guild)['temporary_channels']

        hub = next((h for h in hubs if h['channel_id'] == str(hub_channel.id)), None)
        if hub is None:
            return  # not a tempvoice hub

        # Prevent race-conditions
        if member.id in self.channel_creation_lock:
            return
        self.channel_creation_lock[member.id] = True

        try:
            # Determine PERMISSIONS
            if hub['sync_hub_category']:
                category = discord.utils.get(hub_channel.guild.categories, id=int(hub['category_id']))
                overwrites = category.overwrites.copy()
            else:
                overwrites = {}

            # Give creator full perms
            mod_perms = discord.PermissionOverwrite(**hub["permissions"])
            overwrites[member] = mod_perms

            # Determine index
            idx = 1
            guild_tcs = [tc for tc in tempvoice_db if tc["guild_id"] == hub_channel.guild.id]
            if guild_tcs:
                idx = guild_tcs[-1]["index"] + 1

            # CREATE VOICE CHANNEL
            new_chan = await hub_channel.guild.create_voice_channel(
                name=hub['name'].format(index=idx, username=member.name),
                category=hub_channel.category,
                user_limit=hub['user_limit'],
                bitrate=hub['bitrate'],
                overwrites=overwrites
            )

            await member.move_to(new_chan)

            v.db.update_server_config(
                hub_channel.guild,
                key=f"temporary_channels.{len(tempvoice_db)}",
                value={
                    "index": idx,
                    "guild_id": hub_channel.guild.id,
                    "channel_id": new_chan.id,
                    "creator": member.id
                }
            )

        finally:
            await asyncio.sleep(0.5)
            self.channel_creation_lock.pop(member.id, None)


    # ------------------------------------------------------
    #   LEAVES CHANNEL → DELETE IF EMPTY
    # ------------------------------------------------------
    async def handle_leave(self, channel: discord.VoiceChannel):
        tcs = v.db.get_server_config(channel.guild)['temporary_channels']

        # Find matching entry
        entry_idx = None
        for idx, tc in enumerate(tcs):
            if tc["channel_id"] == channel.id:
                entry_idx = idx
                break

        if entry_idx is None: # not a temp channel
            return

        await asyncio.sleep(0.5) # Wait for member list to update

        # Not empty → do nothing
        if len(channel.members) > 0:
            return

        # Delete channel
        try:
            await channel.delete()
        except:
            pass

    # ------------------------------------------------------
    #   UPDATE HUB NAME ON CHANNEL RENAME
    # ------------------------------------------------------
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):

        if not isinstance(after, discord.VoiceChannel):
            return

        hubs = v.db.get_dash(after.guild)['temporary_channels']['hubs']
        hub = next((h for h in hubs if h['channel_id'] == str(after.id)), None)

        if hub:
            v.db.update_dash(
                after.guild,
                key=f"temporary_channels.hubs.{hubs.index(hub)}.hub_name",
                value=after.name
            )

    # Manage your voice channel pannel
    @commands.slash_command(name="tempvoice-manage", description="Manage your temporary voice channel")
    async def tempvoice_manage(self, ctx: discord.ApplicationContext):
        tcs: list = v.db.get_server_config(ctx.guild)['temporary_channels']

        if not ctx.interaction.user.voice:
            return await ctx.send("You must be connected to a voice channel to use this command.")

        tempvoice = None
        for _tc in tcs:
            if _tc['channel_id'] == ctx.interaction.user.voice.channel.id and _tc['creator'] == ctx.interaction.user.id:
                tempvoice = _tc

        if tempvoice is None:
            return await ctx.respond("Access denied. You must be in your own voice channel to use this command.", ephemeral=True)
        
        view = discord.ui.View()
        
        add_space = discord.ui.Button(label="+", style=discord.ButtonStyle.primary, custom_id="add_space")
        async def add_space_callback(interaction: discord.Interaction):
            channel = discord.utils.get(interaction.guild.voice_channels, id=tempvoice['channel_id'])
            await channel.edit(user_limit=channel.user_limit + 1)

            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description="Voice member limit increased",
            )
            return await interaction.response.send_message(embed=embed)
        add_space.callback = add_space_callback
        view.add_item(add_space)

        remove_space = discord.ui.Button(label="-", style=discord.ButtonStyle.danger, custom_id="remove_space")
        async def remove_space_callback(interaction: discord.Interaction):
            channel = discord.utils.get(interaction.guild.voice_channels, id=tempvoice['channel_id'])
            await channel.edit(user_limit=channel.user_limit - 1)

            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description="Voice member limit decreased",
            )
            return await interaction.response.send_message(embed=embed)
        remove_space.callback = remove_space_callback
        view.add_item(remove_space)

        kick_member = discord.ui.Button(label="K", style=discord.ButtonStyle.danger, custom_id="kick_member")
        async def kick_member_callback(interaction: discord.Interaction):
            class UserKickView(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.user_select(
                    placeholder="Select a member to kick",
                    min_values=1,
                    max_values=1,
                )
                async def callback(self, select, interaction: discord.Interaction):
                    member = interaction.guild.get_member(select.values[0].id)
                    await member.move_to(None)

                    embed = discord.Embed(
                        color=v.style(ctx.guild.id),
                        description=f"{member.display_name} has been kicked from the voice channel",
                    )
                    return await interaction.response.edit_message(embed=embed, view=None)
            
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description="Who do you want to kick from the voice channel?",
            )
            return await interaction.response.send_message(embed=embed, view=UserKickView(), ephemeral=True)
        kick_member.callback = kick_member_callback
        view.add_item(kick_member)
        
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title="Manage your voice channel",
            description=(
                f"+ - Add 1 space to your voice channel"
                f"\n- - Remove 1 space from your voice channel"
                f"\nK - Kick a member from your voice channel"
            )
        )
        await ctx.respond(embed=embed, view=view)
    
def setup(bot):
    bot.add_cog(TempVoice(bot))

# channelName = "#{index} | {member.name}'s Channel"
# chan_id = "1123892899130650686"
# userLimit = 5
# bitrate = 96000
# perms_sync = True # Sync perms with category
# modRoles = []
# mod_perms = {
#     "manage_channels": True,
#     "manage_permissions": True,
#     "priority_speaker": True,
#     "move_members": True,
# }