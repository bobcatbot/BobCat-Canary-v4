import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

class AddNewTempChannelHub(DesignerView):
    def __init__(self, guild: discord.Guild, user: discord.User, data: dict = None):
        super().__init__(timeout=None)
        
        if data is None: # If data none then inint
            data = {}
            data['id'] = v.uuid(length=12, strCase='upper/lower/nums')

            def load_default_data():
                data["default"] = True
                data["hub_name"] = "Hub - Join to create"
                data["name"] = "#{index} - {username}'s Channel"
                data["user_limit"] = "4"
                data["bitrate"] = "64"
                data["sync_hub_category"] = False
                data["permissions"] = {
                    "manage_channels": False,
                    "manage_permissions": False,
                    "priority_speaker": False,
                    "move_members": False
                }
                return data
            load_default_data()

        maincontainer = Container(
            color=discord.Color.embed_background(),
        )
        maincontainer.add_text("## Create New Temporary Channel Hub")
        maincontainer.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class MainHubView(DesignerView):
            def __init__(self):
                super().__init__(timeout=None)
                container = Container(
                    color=discord.Color.embed_background(),
                )
                container.add_text("# Main Hub")
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                
                container.add_text("## Hub Name")
                class HubModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Hub Name
                                "Hub Name",
                                discord.ui.InputText(
                                    placeholder="Hub name here...",
                                    value=f"{data['hub_name']}",
                                    style=discord.InputTextStyle.short,
                                    required=False,
                                    max_length=32,
                                ),
                            ),
                            title="Edit Hub Name",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        data['hub_name'] = self.children[0].item.value

                        await interaction.response.send_message(f"Saving Hub Name to {data['hub_name']}", ephemeral=True)
                class EditHubNameButton(ActionRow):
                    @button(
                        label="Edit Hub Name",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(HubModal())
                container.add_item(EditHubNameButton())

                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                container.add_text("## Temporary Channels Name")
                class TemporaryChannelsNameModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Hub Name
                                "Hub Name",
                                discord.ui.InputText(
                                    placeholder="Channel name here...",
                                    value=f"{data['name']}",
                                    style=discord.InputTextStyle.short,
                                    required=False,
                                    max_length=32,
                                ),
                            ),
                            title="Edit Hub Name",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        data['name'] = self.children[0].item.value

                        btn = container.get_item("previewButton")
                        btn.label = f"{data['name']}".format(index="1", username=user.name)
                        await interaction.response.edit_message(view=container.view)

                        await interaction.followup.send(f"Saving Channel Name to {data['name']}", ephemeral=True)
                class EditChannelsNameButton(ActionRow):
                    @button(
                        label="Edit Hub Name",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(TemporaryChannelsNameModal())
                container.add_item(EditChannelsNameButton())

                container.add_text("Preview:")
                class PreviewChannelsNameButton(ActionRow):
                    @button(
                        label=f"{data['name']}".format(index="1", username=user.name),
                        style=discord.ButtonStyle.gray,
                        custom_id="previewButton",
                        disabled=True
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        pass
                container.add_item(PreviewChannelsNameButton())

                self.add_item(container)
                
                class GoToMainSettingsButton(ActionRow):
                    @button(
                        label="Go Back",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=AddNewTempChannelHub(guild, user, data))
                self.add_item(GoToMainSettingsButton())
        class HubSettingsView(DesignerView):
            def __init__(self):
                super().__init__(timeout=None)
                container = Container(
                    color=discord.Color.embed_background(),
                )
                container.add_text("# Main Settings")
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                
                container.add_text("## User limit")
                class UserLimitModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Hub Name
                                "User limit",
                                discord.ui.InputText(
                                    placeholder="0-99",
                                    value=f"{data['user_limit']}",
                                    style=discord.InputTextStyle.short,
                                    max_length=2,
                                ),
                                description="Default user limit for all temporary voice channels. Max limit 0-99"
                            ),
                            title="Edit User limit",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        data['user_limit'] = self.children[0].item.value

                        await interaction.response.send_message(f"Saving user limit to {data['user_limit']}", ephemeral=True)
                class EditUserLimitButton(ActionRow):
                    @button(
                        label="Edit User limit",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(UserLimitModal())
                container.add_item(EditUserLimitButton())

                container.add_text("## Bitrate")
                class BitrateModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Hub Name
                                "User limit",
                                discord.ui.InputText(
                                    placeholder="0-96000",
                                    value=f"{data['bitrate']}",
                                    style=discord.InputTextStyle.short,
                                    max_length=2,
                                ),
                                description="Default user limit for all temporary voice channels. Max limit 0-96000"
                            ),
                            title="Edit Temp Channel Bitrate",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        data['bitrate'] = self.children[0].item.value
                        await interaction.response.send_message(f"Saving bitrate to {data['bitrate']}", ephemeral=True)
                class EditBitrateButton(ActionRow):
                    @button(
                        label="Edit Bitrate",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(BitrateModal())
                container.add_item(EditBitrateButton())

                self.add_item(container)
                
                class GoToMainSettingsButton(ActionRow):
                    @button(
                        label="Go Back",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=AddNewTempChannelHub(guild, user, data))
                self.add_item(GoToMainSettingsButton())
        class HubPermissionsView(DesignerView):
            def __init__(self):
                super().__init__(timeout=None)
                container = Container(
                    color=discord.Color.embed_background(),
                )
                container.add_text("# Permissions")
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                container.add_text("## Synchronize permissions with Hub category")
                container.add_text("Synchronize the permissions of the temporary channels when they are created with the permissions of the Hub category.")
                
                class SynchronizePermissionsButton(ActionRow):
                    @button(
                        label="Disabled",
                        style=discord.ButtonStyle.red,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            data["sync_hub_category"] = True

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green

                            syncPermsSelect = container.get_item("SyncPermsSelect")
                            syncPermsSelect.disabled = False
                        else:
                            data["sync_hub_category"] = False

                            syncPermsSelect = container.get_item("SyncPermsSelect")
                            syncPermsSelect.disabled = True

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(SynchronizePermissionsButton())

                class SynchronizePermissionsSelect(ActionRow):
                    @channel_select(
                        placeholder="Select a hub feature",
                        channel_types=[discord.ChannelType.category],
                        custom_id="SyncPermsSelect",
                        disabled=True
                    )
                    async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                        pass
                container.add_item(SynchronizePermissionsSelect())
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                container.add_text("## Owner Permissions")

                container.add_text("### Manage Channels")
                container.add_text("The user that triggered the temporary channels creation can rename them on Discord and change the temporary voice channel user limit.")
                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled",
                        style=discord.ButtonStyle.red,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            data["permissions"]["manage_channels"] = True

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            data["permissions"]["manage_channels"] = False

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())
                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

                container.add_text("### Manage Permissions")
                container.add_text("The user that triggered the temporary channels creation can rename them on Discord and change the temporary voice channel user limit.")
                if guild.me.guild_permissions.administrator == False:
                    container.add_text("**Your bot must have the 'Administrator' permission in order to set the 'Manage Permissions' permission on a channel**")

                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled",
                        style=discord.ButtonStyle.red,
                        disabled=True if guild.me.guild_permissions.administrator == False else False
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            data["permissions"]["manage_permissions"] = True

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            data["permissions"]["manage_permissions"] = False

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())
                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

                container.add_text("### Priority Speaker")
                container.add_text("The user that triggered the temporary channels creation can rename them on Discord and change the temporary voice channel user limit.")
                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled",
                        style=discord.ButtonStyle.red,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            data["permissions"]["priority_speaker"] = True

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            data["permissions"]["priority_speaker"] = False

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())

                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
                container.add_text("### Move Members")
                container.add_text("The user that triggered the temporary channels creation can move other users from the temporary voice channel on Discord.")
                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled",
                        style=discord.ButtonStyle.red,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            data["permissions"]["move_members"] = True

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            data["permissions"]["move_members"] = False

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())
                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
                
                self.add_item(container)
                
                class GoToMainSettingsButton(ActionRow):
                    @button(
                        label="Go Back",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=AddNewTempChannelHub(guild, user, data))
                self.add_item(GoToMainSettingsButton())

        class NewHubSelect(ActionRow):
            @select(
                placeholder="Select a hub feature",
                options=[
                    discord.SelectOption(label="Hub"),
                    discord.SelectOption(label="Settings"),
                    discord.SelectOption(label="Permissions"),
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                if select.values[0] == "Hub":
                    return await interaction.response.edit_message(view=MainHubView())
                if select.values[0] == "Settings":
                    return await interaction.response.edit_message(view=HubSettingsView())
                if select.values[0] == "Permissions":
                    return await interaction.response.edit_message(view=HubPermissionsView())
        maincontainer.add_item(NewHubSelect())
        
        self.add_item(maincontainer)

        class SaveNewHubButton(ActionRow):
            @button(
                label="Create",
                style=discord.ButtonStyle.success,
            )
            async def OnCreate(self, button: discord.ui.Button, interaction: discord.Interaction):
                if data['sync_hub_category'] == True:
                    if data['category_id'] == '':
                        # create category
                        category = await guild.create_category_channel(data['hub_name'], reason=f"Temporary category for hub {data['id']}")
                        data['category_id'] = category.id
                    else:
                        category = await guild.fetch_channel(data['category_id'])
                        data['category_id'] = category.id
                else:
                    category = guild
                
                vc = await category.create_voice_channel(data['hub_name'], reason=f"Temporary voice channel for hub {data['id']}")
                data['channel_id'] = vc.id
                
                was_default = data.pop('default') # remove key 'default' before saving to the database

                # Save the data
                idx = len(v.db.get_dash(guild.id)['temporary_channels']['hubs'])
                v.db.update_dash(guild, f'temporary_channels.hubs.{idx}', data)

                await interaction.response.send_message((
                    f"Successfully created hub {data['id']}"
                    "\n\n**Please be aware that you created a new hub with default settings. You can change them in the hub settings menu.**" if was_default == True else ""
                ), ephemeral=True)
        self.add_item(SaveNewHubButton())

class EditTempChannelHub(DesignerView):
    def __init__(self, guild: discord.Guild, user: discord.User, idx: int):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild)['temporary_channels']['hubs'][idx]
        
        maincontainer = Container(
            color=discord.Color.embed_background(),
        )
        maincontainer.add_text(f"## {data['hub_name']} ({data['id']})")
        maincontainer.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class MainHubView(DesignerView):
            def __init__(self):
                super().__init__(timeout=None)
                container = Container(
                    color=discord.Color.embed_background(),
                )
                container.add_text("# Main Hub")
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                
                container.add_text("## Hub Name")
                class HubModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Hub Name
                                "Hub Name",
                                discord.ui.InputText(
                                    placeholder="Hub name here...",
                                    value=f"{data['hub_name']}",
                                    style=discord.InputTextStyle.short,
                                    required=False,
                                    max_length=32,
                                ),
                            ),
                            title="Edit Hub Name",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        hubName = self.children[0].item.value

                        v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.hub_name', hubName)
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())                       

                        await interaction.response.send_message(f"Saving Hub Name to {hubName}", ephemeral=True)
                class EditHubNameButton(ActionRow):
                    @button(
                        label="Edit Hub Name",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(HubModal())
                container.add_item(EditHubNameButton())

                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                container.add_text("## Temporary Channels Name")
                class TemporaryChannelsNameModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Channel Name
                                "Channel Name",
                                discord.ui.InputText(
                                    placeholder="Channel name here...",
                                    value=f"{data['name']}",
                                    style=discord.InputTextStyle.short,
                                    required=False,
                                    max_length=32,
                                ),
                            ),
                            title="Edit Channel Name",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        channelName = self.children[0].item.value

                        btn = container.get_item("previewButton")
                        btn.label = f"{channelName}".format(index="1", username=user.name)
                        await interaction.response.edit_message(view=container.view)

                        v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.name', channelName)
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                        await interaction.followup.send(f"Saving Channel Name to {channelName}", ephemeral=True)
                class EditChannelNameButton(ActionRow):
                    @button(
                        label="Edit Channel Name",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(TemporaryChannelsNameModal())
                container.add_item(EditChannelNameButton())

                container.add_text("Preview:")
                class PreviewChannelNameButton(ActionRow):
                    @button(
                        label=f"{data['name']}".format(index="1", username=user.name),
                        style=discord.ButtonStyle.gray,
                        custom_id="previewButton",
                        disabled=True
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        pass
                container.add_item(PreviewChannelNameButton())

                self.add_item(container)

                class GoToMainSettingsButton(ActionRow):
                    @button(
                        label="Go Back",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=EditTempChannelHub(guild, user, idx))
                self.add_item(GoToMainSettingsButton())
        class HubSettingsView(DesignerView):
            def __init__(self):
                super().__init__(timeout=None)
                container = Container(
                    color=discord.Color.embed_background(),
                )
                container.add_text("# Main Settings")
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                
                container.add_text("## User limit")
                class UserLimitModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Hub Name
                                "User limit",
                                discord.ui.InputText(
                                    placeholder="0-99",
                                    value=f"{data['user_limit']}",
                                    style=discord.InputTextStyle.short,
                                    max_length=2,
                                ),
                                description="Default user limit for all temporary voice channels. 0-99 (0 = unlimited)"
                            ),
                            title="Edit User limit",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        userLimit = self.children[0].item.value

                        v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.user_limit', userLimit) # save data
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow()) # update updated_at

                        await interaction.response.send_message(f"Saving user limit to {userLimit}", ephemeral=True)
                class EditUserLimitButton(ActionRow):
                    @button(
                        label="Edit User limit",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(UserLimitModal())
                container.add_item(EditUserLimitButton())

                container.add_text("## Bitrate")
                container.add_text("ALL THE BITS! Going above 64 kbps may adversely affect people on poor connections.")
                BitrateSelectOptions = [
                    discord.SelectOption(label="8 kbps", value="8"),
                    discord.SelectOption(label="16 kbps", value="16"),
                    discord.SelectOption(label="32 kbps", value="32"),
                    discord.SelectOption(label="64 kbps", value="64"),
                    discord.SelectOption(label="96 kbps", value="96"),
                ]
                if guild.premium_tier >= 1:
                    BitrateSelectOptions.append(discord.SelectOption(label="128 kbps", value="128"))
                if guild.premium_tier >= 2:
                    BitrateSelectOptions.append(discord.SelectOption(label="128 kbps", value="128"))
                    BitrateSelectOptions.append(discord.SelectOption(label="256 kbps", value="256"))
                if guild.premium_tier >= 3:
                    BitrateSelectOptions.append(discord.SelectOption(label="128 kbps", value="128"))
                    BitrateSelectOptions.append(discord.SelectOption(label="256 kbps", value="256"))
                    BitrateSelectOptions.append(discord.SelectOption(label="384 kbps", value="384"))
                class BitrateSelect(ActionRow):
                    @select(
                        placeholder="Select bitrate",
                        options=BitrateSelectOptions,
                    )
                    async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                        bitrate = select.values[0]

                        v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.bitrate', bitrate) # save data
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow()) # update updated_at

                        await interaction.response.send_message(f"Saving bitrate to {bitrate} kbps", ephemeral=True)
                container.add_item(BitrateSelect())

                self.add_item(container)
                
                class GoToMainSettingsButton(ActionRow):
                    @button(
                        label="Go Back",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=EditTempChannelHub(guild, user, idx))
                self.add_item(GoToMainSettingsButton())
        class HubPermissionsView(DesignerView):
            def __init__(self):
                super().__init__(timeout=None)
                container = Container(
                    color=discord.Color.embed_background(),
                )
                container.add_text("# Permissions")
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                container.add_text("## Synchronize permissions with Hub category")
                container.add_text("Synchronize the permissions of the temporary channels when they are created with the permissions of the Hub category.")
                
                class SynchronizePermissionsButton(ActionRow):
                    @button(
                        label="Disabled" if data['sync_hub_category'] == False else "Enabled",
                        style=discord.ButtonStyle.red if data['sync_hub_category'] == False else discord.ButtonStyle.green,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green

                            syncPermsSelect = container.get_item("SyncPermsSelect")
                            syncPermsSelect.disabled = False
                        else:
                            syncPermsSelect = container.get_item("SyncPermsSelect")
                            syncPermsSelect.disabled = True

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(SynchronizePermissionsButton())

                class SynchronizePermissionsSelect(ActionRow):
                    @channel_select(
                        placeholder="Select a hub feature",
                        channel_types=[discord.ChannelType.category],
                        custom_id="SyncPermsSelect",
                        disabled=True if data['sync_hub_category'] == False else False,
                        default_values=[ discord.utils.get(guild.categories, id=data['category_id']) ] if data['category_id'] != '' else None,
                    )
                    async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                        category = select.values[0]
                        print(category)
                container.add_item(SynchronizePermissionsSelect())
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                container.add_text("## Owner Permissions")

                container.add_text("### Manage Channels")
                container.add_text("The user that triggered the temporary channels creation can rename them on Discord and change the temporary voice channel user limit.")
                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled" if data['permissions']['manage_channels'] == False else "Enabled",
                        style=discord.ButtonStyle.red if data['permissions']['manage_channels'] == False else discord.ButtonStyle.green,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.manage_channels', True)

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.manage_channels', False)

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())
                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

                container.add_text("### Manage Permissions")
                container.add_text("The user that triggered the temporary channels creation can rename them on Discord and change the temporary voice channel user limit.")
                if guild.me.guild_permissions.administrator == False:
                    container.add_text("**Your bot must have the 'Administrator' permission in order to set the 'Manage Permissions' permission on a channel**")

                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled" if data['permissions']['manage_permissions'] == False else "Enabled",
                        style=discord.ButtonStyle.red if data['permissions']['manage_permissions'] == False else discord.ButtonStyle.green,
                        disabled=True if guild.me.guild_permissions.administrator == False else False
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.manage_permissions', True)

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.success
                        else:
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.manage_permissions', False)

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())
                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

                container.add_text("### Priority Speaker")
                container.add_text("The user that triggered the temporary channels creation can rename them on Discord and change the temporary voice channel user limit.")
                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled" if data['permissions']['priority_speaker'] == False else "Enabled",
                        style=discord.ButtonStyle.red if data['permissions']['priority_speaker'] == False else discord.ButtonStyle.green,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.priority_speaker', True)

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.priority_speaker', False)

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())

                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
                container.add_text("### Move Members")
                container.add_text("The user that triggered the temporary channels creation can move other users from the temporary voice channel on Discord.")
                class ManageChannelsPermissionsButton(ActionRow):
                    @button(
                        label="Disabled" if data['permissions']['move_members'] == False else "Enabled",
                        style=discord.ButtonStyle.red if data['permissions']['move_members'] == False else discord.ButtonStyle.green,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        if button.label == "Disabled":
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.move_members', True)

                            button.label = "Enabled"
                            button.style = discord.ButtonStyle.green
                        else:
                            v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.permissions.move_members', False)

                            button.label = "Disabled"
                            button.style = discord.ButtonStyle.red
                        
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                        await interaction.response.edit_message(view=interaction.view)
                container.add_item(ManageChannelsPermissionsButton())
                container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
                
                self.add_item(container)
                
                class GoToMainSettingsButton(ActionRow):
                    @button(
                        label="Go Back",
                        style=discord.ButtonStyle.primary,
                    )
                    async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=EditTempChannelHub(guild, user, idx))
                self.add_item(GoToMainSettingsButton())

        class NewHubSelect(ActionRow):
            @select(
                placeholder="Select a hub feature",
                options=[
                    discord.SelectOption(label="Hub"),
                    discord.SelectOption(label="Settings"),
                    discord.SelectOption(label="Permissions"),
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                if select.values[0] == "Hub":
                    return await interaction.response.edit_message(view=MainHubView())
                if select.values[0] == "Settings":
                    return await interaction.response.edit_message(view=HubSettingsView())
                if select.values[0] == "Permissions":
                    return await interaction.response.edit_message(view=HubPermissionsView())
        maincontainer.add_item(NewHubSelect())
        
        self.add_item(maincontainer)

        class DeleteHubButton(ActionRow):
            @button(
                label="Delete Hub",
                style=discord.ButtonStyle.danger,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                class ConfirmDeleteHubView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=None)

                    @discord.ui.button(
                        label="Delete",
                        style=discord.ButtonStyle.danger,
                    )
                    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                        # delete category and all channels in it if sync_hub_category is enabled
                        if data['sync_hub_category'] == True and data['category_id'] != '':
                            category = discord.utils.get(guild.categories, id=data['category_id'])
                            if category:
                                await category.delete(reason=f"Hub {data['id']} deleted")

                        # delete the temporary voice channel if sync_hub_category is disabled or if there is no category
                        elif data['channel_id'] != '':
                            channel = discord.utils.get(guild.voice_channels, id=data['channel_id'])
                            if channel:
                                await channel.delete(reason=f"Hub {data['id']} deleted")

                        # remove hub from database
                        tcs = v.db.get_dash(guild.id)['temporary_channels']
                        tcs['hubs'].pop(idx)

                        v.db.update_dash(guild, key=f'temporary_channels.hubs', value=tcs['hubs'])
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                        await interaction.response.send_message(f"Hub {data['id']} has been deleted", ephemeral=True)

                    @discord.ui.button(
                        label="Cancel",
                        style=discord.ButtonStyle.secondary,
                    )
                    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True
                        
                        await interaction.response.edit_message(content="Canceled", view=self)

                await interaction.response.send_message("### Are you sure you want to delete this hub? This action cannot be undone.", view=ConfirmDeleteHubView(), ephemeral=True)
        self.add_item(DeleteHubButton())

        class GoBackToMainButton(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def GoBack(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginTempChannels(guild))
            
            @button(
                label="Updated at: " + datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime("%d-%m-%Y %H:%M"),
                style=discord.ButtonStyle.gray,
                disabled=True
            )
            async def UpdateButton(self, b, i):
                pass
        self.add_item(GoBackToMainButton())

class PluginTempChannels(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['temporary_channels']

        container = Container(
            color=discord.Color.embed_background(),
        )
        container.add_text("# Temporary Channels")
        container.add_text("Allow your members to create temporary voice channels in one click in your server")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild.id, 'temporary_channels.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild.id, 'temporary_channels.status', True)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild.id, 'temporary_channels.status', True)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CreateTempChannelButton(ActionRow):
            @button(
                label="New Hub",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_message(view=AddNewTempChannelHub(guild=guild, user=interaction.user), ephemeral=True)
        container.add_item(CreateTempChannelButton())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
        container.add_text("## Your Hubs")
        class SelectTempChans(ActionRow):
            @select(
                placeholder="Select a hub",
                options=[
                    discord.SelectOption(label=f"{option['hub_name']}",) 
                    for option in data["hubs"]
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                hub_idx = None
                for idx, option in enumerate(data["hubs"]):
                    if option['hub_name'] == select.values[0]:
                        hub_idx = idx
                        break

                await interaction.response.edit_message(view=EditTempChannelHub(guild=guild, user=interaction.user, idx=hub_idx))
        container.add_item(SelectTempChans())

        # Main container for the view
        self.add_item(container)
