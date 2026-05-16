import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

class WelcomeWelcomeContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild)['welcome']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Welcome")
        container.add_text("Automatically send messages and give roles to your new members")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # Welcome
        container.add_text("### Send a message when a user joins the server")
        class WelcomeToggle(ActionRow):
            @button(
                label="Disabled" if data['join']['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['join']['status'] == False else discord.ButtonStyle.green,
                custom_id="welcome_toggle",
            )
            async def status(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'welcome.join.status', True)
                    v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'welcome.join.status', False)
                    v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red
                await interaction.response.edit_message(view=container.view)
        container.add_item(WelcomeToggle())
        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small) # Invisible separator to add space

        container.add_text("### Welcome message channel")
        class WelcomeChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                default_values=[ guild.get_channel(int(data['join']['channel'])) ],
            )
            async def callback(self, select, interaction: discord.Interaction):
                v.db.update_dash(guild, 'welcome.join.channel', select.values[0].id)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_btn = interaction.view.get_item("SaveSuccess")
                update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(WelcomeChannelSelect())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small) # Invisible separator to add space

        container.add_text("### Welcome message")
        class WelcomeMessageModal(ActionRow):
            @button(
                label="Add message",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                update_btn = interaction.view.get_item("SaveSuccess")

                class WelcomeModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label(
                                "Message",
                                discord.ui.InputText(
                                    style=discord.InputTextStyle.short,
                                    value=data['join']['message']['content'],
                                ),
                            ),
                            title="Welcome DM Message",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        v.db.update_dash(guild, 'welcome.join.message.content', self.children[0].item.value)
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                        update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                        await interaction.response.edit_message(view=container.view)
                await interaction.response.send_modal(WelcomeModal())
        container.add_item(WelcomeMessageModal())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large) # Invisible separator to add space

        # Welcome DM
        container.add_text("### Send a private message to new users")
        class WelcomeDMToggle(ActionRow):
            @button(
                label="Disabled" if data['dm']['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['dm']['status'] == False else discord.ButtonStyle.green,
                custom_id="welcome_dm_toggle",
            )
            async def status(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'welcome.dm.status', True)
                    v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'welcome.dm.status', False)
                    v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red
                await interaction.response.edit_message(view=container.view)
        container.add_item(WelcomeDMToggle())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small) # Invisible separator to add space

        container.add_text("### Message")
        class WelcomeDMMessageModal(ActionRow):
            @button(label="Edit message", style=discord.ButtonStyle.primary)
            async def callback(self, btn, interaction: discord.Interaction):
                class WelcomeDMModal(discord.ui.Modal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.InputText(
                                label="Message",
                                style=discord.InputTextStyle.short,
                                value=data['dm']['message']['content'],
                            ),
                            title="Welcome DM Message",
                        )
                    async def on_submit(self, interaction: discord.Interaction):
                        v.db.update_dash(guild, 'welcome.dm.message.content', self.children[0].value)
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                        update_btn = interaction.view.get_item("SaveSuccess")
                        update_btn.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                        await interaction.response.edit_message(view=container.view)
                await interaction.response.send_modal(WelcomeDMModal())
        container.add_item(WelcomeDMMessageModal())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large) # Separator for 

        # Welcome Auto roles
        container.add_text("## Give roles to new users")
        class WelcomeAutoRoleToggle(ActionRow):
            @button(
                label="Disabled" if data['autoRoles']['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['autoRoles']['status'] == False else discord.ButtonStyle.green,
                custom_id="welcome_autoRoles_toggle",
            )
            async def status(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'welcome.autoRoles.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'welcome.autoRoles.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(WelcomeAutoRoleToggle())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

        container.add_text("### Roles to give")
        class WelcomeAutoRoleSelect(ActionRow):
            @role_select(
                placeholder="Select a role",
                max_values=5,
                default_values=[ guild.get_role(int(role_id)) for role_id in data['autoRoles']['roles'] ],
            )
            async def callback(self, select, interaction: discord.Interaction):
                v.db.update_dash(guild, 'welcome.autoRoles.roles', [str(role.id) for role in select.values])
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(WelcomeAutoRoleSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginWelcomeGoodbye(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class WelcomeGoodbyeContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild)['welcome']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Goodbye")
        container.add_text("Automatically send messages and give roles to your new members")
        
        class WelcomeGoodbyeToggle(ActionRow):
            @button(
                label="Disabled" if data['leave']['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['leave']['status'] == False else discord.ButtonStyle.green,
                custom_id="welcome_goodbye_toggle",
            )
            async def status(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'welcome.leave.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'welcome.leave.status', False)


                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(WelcomeGoodbyeToggle())
        
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # Leave Channel
        container.add_text("### Leave message channel")
        class LeaveChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                default_values=[ guild.get_channel(int(data['leave']['channel'])) ],
            )
            async def callback(self, select, interaction: discord.Interaction):
                v.db.update_dash(guild, 'welcome.leave.channel', str(select.values[0].id))
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        container.add_item(LeaveChannelSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        # Leave Message
        container.add_text("### Send a message when a user leaves the server")
        class LeaveMessageModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Message",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.long,
                            value=data['leave']['message']['content'],
                        )
                    ),
                    title="Leave Message",
                )
            async def callback(self, interaction: discord.Interaction):
                v.db.update_dash(guild, 'welcome.leave.message.content', self.children[0].value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        class LeaveMessageButton(ActionRow):
            @button(
                label="Edit message",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(LeaveMessageModal())
        container.add_item(LeaveMessageButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginWelcomeGoodbye(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class PluginWelcomeGoodbye(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild)['welcome']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Welcome & Goodbye")
        container.add_text("Automatically send messages and give roles to your new members and send a message when a members leaves your server")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def status(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'welcome.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'welcome.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        container.add_text("**Configure**")

        class PluginButtons(ActionRow):
            @button(
                label="Welcome",
                style=discord.ButtonStyle.gray,
            )
            async def welcomeBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=WelcomeWelcomeContainer(guild))
            
            @button(
                label="Goodbye",
                style=discord.ButtonStyle.gray,
            )
            async def goodbyeBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=WelcomeGoodbyeContainer(guild))
        
        container.add_item(PluginButtons())
        self.add_item(container)