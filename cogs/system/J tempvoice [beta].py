import discord
import asyncio
from discord.ext import commands
from modules import bot as v
from modules.models import Guild, TempChannel

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

        hubs = Guild.get(str(hub_channel.guild.id)).run().dashboard.temporary_channels["hubs"]
        tempvoice_db = TempChannel.find(TempChannel.guild_id == str(hub_channel.guild.id)).run()

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
            if tempvoice_db:
                idx = max(tc.index for tc in tempvoice_db) + 1

            # CREATE VOICE CHANNEL
            new_chan = await hub_channel.guild.create_voice_channel(
                name=v.render_placeholders(hub['name'], index=idx, username=member.name),
                category=hub_channel.category,
                user_limit=hub['user_limit'],
                bitrate=hub['bitrate'],
                overwrites=overwrites
            )

            await member.move_to(new_chan)

            TempChannel(
                guild_id=str(hub_channel.guild.id),
                channel_id=str(new_chan.id),
                creator_id=str(member.id),
                index=idx
            ).insert()

        finally:
            await asyncio.sleep(0.5)
            self.channel_creation_lock.pop(member.id, None)

    # ------------------------------------------------------
    #   LEAVES CHANNEL → DELETE IF EMPTY
    # ------------------------------------------------------
    async def handle_leave(self, channel: discord.VoiceChannel):
        tempvoice = TempChannel.find_one(
            TempChannel.guild_id == str(channel.guild.id),
            TempChannel.channel_id == str(channel.id),
        ).run()

        if tempvoice is None:
            return

        await asyncio.sleep(0.5)

        if channel.members:
            return

        try:
            await channel.delete()
            tempvoice.delete()
        except discord.HTTPException:
            pass

    # Manage your voice channel panel
    @commands.slash_command(name="tempvoice-manage", description="Manage your temporary voice channel")
    async def tempvoice_manage(self, ctx: discord.ApplicationContext):
        if not ctx.interaction.user.voice:
            return await ctx.send("You must be connected to a voice channel to use this command.")

        tempvoice = TempChannel.find_one(
            TempChannel.guild_id == str(ctx.guild.id),
            TempChannel.channel_id == str(ctx.interaction.user.voice.channel.id),
            TempChannel.creator_id == str(ctx.interaction.user.id),
        ).run()

        if tempvoice is None:
            return await ctx.respond("Access denied. You must be in your own voice channel to use this command.", ephemeral=True)
        
        view = discord.ui.View()
        
        add_space = discord.ui.Button(label="+", style=discord.ButtonStyle.primary, custom_id="add_space")
        async def add_space_callback(interaction: discord.Interaction):
            channel = discord.utils.get(interaction.guild.voice_channels, id=int(tempvoice.channel_id))

            if channel.user_limit >= 99:
                return await interaction.response.send_message(
                    "This channel is already at the maximum limit of 99.", ephemeral=True
                )

            await channel.edit(user_limit=channel.user_limit + 1)
            embed = discord.Embed(color=v.style(ctx.guild.id), description="Voice member limit increased")
            return await interaction.response.send_message(embed=embed)
        add_space.callback = add_space_callback
        view.add_item(add_space)

        remove_space = discord.ui.Button(label="-", style=discord.ButtonStyle.danger, custom_id="remove_space")
        async def remove_space_callback(interaction: discord.Interaction):
            channel = discord.utils.get(interaction.guild.voice_channels, id=int(tempvoice.channel_id))

            if channel.user_limit <= 0:
                return await interaction.response.send_message(
                    "This channel already has no member limit.", ephemeral=True
                )

            await channel.edit(user_limit=channel.user_limit - 1)
            embed = discord.Embed(color=v.style(ctx.guild.id), description="Voice member limit decreased")
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

                    if not member.voice or member.voice.channel.id != int(tempvoice.channel_id):
                        return await interaction.response.send_message(
                            f"{member.display_name} isn't in your voice channel.", ephemeral=True
                        )

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