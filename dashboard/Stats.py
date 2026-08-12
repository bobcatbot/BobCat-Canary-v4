import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, channel_select
from dashboard._components import FooterRow, StatusToggle, save_dash, refresh_footer


class StatsCountersContainer(DesignerView):
    """View for managing stats counters."""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.stats
        
        container = Container(color=v.style(guild))
        container.add_text("# Stats Counters")
        container.add_text("Configure which statistics to track.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        counters = data.get('counters', [])
        
        # Add Counter Button
        class AddCounterButton(ActionRow):
            @button(
                label="Add Counter",
                style=discord.ButtonStyle.primary,
                emoji="➕"
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                class AddCounterModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label(
                                "Counter Type",
                                discord.ui.Select(
                                    options=[
                                        discord.SelectOption(label="Total Members", value="totalMembers"),
                                        discord.SelectOption(label="Online Members", value="onlineCount"),
                                        discord.SelectOption(label="Bots", value="botCount"),
                                        discord.SelectOption(label="Humans", value="humanCount"),
                                        discord.SelectOption(label="Total Channels", value="totalChannels"),
                                        discord.SelectOption(label="Text Channels", value="textCount"),
                                        discord.SelectOption(label="Voice Channels", value="voiceCount"),
                                        discord.SelectOption(label="Roles", value="roleCount"),
                                    ],
                                    placeholder="Select a statistic"
                                )
                            ),
                            discord.ui.Label(
                                "Text Template",
                                discord.ui.InputText(
                                    placeholder="👥 Members: {count}",
                                    value="👥 Members: {count}",
                                    max_length=90
                                )
                            ),
                            title="Add Stats Counter"
                        )
                        
                    async def callback(self, interaction: discord.Interaction):
                        target = self.children[0].item.values[0]
                        template = self.children[1].item.value
                        
                        new_counter = {
                            "target": target,
                            "channel_id": "",
                            "text": template,
                            "count": 0
                        }
                        
                        current_counters = Guild.get(str(guild.id)).run().dashboard.stats.get('counters', [])
                        current_counters.append(new_counter)
                        
                        save_dash(guild, 'stats.counters', current_counters)
                        refresh_footer(interaction.view, guild)
                        
                        await interaction.response.edit_message(
                            view=StatsCountersContainer(guild)
                        )
                        await interaction.followup.send(
                            f"✅ Added counter for {target}",
                            ephemeral=True
                        )
                        
                await interaction.response.send_modal(AddCounterModal())
                
        container.add_item(AddCounterButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        # Display existing counters
        if not counters:
            container.add_text("*No counters configured. Add one above!*")
        else:
            for idx, counter in enumerate(counters):
                target = counter.get('target', 'Unknown')
                template = counter.get('text', '{count}')
                channel_id = counter.get('channel_id')
                count = counter.get('count', 0)
                
                # Get channel mention if it exists
                channel_mention = "Not set"
                if channel_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        channel_mention = channel.mention
                    else:
                        channel_mention = f"Channel {channel_id} (deleted)"
                
                container.add_text(f"**{target}**")
                container.add_text(f"Template: `{template}`")
                container.add_text(f"Channel: {channel_mention}")
                container.add_text(f"Current count: {count}")
                
                # Delete button for this counter
                class DeleteCounterButton(ActionRow):
                    @button(
                        label="Remove",
                        style=discord.ButtonStyle.danger,
                        custom_id=f"delete_counter_{idx}"
                    )
                    async def delete_callback(self, btn: discord.ui.Button, inter: discord.Interaction):
                        current_counters = Guild.get(str(guild.id)).run().dashboard.stats.get('counters', [])
                        
                        # Try to delete the channel if it exists
                        channel_id = current_counters[idx].get('channel_id')
                        if channel_id:
                            channel = guild.get_channel(int(channel_id))
                            if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                                try:
                                    await channel.delete(reason="Counter removed")
                                except:
                                    pass
                        
                        # Remove the counter
                        current_counters.pop(idx)
                        save_dash(guild, 'stats.counters', current_counters)
                        refresh_footer(inter.view, guild)
                        
                        await inter.response.edit_message(
                            view=StatsCountersContainer(guild)
                        )
                        await inter.followup.send(
                            "✅ Counter removed",
                            ephemeral=True
                        )
                        
                container.add_item(DeleteCounterButton())
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginStats(guild)))


class StatsChannelPicker(DesignerView):
    """View for selecting which channel to use for a specific counter."""
    
    def __init__(self, guild: discord.Guild, target: str, idx: int):
        super().__init__(timeout=None)
        self.target = target
        self.idx = idx
        
        container = Container(color=v.style(guild))
        container.add_text(f"# Set Channel for {target}")
        container.add_text(f"Select the voice channel to display the {target} statistic.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        class ChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a voice channel",
                channel_types=[discord.ChannelType.voice],
                min_values=0,
                max_values=1,
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                new_channel = str(select.values[0].id) if select.values else None
                
                # Get current counters
                current_counters = Guild.get(str(guild.id)).run().dashboard.stats.get('counters', [])
                
                # Update the specific counter
                if 0 <= idx < len(current_counters):
                    current_counters[idx]['channel_id'] = new_channel
                    save_dash(guild, 'stats.counters', current_counters)
                    refresh_footer(interaction.view, guild)
                
                await interaction.response.edit_message(
                    view=StatsCountersContainer(guild)
                )
                await interaction.followup.send(
                    f"✅ Channel set for {target}",
                    ephemeral=True
                )
                
        container.add_item(ChannelSelect())
        
        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: StatsCountersContainer(guild)))


class PluginStats(DesignerView):
    """Main Stats plugin dashboard view."""
    
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.stats
        
        container = Container(color=v.style(guild))
        container.add_text("# Server Statistics")
        container.add_text("Track server statistics in real-time using voice channels.")
        container.add_text("-# Stats channels are voice channels that update automatically with server data.")
        
        # Status toggle
        container.add_item(StatusToggle(guild, 'stats.status', data.get('status', False)))
        
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        # Plugin buttons
        class PluginButtons(ActionRow):
            @button(
                label="Manage Counters",
                style=discord.ButtonStyle.gray
            )
            async def counters_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=StatsCountersContainer(guild))
                
            @button(
                label="Auto-Setup",
                style=discord.ButtonStyle.success
            )
            async def setup_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                """Auto-create default stats channels."""
                await interaction.response.defer(ephemeral=True)
                
                # Check if channels already exist
                counters = Guild.get(str(guild.id)).run().dashboard.stats.get('counters', [])
                existing = [c for c in counters if c.get('channel_id')]
                
                if existing:
                    return await interaction.followup.send(
                        "⚠️ Stats channels already exist. Use the counters manager to modify them.",
                        ephemeral=True
                    )
                
                # Create default counters
                default_counters = [
                    {"target": "totalMembers", "text": "👥 Members: {count}", "channel_id": "", "count": 0},
                    {"target": "onlineCount", "text": "🟢 Online: {count}", "channel_id": "", "count": 0},
                    {"target": "totalChannels", "text": "📋 Channels: {count}", "channel_id": "", "count": 0},
                    {"target": "botCount", "text": "🤖 Bots: {count}", "channel_id": "", "count": 0},
                ]
                
                try:
                    # Create voice channels
                    for counter in default_counters:
                        channel = await guild.create_voice_channel(
                            name=counter["text"].format(count=0),
                            reason="Stats auto-setup"
                        )
                        counter["channel_id"] = str(channel.id)
                    
                    # Save to config
                    save_dash(guild, 'stats.counters', default_counters)
                    save_dash(guild, 'stats.status', True)
                    
                    await interaction.followup.send(
                        f"✅ Created {len(default_counters)} stats channels!",
                        ephemeral=True
                    )
                    
                    # Refresh the view
                    await interaction.response.edit_message(view=PluginStats(guild))
                    
                except discord.Forbidden:
                    await interaction.followup.send(
                        "❌ I don't have permission to create voice channels.",
                        ephemeral=True
                    )
                except Exception as e:
                    await interaction.followup.send(
                        f"❌ Failed to create stats channels: {str(e)}",
                        ephemeral=True
                    )
                    
        container.add_item(PluginButtons())
        
        # Show current stats summary
        counters = data.get('counters', [])
        if counters:
            container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
            container.add_text("## Current Statistics")
            
            for counter in counters:
                target = counter.get('target', 'Unknown')
                count = counter.get('count', 0)
                channel_id = counter.get('channel_id')
                status = "✅" if channel_id else "⚠️ No channel set"
                
                container.add_text(f"**{target}**: {count} — {status}")
        
        self.add_item(container)