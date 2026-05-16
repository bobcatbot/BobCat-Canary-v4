import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

BUTTON_STYLES = {
    "gray": discord.ButtonStyle.gray,
    "blurple": discord.ButtonStyle.blurple,
    "green": discord.ButtonStyle.green,
    "red": discord.ButtonStyle.red
}

class VerificationMessage(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['verification']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Verification Message")
        container.add_text("Set the message that will be sent in the verification channel.")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        container.add_text("### Embed Preview")
        container.add_text(f"# {data['message']['embed']['title']}", id=100)
        container.add_text(f"{data['message']['embed']['desc']}", id=101)
        class VerificationButtonPreview(ActionRow):
            @button(
                emoji= f"{data['message']['btn']['emoji']}",
                label= f"{data['message']['btn']['title']}",
                style= BUTTON_STYLES.get(data['message']['btn']['color'], discord.ButtonStyle.gray),
                disabled=True,
                id=102,
            )
            async def callback(s,b,i):
                pass
        container.add_item(VerificationButtonPreview())
        container.add_text("-# Button is disabled because this is just a preview")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class MessageModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Embed Color",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.short,
                            value=data['message']['embed']['color'],
                        )
                    ),
                    discord.ui.Label(
                        "Embed Title",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.short,
                            value=data['message']['embed']['title'],
                        )
                    ),
                    discord.ui.Label(
                        "Embed Description",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.long,
                            value=data['message']['embed']['desc'],
                        )
                    ),
                    title="Verification Embed Message",
                )
            async def callback(self, interaction: discord.Interaction):
                embedColor = self.children[0].item.value
                embedTitle = self.children[1].item.value
                embedDesc = self.children[2].item.value

                container.view.get_item(100).content = f"# {embedTitle}"
                container.view.get_item(101).content = f"{embedDesc}"

                v.db.update_dash(guild, 'verification.message.embed.color', embedColor)
                v.db.update_dash(guild, 'verification.message.embed.title', embedTitle)
                v.db.update_dash(guild, 'verification.message.embed.desc', embedDesc)

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_btn = container.view.get_item("SaveSuccess")
                update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        class MessageButton(ActionRow):
            @button(
                label="Edit message",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(MessageModal())
        container.add_item(MessageButton())
        
        class EditVerifyButtonModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Color",
                        discord.ui.Select(
                            options=[
                                discord.SelectOption(label="Gray", value="gray", default=data['message']['btn']['color'] == "gray"),
                                discord.SelectOption(label="Blurple", value="blurple", default=data['message']['btn']['color'] == "blurple"),
                                discord.SelectOption(label="Green", value="green", default=data['message']['btn']['color'] == "green"),
                                discord.SelectOption(label="Red", value="red", default=data['message']['btn']['color'] == "red"),
                            ],
                            placeholder="Select a color",
                        )
                    ),
                    discord.ui.Label(
                        "Emoji",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.short,
                            value=data['message']['btn']['emoji'],
                            required=False,
                        )
                    ),
                    discord.ui.Label(
                        "Title",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.short,
                            value=data['message']['btn']['title'],
                        )
                    ),
                    title="Verification Button",
                )
            async def callback(self, interaction: discord.Interaction):
                btnColor = self.children[0].item.values[0]
                btnEmoji = self.children[1].item.value
                btnTitle = self.children[2].item.value

                btn = container.view.get_item(102)
                btn.label = btnTitle
                btn.emoji = btnEmoji
                btn.style = BUTTON_STYLES.get(btnColor, discord.ButtonStyle.gray)

                v.db.update_dash(guild, 'verification.message.btn.title', btnTitle)
                v.db.update_dash(guild, 'verification.message.btn.emoji', btnEmoji)
                v.db.update_dash(guild, 'verification.message.btn.color', btnColor)

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_btn = container.view.get_item("SaveSuccess")
                update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        class EditVerifyButton(ActionRow):
            @button(
                label="Edit Verify Button",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(EditVerifyButtonModal())
        container.add_item(EditVerifyButton())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.large)
        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
        
        class VerifyButton(ActionRow):
            @button(
                label="Publish" if not data['message_published'] else "Published",
                style=discord.ButtonStyle.blurple if not data['message_published'] else discord.ButtonStyle.green,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                # Check for the right permissions before everything else
                if guild.me.guild_permissions.manage_channels is False:
                    return await interaction.response.send_message("I don't have permission to send messages in this server! \nPlease give me the 'Manage Channels' permission and try again.", ephemeral=True)
                if guild.me.guild_permissions.manage_roles is False:
                    return await interaction.response.send_message("I don't have permission to assign roles in this server! \nPlease give me the 'Manage Roles' permission and try again.", ephemeral=True)
                
                if data['channel'] is None:
                    return await interaction.response.send_message("Oops! It looks like you haven't set a verification channel first. \nGo to the 'Channel & Role' settings.", ephemeral=True)
                if data['role'] is None:
                    return await interaction.response.send_message("Oops! It looks like you haven't set a verification role first. \nGo to the 'Channel & Role' settings.", ephemeral=True)

                config = v.db.get_dash(guild.id)['verification']

                channel = guild.get_channel(int(config['channel']))
                role = guild.get_role(int(config['role']))
                
                embed = discord.Embed.from_dict({
                    "title": config['message']['embed']['title'],
                    "description": config['message']['embed']['desc'],
                    "color": int(config['message']['embed']['color'].replace("#", ""), 16)
                })

                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label=config['message']['btn']['title'],
                    emoji=config['message']['btn']['emoji'],
                    style=BUTTON_STYLES.get(config['message']['btn']['color'], discord.ButtonStyle.gray),
                    custom_id="Verification",
                ))

                if config['message_published']:
                    msg = await channel.fetch_message(int(config['message_id']))
                    await msg.edit(embed=embed, view=view)
                    return await interaction.response.send_message("Verification message updated!", ephemeral=True)

                await channel.set_permissions(guild.default_role, overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=False))
                await channel.set_permissions(role, overwrite=discord.PermissionOverwrite(read_messages=False, send_messages=False))

                await guild.default_role.edit( # @everyone
                    reason="Verification system enabled",
                    permissions=discord.Permissions(read_messages=False,)
                )

                if role.id == int(config['role']):
                    await role.edit(
                        reason="Verification system enabled",
                        permissions=discord.Permissions(read_messages=True)
                    )

                msg = await channel.send(embed=embed, view=view)
                v.db.update_dash(guild, 'verification.message_id', str(msg.id))
                v.db.update_dash(guild, 'verification.message_published', True)

                button.label = "Published"
                await interaction.followup.edit_message(interaction.message.id, view=interaction.view)
                await interaction.followup.send_message("Verification message sent!", ephemeral=True)

        container.add_item(VerifyButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginVerification(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%d-%m-%Y %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, b, i):
                pass
        self.add_item(ViewButtons())

class VerificationChanRoleOptions(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['verification']

        chan = []
        if data['channel']:
            chan = [ guild.get_channel(int(data['channel'])) ]

        role = []
        if data['role']:
            role = [ guild.get_role(int(data['role'])) ]

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Verification Channel And Role")
        container.add_text("Configure your verification channel and role.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Verification Channel")
        container.add_text("Select the channel where the verification message will be sent.")
        class ChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                min_values=0,
                max_values=1,
                default_values=chan,
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                if len(select.values) > 0:
                    channel = select.values[0]
                    v.db.update_dash(guild, 'verification.channel', str(channel.id))
                else:
                    v.db.update_dash(guild, 'verification.channel', None)
                
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_btn = container.view.get_item("SaveSuccess")
                update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(ChannelSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Verification Role")
        container.add_text("Select the role that will be given to the verified members.")
        class RoleSelect(ActionRow):
            @role_select(
                placeholder="Select a role",
                min_values=0,
                max_values=1,
                default_values=role,
            )
            async def callback(self, select: discord.ui.RoleSelect, interaction: discord.Interaction):
                if len(select.values) > 0:
                    role = select.values[0]
                    v.db.update_dash(guild, 'verification.role', str(role.id))
                else:
                    v.db.update_dash(guild, 'verification.role', None)
                
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_btn = container.view.get_item("SaveSuccess")
                update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(RoleSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginVerification(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, b, i):
                pass
        self.add_item(ViewButtons())

class VerificationGeneralOptions(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['verification']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# General Verification Options")
        container.add_text("Configure general verification options.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Verification Mode")
        container.add_text("What kind of verification method do you want to use?")
        class ModeSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Instant Access", value="instant", default=data['mode'] == "instant"),
                    discord.SelectOption(label="Captcha (DM)", value="captcha_dm", default=data['mode'] == "captcha_dm"),
                    discord.SelectOption(label="Captcha (Channel)", value="captcha_channel", default=data['mode'] == "captcha_channel"),
                ],
                min_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                new_value = select.values[0]
                
                for option in select.options:
                    option.default = option.value == new_value

                v.db.update_dash(guild, 'verification.mode', new_value.lower().replace(" & ", "_"))
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(ModeSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Fail Action")
        container.add_text("What should happen if the verification fails?")
        class FailActionSelect(ActionRow):
            @select(
                options=[
                    discord.SelectOption(label="Keep Unverified", value="unverified", default=data['failAction'] == "unverified"),
                    discord.SelectOption(label="Kick", value="kick", default=data['failAction'] == "kick"),
                    discord.SelectOption(label="Ban", value="ban", default=data['failAction'] == "ban"),
                ],
                placeholder="Select an option",
                min_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                new_value = select.values[0]
                
                for option in select.options:
                    option.default = option.value == new_value

                v.db.update_dash(guild, 'verification.failAction', new_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(FailActionSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginVerification(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, b, i):
                pass
        self.add_item(ViewButtons())

class PluginVerification(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['verification']
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Verification")
        container.add_text("Verification gate that your new members need to pass in order to get access to your server.")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def status(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'verification.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'verification.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class PluginButtons(ActionRow):
            @button(
                label="Message",
                style=discord.ButtonStyle.gray,
            )
            async def messageBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=VerificationMessage(guild))

            @button(
                label="Channel & Role",
                style=discord.ButtonStyle.gray,
            )
            async def channelBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=VerificationChanRoleOptions(guild))

            @button(
                label="Advanced",
                style=discord.ButtonStyle.gray,
            )
            async def advancedBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=VerificationGeneralOptions(guild))

        container.add_item(PluginButtons())
        
        self.add_item(container)
