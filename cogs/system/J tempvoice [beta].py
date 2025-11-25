import discord
import json
from discord.ext import commands
from modules import bot as v

class TempVoice(commands.Cog):
    def __init__(self, bot: commands.bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        
        ## Create ##
        if after.channel:
            hubs = v.db.get_dash(after.channel.guild)['temporary_channels']['hubs']
            tempvoice = v.db.get_server_config(after.channel.guild)['temporary_channels']

            hub = next((_hub for _hub in hubs if _hub['channel_id'] == str(after.channel.id)), None)

            if hub is None:
                return
            
            perms_sync = hub['sync_hub_category']
            modRoles = []
            mod_perms = hub['permissions']

            if perms_sync:
                chan = discord.utils.get(after.channel.guild.categories, id=int(hub['category_id']))
                perms = chan.overwrites
                
                if modRoles is not None:
                    for role in modRoles:
                        perms[role] = discord.PermissionOverwrite(**mod_perms)
                
                perms[member] = discord.PermissionOverwrite(**mod_perms)
            else:
                chan = after.channel.guild
                perms = { member: discord.PermissionOverwrite(**mod_perms) }
            
            idx = 1
            for tempchan in tempvoice:
                if tempchan["guild_id"] == after.channel.guild.id:
                    idx = tempchan['index'] + 1

            temp_chan = await chan.create_voice_channel(
                name=hub['name'].format(index=idx, username=member.name),
                user_limit=hub['user_limit'],
                bitrate=hub['bitrate'],
                overwrites=perms
            )
            await member.move_to(temp_chan)

            v.db.update_server_config(after.channel.guild, key=f"temporary_channels.{len(tempvoice)}", value={
                "index": idx,
                "guild_id": after.channel.guild.id,
                "channel_id": temp_chan.id,
                "creator": member.id
            })
            ###
        ##

        ## Delete ##
        if before.channel:
            for i in v.db.get_server_config(before.channel.guild)['temporary_channels']:
                if i["channel_id"] == before.channel.id and len(before.channel.members) == 0:
                    await before.channel.delete()
            return
    
    # Event listener for when the channel name of the hub is changed
    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        if not isinstance(after, discord.VoiceChannel):
            return

        channel = after
        hubs: list = v.db.get_dash(channel.guild)['temporary_channels']['hubs']

        hub = next((_hub for _hub in hubs if _hub['channel_id'] == str(channel.id)), None)

        if hub is None:
            return

        v.db.update_dash(channel.guild, key=f"temporary_channels.hubs.{hubs.index(hub)}.hub_name", value=channel.name)


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