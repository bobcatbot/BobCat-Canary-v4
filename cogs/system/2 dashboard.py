import patreon
import requests
import discord
from datetime import datetime
from discord.ext import commands
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

CREATOR_ACCESS_TOKEN = "CeMP33TcR7N3uo0yvTSWywBEvG8ilCPSwSucI-6L6ys"
papi_client = patreon.API(CREATOR_ACCESS_TOKEN)

PM_Options = [ { "label": "Server", "desc": "Include the server name" }, { "label": "Action", "desc": "Include the action of what happend" }, {  "label": "Reason", "desc": "Include the reason for the kick" }, { "label": "Moderator", "desc": "Include the moderator who kicked the user" } ]

TIME_OPTIONS = [ { "time": "00:00 - 12am", "value": "0" }, { "time": "01:00 - 1am", "value": "1" }, { "time": "02:00 - 2am", "value": "2" }, { "time": "03:00 - 3am", "value": "3" }, { "time": "04:00 - 4am", "value": "4" }, { "time": "05:00 - 5am", "value": "5" }, { "time": "06:00 - 6am", "value": "6" }, { "time": "07:00 - 7am", "value": "7" }, { "time": "08:00 - 8am", "value": "8" }, { "time": "09:00 - 9am", "value": "9" }, { "time": "10:00 - 10am", "value": "10" }, { "time": "11:00 - 11am", "value": "11" }, { "time": "12:00 - 12pm", "value": "12" }, { "time": "13:00 - 1pm", "value": "13" }, { "time": "14:00 - 2pm", "value": "14" }, { "time": "15:00 - 3pm", "value": "15" }, { "time": "16:00 - 4pm", "value": "16" }, { "time": "17:00 - 5pm", "value": "17" }, { "time": "18:00 - 6pm", "value": "18" }, { "time": "19:00 - 7pm", "value": "19" }, { "time": "20:00 - 8pm", "value": "20" }, { "time": "21:00 - 9pm", "value": "21" }, { "time": "22:00 - 10pm", "value": "22" }, { "time": "23:00 - 11pm", "value": "23" } ]

BUTTON_STYLES = {
    "gray": discord.ButtonStyle.gray,
    "blurple": discord.ButtonStyle.blurple,
    "green": discord.ButtonStyle.green,
    "red": discord.ButtonStyle.red
}

# Bot Settings
class BotSettingsMastersAndAdmins(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_server_config(guild.id, True)['settings']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Bot Masters & Admins")
        container.add_text("Here you can adjust the bots settings")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("Administrator Roles")
        container.add_text("Any role with the Administrator permission is considered as a bot master.")
        class AdminsSelect(ActionRow):
            @role_select(
                placeholder="Select roles",
                max_values=len(guild.roles),
                default_values=[ 
                    guild.get_role(int(role))
                    for role in data['admin_roles']
                ],
            )
            async def select(self, select: discord.ui.RoleSelect, interaction: discord.Interaction):
                print(select.values)
                # v.db.update_server_config(guild, True, 'settings.admins', select.values)
                # v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                # update_at = interaction.view.get_item("SaveSuccess")
                # update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(AdminsSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("Additional Bot Master Roles")
        container.add_text("Roles that will also be considered as bot masters, even if they do not have the Administrator permission.")
        class MastersSelect(ActionRow):
            @role_select(
                placeholder="Select roles",
                max_values=len(guild.roles),
                default_values=[ 
                    guild.get_role(int(role))
                    for role in data['bot_masters']
                ],
            )
            async def select(self, select: discord.ui.RoleSelect, interaction: discord.Interaction):
                print(select.values)
                # v.db.update_server_config(guild, True, 'settings.masters', select.values)
                # v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                # update_at = interaction.view.get_item("SaveSuccess")
                # update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MastersSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginBotSettings(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class BotSettingsColor(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_server_config(guild.id, True)['settings']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Color")
        container.add_text("The color for the bot")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ColorModal(discord.ui.DesignerModal):
            def __init__(self, guild: discord.Guild):
                super().__init__(
                    discord.ui.Label(
                        "Color",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.short,
                            value=data['color'],
                        )
                    ),
                    title="Color",
                )

            async def callback(self, interaction: discord.Interaction):
                color = self.children[0].value
                v.db.update_server_config(self.guild, True, 'settings.color', color)
                v.db.update_server_config(self.guild, True, 'updated_at', discord.utils.utcnow())
        
        class ColorButton(ActionRow):
            @button(
                label="Change Color",
                style=discord.ButtonStyle.primary,
            )
            async def changeColor(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(ColorModal(guild))
        container.add_item(ColorButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginBotSettings(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class BotSettingsOptions(DesignerView):  # TODO: finish 
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        from dashboard.consts import langs, tz as timezones
        data = v.db.get_server_config(guild.id, True)['settings']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Other options")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Langauge")
        container.add_text("Change the default language of the bot in your server.")
        container.add_text("This feature is a working in progress")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Timezone")
        container.add_text("Change the default timezone of the bot in your server.")
        container.add_text("This feature is a working in progress")

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginBotSettings(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class PluginBotSettings(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Settings")
        container.add_text("Here you can adjust the bots settings")

        class SettingsSelect(ActionRow):
            @select(
                placeholder="Select a setting",
                options=[
                    discord.SelectOption(label="Bot Masters", description="Bot masters can modify all Dashboard settings."),
                    discord.SelectOption(label="Color", description="The color for the bot"),
                    discord.SelectOption(label="Other Options", description="")
                ],
            )
            async def select(self, select: discord.ui.Select, interaction: discord.Interaction):
                if select.values[0] == "Bot Masters":
                    await interaction.response.edit_message(view=BotSettingsMastersAndAdmins(guild))
                if select.values[0] == "Color":
                    await interaction.response.edit_message(view=BotSettingsColor(guild))
                if select.values[0] == "Other Options":
                    await interaction.response.edit_message(view=BotSettingsOptions(guild))
        container.add_item(SettingsSelect())
        self.add_item(container)

# Welcome & Goodbye
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
        container.add_text("## Send a message when a user joins the server")
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
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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

        container.add_text("## Welcome message")
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

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # Welcome DM
        container.add_text("## Send a private message to new users")
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
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Message")
        class WelcomeDMMessageModal(ActionRow):
            @button( label="Edit message", style=discord.ButtonStyle.primary )
            async def callback(self, button, interaction: discord.Interaction):
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

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginWelcome(guild))

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
        container.add_text("## Leave message channel")
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
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginWelcome(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class PluginWelcome(DesignerView):
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

        class WelcomeSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Welcome"),
                    discord.SelectOption(label="Goodbye"),
                ],
                min_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                if select.values[0] == "Welcome":
                    await interaction.response.edit_message(view=WelcomeWelcomeContainer(guild))
                if select.values[0] == "Goodbye":
                    await interaction.response.edit_message(view=WelcomeGoodbyeContainer(guild))
        container.add_item(WelcomeSelect())
        
        self.add_item(container)

# Moderation
class ModeratorKickContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['moderation']['settings']['kick']
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Kick Settings")
        container.add_text("All the settings for kicking")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Privete Message")
        container.add_text("Send a private message to the user when they are kicked")
        class KickMessageSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(
                        label=option['label'], 
                        description=option['desc'],
                        default=option['label'].lower() in data['dm'],
                    ) 
                    for option in PM_Options
                ],
                min_values=1,
                max_values=len(PM_Options),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [option.lower() for option in select.values]

                v.db.update_dash(guild, 'moderation.settings.kick.dm', new_values)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                for option in select.options:
                    option.default = option.label.lower() in new_values

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(KickMessageSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginModerator(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, btn, itr):
                pass
        self.add_item(ViewButtons())
class ModeratorBanContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['moderation']['settings']['ban']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Ban Settings")
        container.add_text("All the settings for banning")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Private Message")
        container.add_text("Send a private message to the user when they are banned")
        class BanMessageSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(
                        label=option['label'], 
                        description=option['desc'],
                        default=option['label'].lower() in data['dm'],
                    ) 
                    for option in PM_Options
                ],
                min_values=1,
                max_values=len(PM_Options),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [option.lower() for option in select.values]

                v.db.update_dash(guild, 'moderation.settings.ban.dm', new_values)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                for option in select.options:
                    option.default = option.label.lower() in new_values

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BanMessageSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Default message purge")
        container.add_text("Select the previous days of messages to purge when a user is banned")
        class BanPurgeSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[discord.SelectOption(label=str(option), default=str(option) in data['deleteMessageDays']) for option in range(7)],
                min_values=1,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = select.values[0]

                v.db.update_dash(guild, 'moderation.settings.ban.deleteMessageDays', new_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                for option in select.options:
                    option.default = option.label in new_value

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BanPurgeSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginModerator(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, btn, itr):
                pass
        self.add_item(ViewButtons())
class ModeratorMuteContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['moderation']['settings']['mute']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Mute Settings")
        container.add_text("All the settings for muting")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Private Message")
        container.add_text("Send a private message to the user when they are muted")
        class MuteMessageSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(
                        label=option['label'], 
                        description=option['desc'],
                        default=option['label'].lower() in data['dm'],
                    ) 
                    for option in PM_Options
                ],
                min_values=1,
                max_values=len(PM_Options),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [option.lower() for option in select.values]

                v.db.update_dash(guild, 'moderation.settings.mute.dm', new_values)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                for option in select.options:
                    option.default = option.label.lower() in new_values

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MuteMessageSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Mute Type")
        container.add_text("Select the type of mute to apply")
        class MuteTypeSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Role", default=data['type'] == "role"),
                    discord.SelectOption(label="Timeout", default=data['type'] == "timeout"),
                ],
                min_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                new_value = select.values[0]
                
                for option in select.options:
                    option.default = option.label == new_value

                v.db.update_dash(guild, 'moderation.settings.mute.type', new_value.lower())
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MuteTypeSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Default Mute Duration")
        container.add_text("Select the mute duration")
        class MuteTimeSelect(ActionRow):
            time_option = ["60 SEC", "5 MIN", "10 MIN", "1 HOUR", "1 DAY", "1 WEEK"]
            @select(
                placeholder="Select an option",
                options=[discord.SelectOption(label=option, default=option.replace(" ", "-").lower() in data['duration']) for option in time_option],
                min_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                new_value = select.values[0]
                
                for option in select.options:
                    option.default = option.label == new_value

                v.db.update_dash(guild, 'moderation.settings.mute.duration', new_value.replace(" ", "-").lower())
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MuteTimeSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginModerator(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, btn, itr):
                pass
        self.add_item(ViewButtons())
class ModeratorWarnContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild)['moderation']['settings']['warn']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Warn Settings")
        container.add_text("All the settings for Warning")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Private Message")
        container.add_text("Send a private message to the user when they are warned")
        class WarnMessageSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(
                        label=option['label'], 
                        description=option['desc'],
                        default=option['label'].lower() in data['dm'],
                    ) 
                    for option in PM_Options
                ],
                min_values=1,
                max_values=len(PM_Options),
            )
            async def callback(self, select, interaction: discord.Interaction): 
                new_values = [option.lower() for option in select.values]

                v.db.update_dash(guild, 'moderation.settings.warn.dm', new_values)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                for option in select.options:
                    option.default = option.label.lower() in new_values

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(WarnMessageSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginModerator(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, btn, itr):
                pass
        self.add_item(ViewButtons())
class PluginModerator(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['moderation']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Moderation")
        container.add_text("Keep your server safe with auto-moderation & empower your mods with powerful moderation tools")
       
        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'moderation.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'moderation.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ModerationSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Kick"),
                    discord.SelectOption(label="Ban"),
                    discord.SelectOption(label="Mute"),
                    discord.SelectOption(label="Warn"),
                    discord.SelectOption(label="Audit Logging"), # TODO
                ],
            )
            async def callback(self, select, interaction: discord.Interaction):
                if select.values[0] == "Kick":
                    return await interaction.response.edit_message(view=ModeratorKickContainer(guild))
                if select.values[0] == "Ban":
                    return await interaction.response.edit_message(view=ModeratorBanContainer(guild))
                if select.values[0] == "Mute":
                    return await interaction.response.edit_message(view=ModeratorMuteContainer(guild))
                if select.values[0] == "Warn":
                    return await interaction.response.edit_message(view=ModeratorWarnContainer(guild))
        
        container.add_text("**Choose a moderation setting to configure**")
        container.add_item(ModerationSelect())

        self.add_item(container)

# Verification
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
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
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
                    discord.SelectOption(label="Instant Access", default=data['mode'] == "instant"),
                    discord.SelectOption(label="Captcha (DM)", default=data['mode'] == "captcha_dm"),
                    discord.SelectOption(label="Captcha (Channel)", default=data['mode'] == "captcha_channel"),
                ],
                min_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                new_value = select.values[0]
                
                for option in select.options:
                    option.default = option.label == new_value

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
                    option.default = option.label == new_value

                v.db.update_dash(guild, 'verification.failAction', new_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(FailActionSelect())

        self.add_item(container)
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

        class VerificationSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Message"),
                    discord.SelectOption(label="Channel & Role"),
                    discord.SelectOption(label="Advanced"),
                ],
            )
            async def callback(self, select, interaction: discord.Interaction):
                if select.values[0] == "Message":
                    await interaction.response.edit_message(view=VerificationMessage(guild))
                if select.values[0] == "Channel & Role":
                    await interaction.response.edit_message(view=VerificationChanRoleOptions(guild))
                if select.values[0] == "Advanced":
                    await interaction.response.edit_message(view=VerificationGeneralOptions(guild))
        container.add_item(VerificationSelect())
        
        self.add_item(container)

# TODO: Starboard

# TODO: View & Edit views
class ViewForms(DesignerView):
    def __init__(self, guild: discord.Guild, idx: int):
        super().__init__(timeout=None)
        data = v.db.get_server_config(guild.id)["forms"][idx]
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text(f"# {data['name']} ({data['id']})")
        container.add_text(f"{data['description']}")

        self.add_item(container)
class PluginForms(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['forms']
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Forms")
        container.add_text("Configure forms in the dashboard.")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'forms.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'forms.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CreateFormButton(ActionRow):
            @button(
                label="Create Form",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_message("You selected Create Form")
        container.add_item(CreateFormButton())

        class SelectForums(ActionRow):
            @select(
                placeholder="Select a form",
                options=[
                    discord.SelectOption(label=f"{option['name']}", description=f"{option['description']}", value=f"{option['id']}") 
                    for option in v.db.get_server_config(guild.id)["forms"]
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                hub_idx = None
                for idx, form in enumerate(v.db.get_server_config(guild.id)["forms"]):
                    if form['id'] == select.values[0]:
                        hub_idx = idx

                await interaction.response.send_message(view=ViewForms(guild, hub_idx))
        container.add_item(SelectForums())

        self.add_item(container)

# Temporary Channels
class AddNewTempChannelHub(DesignerView):
    def __init__(self, guild: discord.Guild, user: discord.User):
        super().__init__(timeout=None)
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

                        await interaction.response.send_message(f"Saving Hub Name to {self.children[0].item.value}", ephemeral=True)
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
                        btn.label = f"{self.children[0].item.value}".format(index="1", username=user.name)
                        await interaction.response.edit_message(view=container.view)

                        await interaction.followup.send(f"Saving Channel Name to {self.children[0].item.value}", ephemeral=True)
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
                        await interaction.response.edit_message(view=AddNewTempChannelHub(guild, user))
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

                        await interaction.response.send_message(f"Saving user limit to {self.children[0].item.value}", ephemeral=True)
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
                        await interaction.response.send_message(f"Saving bitrate to {self.children[0].item.value}", ephemeral=True)
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
                        await interaction.response.edit_message(view=AddNewTempChannelHub(guild, user))
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
                        await interaction.response.edit_message(view=AddNewTempChannelHub(guild, user))
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
                print(data)

                # TODO: on create button
                # if data['sync_hub_category'] == True:
                    # if data['category_id'] == '':
                    #     # create category
                    #     category = await guild.create_category_channel(data['hub_name'], reason=f"Temporary category for hub {data['id']}")
                    #     data['category_id'] = category.id
                    # else:
                    #     category = await guild.fetch_channel(data['category_id'])
                    #     data['category_id'] = category.id
                
                # vc = await category.create_voice_channel(data['hub_name'], reason=f"Temporary voice channel for hub {data['id']}")
                # data['channel_id'] = vc.id
                
                # data.pop('default') # remove key 'default' before saving to the database

                await interaction.response.send_message((
                    f"Successfully created hub {data['id']}"
                    "\n\n**Please be aware that you created a new hub with default settings. You can change them in the hub settings menu.**" if data['default'] == True else ""
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
                                description="Default user limit for all temporary voice channels. Max limit 0-99"
                            ),
                            title="Edit User limit",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        userLimit = self.children[0].item.value

                        v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.user_limit', userLimit)
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

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
                class BitrateModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label( # Bitrate
                                "Bitrate",
                                discord.ui.InputText(
                                    placeholder="0-96000",
                                    value=f"{data['bitrate']}",
                                    style=discord.InputTextStyle.short,
                                    max_length=5,
                                ),
                                description="Default bitrate for all temporary voice channels. Limit of 0kbps - 96kbps"
                            ),
                            title="Edit Bitrate",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        bitrate = self.children[0].item.value

                        v.db.update_dash(guild, f'temporary_channels.hubs.{idx}.bitrate', bitrate)
                        v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                        await interaction.response.send_message(f"Saving bitrate to {bitrate}", ephemeral=True)
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

        class SaveNewHubButton(ActionRow):
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
        self.add_item(SaveNewHubButton())
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

# Leveling
class LevelingLevelingUpContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Leveling Up")
        container.add_text("Whenever the user gains a level, BobCat can send a message.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Level up announcement")

        class LevelUpSettingSelect(ActionRow):
            @select(
                placeholder="Select a option",
                options=[
                    discord.SelectOption(label="Disabled", value="disabled", default=data['message']['status'] == 'disabled'),
                    discord.SelectOption(label="Current Channel", value="current", default=data['message']['status'] == 'current'),
                    discord.SelectOption(label="Private Message", value="dm", default=data['message']['status'] == 'dm'),
                    discord.SelectOption(label="Custom Channel", value="custom", default=data['message']['status'] == 'custom'),
                ],
                custom_id="level_up_setting_select",
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                settingSelect: discord.ui.Select = container.get_item("level_up_setting_select")
                
                if select.values[0] == "custom":
                    for option in settingSelect.options:
                        option.default = False
                    
                    settingSelect.options[3].default = True
                    
                    lvlupChannelSelect = container.get_item("LevelUpChannel")
                    lvlupChannelSelect.disabled = False

                    v.db.update_dash(guild, 'leveling.message.status', select.values[0])
                    v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                    return await interaction.response.edit_message(view=interaction.view)

                selected_value = select.values[0]

                # Reset all defaults
                for option in settingSelect.options:
                    option.default = False

                # Apply new default
                for option in settingSelect.options:
                    if option.value == selected_value:
                        option.default = True

                v.db.update_dash(guild, 'leveling.message.status', selected_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                if selected_value != "custom": # Disable channel select if not custom
                    lvlupChannelSelect = container.get_item("LevelUpChannel")
                    lvlupChannelSelect.disabled = True

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(LevelUpSettingSelect())
        
        container.add_text("Announcement Channel")
        
        df_value = []
        if data['channel'] != None and data['message']['status'] == 'custom':
            df_value = [ guild.get_channel(int(data['channel'])) ]

        class LevelUpChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                custom_id="LevelUpChannel",
                default_values=df_value,
                disabled=False if data['message']['status'] == 'custom' else True,
                min_values=0
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                chan: discord.TextChannel = select.values[0]

                v.db.update_dash(guild, 'leveling.channel', str(chan.id))
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(LevelUpChannelSelect())
        
        self.add_item(container)

        class GoBackButton(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))
        self.add_item(GoBackButton())
class LevelingServerCardContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Server Card")
        container.add_text("You can customize the default /rank card in your server. Every member of your server will have that rank card.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        response = requests.post("http://198.50.133.104:8065/lvl-cards")
        baseURI = "http://198.50.133.104:8065/static/lvl-cards/gallery/"
        if response.status_code == 200:
            jdata = response.json()
            default_cards = jdata['default']
            fun_cards = jdata['cards']

        container.add_text("## Default Colors")
        default_gallery = discord.ui.MediaGallery()
        default_gallery.add_item(
            url=f"{baseURI}/default_gallery.png",
        )
        container.add_item(default_gallery)

        container.add_text("## Picture Backgrounds")
        picture_gallery = discord.ui.MediaGallery()
        picture_gallery.add_item(
            url=f"{baseURI}/fun_gallery.png",
        )
        container.add_item(picture_gallery)

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ImgSelect(ActionRow):
            defc = [ 
                discord.SelectOption(label=f"{option['card_name']}", value=option['card'], default=data['card'] == option['card']) for option in default_cards
            ]
            func = [
                discord.SelectOption(label=f"{option['card_name']}", value=option['card'], default=data['card'] == option['card']) for option in fun_cards
            ]
            @select(
                placeholder="Select an Image",
                options=defc + func,
                custom_id="img_select",
                disabled=False,
                select_type=discord.ComponentType.string_select,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                selected_card = select.values[0]
                print(selected_card)

                v.db.update_dash(guild, 'leveling.card', selected_card)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                # Reset all defaults
                for option in select.options:
                    option.default = False

                # Apply new default
                for option in select.options:
                    if option.value == selected_card:
                        option.default = True

                await interaction.response.edit_message(view=interaction.view)

                card = [ option['card_name'] for option in default_cards + fun_cards if option['card'] == selected_card ][0]
                await interaction.followup.send(f"Updated your rank card to {card}!", ephemeral=True)
        container.add_item(ImgSelect())

        self.add_item(container)

        class GoBackButton(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))
        self.add_item(GoBackButton())
class LevelingRoleRewardsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Role Rewards")
        container.add_text("Role Rewards are given to users when they hit the respective level.")
        container.add_text("when checked users can have multiple rewards at once but the highest reward will be given. when unchecked only the highest reward will be given and the previous rewards will be removed")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class RoleRewardsStackSelect(ActionRow):
            @select(
                placeholder="Stack or Remove Rewards",
                options=[
                    discord.SelectOption(label="Stack rewards", description="Users can have multiple rewards at once", default=True if data['roleRewards']['stacked'] == True else False),
                    discord.SelectOption(label="Remove rewards", description="Users can only have the highest reward", default=True if data['roleRewards']['stacked'] == False else False),
                ],
                min_values=1,
                max_values=1
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = True if select.values[0] == "Stack rewards" else False
                
                v.db.update_dash(guild, 'leveling.roleRewards.stacked', new_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.send_message(view=interaction.view)

                await interaction.followup.send(f"Role rewards updated to {select.values[0].split(' ')[0]}!", ephemeral=True)
        container.add_item(RoleRewardsStackSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class RoleAddRewardModal(discord.ui.DesignerModal):
            def __init__(self):
                lvlselect = discord.ui.Label(
                    "Level",
                    discord.ui.InputText(
                        placeholder="Select a number for level",
                        style=discord.InputTextStyle.short,
                        value="1",
                        required=True,
                    )
                )
                roleselect = discord.ui.Label(
                    "Role",
                    discord.ui.RoleSelect(
                        select_type=discord.ComponentType.role_select,
                        placeholder="Select a role",
                        required=True
                    )
                )
                super().__init__(
                    lvlselect,
                    roleselect,
                    title="Add Role Reward",
                )
            async def callback(self, interaction: discord.Interaction):
                level = self.children[0].item.value
                role = self.children[1].item.values[0]

                guild_role = guild.get_role(role.id)

                if guild_role.position > guild.me.top_role.position:
                    return await interaction.response.send_message("Whoops, I can't assign that role as it is higher than my highest role. Please change the role position in your server settings.", ephemeral=True)
                
                roles = data['roleRewards']['roles']
                roles.append({ 'id': str(role.id), 'level': int(level) })
                v.db.update_dash(guild, 'leveling.roleRewards.roles', roles)

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.send_message(f"Role rewards updated!\n**Level:** {self.children[0]}\n**Role:** {self.children[1]}")
        class RoleAddReward(ActionRow):
            @button(
                label="Add Role Reward",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(RoleAddRewardModal())
        container.add_item(RoleAddReward())

        if guild.me.guild_permissions.manage_roles == False:
            container.add_text("Whoops, it looks like I can't give any roles. Please fix that by giving me the MANAGE ROLES or ADMINISTRATOR permissions.")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        for reward in data['roleRewards']['roles']:
            container.add_text(f"**Level:** {reward['level']}\n**Role:** {guild.get_role(int(reward['id'])).mention}")
            container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class LevelingXpOptionsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# XP Options & Modifiers")
        container.add_text("Customize the other options of the XP system.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## No XP Channels")
        container.add_text("Prevent your members from gaining XP if they send messages in certain text channels.")

        class NoXpChannelsSelect(ActionRow): # TODO: make this work
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
            )
            async def callback(self, select, interaction: discord.Interaction):
                await interaction.response.defer()
                await interaction.followup.send(f"You selected {select.values[0].name}")
        container.add_item(NoXpChannelsSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Auto Reset")
        container.add_text("Should the bot reset user's level and XP if they leave the server?")
        class AutoResetToggle(ActionRow):
            @button(
                label="Disabled" if data['auto_reset'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['auto_reset'] == False else discord.ButtonStyle.green,
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'leveling.auto_reset', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'leveling.auto_reset', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("update_at")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(AutoResetToggle())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Economy Integration")
        container.add_text("Each time a user sends a message or levels up they gain coins.")
        class EconomyToggle(ActionRow):
            @button(
                label="Disabled" if data['economy'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['economy'] == False else discord.ButtonStyle.green,
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'leveling.economy', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'leveling.economy', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red
                
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("update_at")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(EconomyToggle())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class PluginLeveling(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Leveling")
        container.add_text("Give your members XP and Levels when they send messages")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'leveling.status', True)
                    
                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'leveling.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class LevelingPluginSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Level Message", description="Send a message when a user levels up"),
                    discord.SelectOption(label="Server Card", description="Reply with a card when they use the /rank command"),
                    discord.SelectOption(label="Role Rewards", description="Give roles to users when they hit certain levels"),
                    discord.SelectOption(label="XP Options & Modifiers", description="Customize other XP options"),
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                if select.values[0] == "Level Message":
                    await interaction.response.edit_message(view=LevelingLevelingUpContainer(guild))
                if select.values[0] == "Server Card":
                    await interaction.response.edit_message(view=LevelingServerCardContainer(guild))
                if select.values[0] == "Role Rewards":
                    await interaction.response.edit_message(view=LevelingRoleRewardsContainer(guild))
                if select.values[0] == "XP Options & Modifiers":
                    await interaction.response.edit_message(view=LevelingXpOptionsContainer(guild))

        container.add_item(LevelingPluginSelect())

        self.add_item(container)

# TODO: Add Ticketing

# Birthdays
class BirthdaysBirthdayMessageContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['birthdays']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Birthday Message")
        container.add_text("BobCat can remember users' birthdays and wish them a happy one in a specific channel.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Happy Birthday Channel")
        container.add_text("Choose the channel for the messages to be sent in")
        class BirthdayChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                default_values=[ guild.get_channel(int(data['channel_id'])) ],
                max_values=1,
            )
            async def callback(self, select, interaction: discord.Interaction):
                new_channel = select.values[0].id

                v.db.update_dash(guild.id, 'birthdays.channel_id', str(new_channel))
                v.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BirthdayChannelSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Happy Birthday Wishing Hour")
        container.add_text("Change the hour at which the birthday messages should be sent with respect to the timezone of your server")
        class BirthdayMessageSelect(ActionRow):
            @select(
                placeholder="Select a time",
                options=[
                    discord.SelectOption(
                        label=f"{message['time']}", 
                        value=message['value'], 
                        default=message['value'] == str(data['message_hour'])
                    ) 
                    for message in TIME_OPTIONS
                ],
                max_values=1,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = select.values[0]

                v.db.update_dash(guild.id, 'birthdays.message_hour', new_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BirthdayMessageSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Happy Birthday Message")
        container.add_text("Send a message to the user when on their sepcial day")
        class BirthdayMessageModel(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Birthday Message",
                        discord.ui.InputText(
                            placeholder="Write your message here...",
                            value=f"{data['message']}",
                            style=discord.InputTextStyle.long,
                        )
                    ),
                    title="Birthday Message",
                )
            async def callback(self, interaction: discord.Interaction):
                new_message = self.children[0].value

                v.db.update_dash(guild.id, 'birthdays.message', new_message)
                v.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        class BirthdayMessageButton(ActionRow):
            @button(
                label="Edit Message",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(BirthdayMessageModel())
        container.add_item(BirthdayMessageButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginBirthdays(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class BirthdaysBirthdayRoleContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['birthdays']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Birthday Role")
        container.add_text("Give a role to a user when they have a birthday")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class BirthdayRoleSelect(ActionRow):
            @role_select(
                placeholder="Select a role",
                max_values=1,
                default_values=[ guild.get_role(int(data['birthday_role'])) ]
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_role = select.values[0].id

                v.db.update_dash(guild.id, 'birthdays.birthday_role', str(new_role))
                v.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BirthdayRoleSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginBirthdays(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class PluginBirthdays(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['birthdays']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Birthdays")
        container.add_text("Track your members birthdays and wish them a happy birthday")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild.id, 'birthdays.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild.id, 'birthdays.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class BirthdayPluginSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Birthday Message"),
                    discord.SelectOption(label="Birthday Role"),
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                if select.values[0] == "Birthday Message":
                    await interaction.response.edit_message(view=BirthdaysBirthdayMessageContainer(guild))
                if select.values[0] == "Birthday Role":
                    await interaction.response.edit_message(view=BirthdaysBirthdayRoleContainer(guild))

        container.add_item(BirthdayPluginSelect())
        self.add_item(container)

# Economy
class EconomyCustomizeCoinsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Customize your currency")
        container.add_text("Customize your currency icon and name")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CoinModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Currency Icon
                        "Currency Icon",
                        discord.ui.InputText(
                            placeholder="Currency icon here...",
                            value=f"{data['icon']}",
                            style=discord.InputTextStyle.short,
                        ),
                        description="Only use default emojis or Discord emojis ( <:EMOJI_NAME:EMOJI_ID> )",
                    ),
                    discord.ui.Label( # Currency Name
                        "Currency Name",
                        discord.ui.InputText(
                            placeholder="Currency name here...",
                            value=f"{data['name']}",
                            style=discord.InputTextStyle.short,
                        ),
                        description="Your currency name will be displayed in the currency shop and in the currency leaderboard",
                    ),
                    title="Customize Your Currency Name and Icon",
                )
            async def callback(self, interaction: discord.Interaction):
                newCoinIcon = self.children[0].item.value
                newCoinName = self.children[1].item.value
                
                v.db.update_dash(guild.id, 'economy.icon', newCoinIcon)
                v.db.update_dash(guild.id, 'economy.name', newCoinName)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        
        class CustomizeCoinButton(ActionRow):
            @button(
                label="Edit currency icon and name",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(CoinModal())
        container.add_item(CustomizeCoinButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def go_back(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class EconomyShopContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']
        shop_items: list = data["shop"]
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Shop Items")
        container.add_text("Customize the items in your shop")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ShopModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Item Icon
                        "Item Icon",
                        discord.ui.InputText(
                            placeholder="Item icon here...",
                            value="🪙",
                            style=discord.InputTextStyle.short,
                        ),
                        description="Only use default emojis or Discord emojis ( <:EMOJI_NAME:EMOJI_ID> )",
                    ),
                    discord.ui.Label( # Item Name
                        "Item Name",
                        discord.ui.InputText(
                            placeholder="Item name here...",
                            value="BobCat Coin",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    discord.ui.Label( # Item Price
                        "Item Price",
                        discord.ui.InputText(
                            placeholder="Item price here...",
                            value="100",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    discord.ui.Label( # Item Description
                        "Item Description",
                        discord.ui.InputText(
                            placeholder="Item description here...",
                            value="",
                            style=discord.InputTextStyle.long,
                            required=False
                        )
                    ),
                    discord.ui.Label( # Item Max Limit
                        "Max amount per player",
                        discord.ui.InputText(
                            placeholder="Item limit here...",
                            value="5",
                            style=discord.InputTextStyle.short,
                            required=False
                        ),
                    ),
                    # discord.ui.Label( "Type", discord.ui.Select(placeholder="Select an option", options=[ discord.SelectOption(label="Usable Item", default=True), discord.SelectOption(label="Role") ]) ) # Item Type
                    title="Create a shop item",
                )
            async def callback(self, interaction: discord.Interaction):
                newItem = {
                    "icon": self.children[0].item.value, 
                    "name": self.children[1].item.value, 
                    "price": self.children[2].item.value, 
                    "description": self.children[3].item.value, 
                    "max_limit": self.children[4].item.value,
                    "type": "usable-item"
                }
                
                NewShopItems = shop_items.append(newItem)

                v.db.update_dash(guild.id, 'shop', NewShopItems)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                # update the main container view
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                container.add_text(f"**{newItem['name']}**  Max: {newItem['max_limit']}")
                container.add_text(f"{newItem['icon']}")
                container.add_text(f"{newItem['price']} {data['icon']}")
                
                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        class CustomizeShopButton(ActionRow):
            @button(
                label="Add Shop Item",
                style=discord.ButtonStyle.primary,
                disabled=True if len(shop_items) >= 5 else False,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(ShopModal())
        container.add_item(CustomizeShopButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        for index, item in enumerate(shop_items):
            container.add_text(f"**{item['name']}**  Max: {item['max_limit']}")
            container.add_text(f"{item['icon']}")
            container.add_text(f"{item['price']} {data['icon']}")
            
            # Only show separator if NOT the last item
            if index != len(shop_items) - 1:
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class EconomyRestrictionsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Restrictions")
        container.add_text("Handle game restrictions for all games in one place")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Max Gambling")
        class MaxGamblingModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Max Gambling
                        "Max Gambling",
                        discord.ui.InputText(
                            placeholder="",
                            value=f"{data['MaxGambling']}",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    title="Edit your max gambling amount",
                )
            async def callback(self, interaction: discord.Interaction):
                maxGambling = self.children[0].item.value

                v.db.update_dash(guild.id, 'economy.MaxGambling', maxGambling)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        class CustomizeMaxGamblingButton(ActionRow):
            @button(
                label="Edit Max Gambling",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(MaxGamblingModal())
        container.add_item(CustomizeMaxGamblingButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Max Payment")
        class MaxPaymentModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Max Payment
                        "Max Payment",
                        discord.ui.InputText(
                            placeholder="",
                            value=f"{data['MaxPayment']}",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    title="Edit your max Payment amount",
                )
            async def callback(self, interaction: discord.Interaction):
                maxPayment = self.children[0].item.value

                v.db.update_dash(guild.id, 'economy.MaxPayment', maxPayment)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        class CustomizeMaxPaymentButton(ActionRow):
            @button(
                label="Edit Max Payment",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(MaxPaymentModal())
        container.add_item(CustomizeMaxPaymentButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())
class EconomyResetContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Reset Economy")
        container.add_text("This will remove all the coins or shop items from your users")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ResetEconomyButton(ActionRow):
            @button(
                label="Reset Economy coins",
                style=discord.ButtonStyle.red,
            )
            async def ResetEcoCoins(self, button, interaction: discord.Interaction):
                class ConfirmResetEcoCoins(discord.ui.View):
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True
                        await interaction.response.edit_message(content="Reset cancelled.", view=self)
                    
                    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red)
                    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True

                        users = v.db.get_server_config(guild.id)['economy']
                        for user in users:
                            users[user]['wallet'] = 0
                            users[user]['bank'] = 0
                            users[user]['bag'] = []
                            v.db.update_server_config(guild.id, False, 'economy', users)
                        
                        v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                        await interaction.response.edit_message(content="Economy coins have been reset.", view=self)
                await interaction.response.send_message(f"This action is strictly irreversible! Everyone will lose their coins.", view=ConfirmResetEcoCoins(), ephemeral=True)
            
            @button(
                label="Reset Economy shop",
                style=discord.ButtonStyle.red,
            )
            async def resetecoshop(self, button, interaction: discord.Interaction):
                class ConfirmResetEcoShop(discord.ui.View):
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True
                        await interaction.response.edit_message(content="Reset cancelled.", view=self)
                    
                    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red)
                    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True

                        shop = [
                            {"name": "Teddy", "price": 50, "icon": "🧸", "description": "Very sot cuddly teddy bear", "type": "string", "max_limit": 5},
                            {"name": "Watch", "price": 100, "icon": "⌚", "description": "A thing to tell the time", "type": "string", "max_limit": 5},
                            {"name": "Phone", "price": 500, "icon": "📱", "description": "A phone", "type": "string", "max_limit": 5},
                            {"name": "Laptop", "price": 1000, "icon": "💻", "description": "A nice laptop for work and play", "type": "string", "max_limit": 5},
                        ]
                        v.db.update_dash(guild.id, 'economy.shop', shop)

                        v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())
                        
                        await interaction.response.edit_message(content="Economy shop has been reset.", view=self)
                await interaction.response.send_message(f"This action is strictly irreversible! The economy shop will be reset back to default.", view=ConfirmResetEcoShop(), ephemeral=True)
        container.add_item(ResetEconomyButton())

        self.add_item(container)
        
        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))
        self.add_item(ViewButtons())
class PluginEconomy(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Economy")
        container.add_text("Players can gain coins once a day. A player can stake their coins at games. Use your coins to buy items from the shop.")
        
        class EconomyStatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild.id, 'economy.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild.id, 'economy.status', True)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(EconomyStatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class EconomyPluginSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Customize Coins"),
                    discord.SelectOption(label="Shop"),
                    discord.SelectOption(label="Restrictions"),
                    discord.SelectOption(label="Reset economy"),
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                if select.values[0] == "Customize Coins":
                    await interaction.response.edit_message(view=EconomyCustomizeCoinsContainer(guild))
                if select.values[0] == "Shop":
                    await interaction.response.edit_message(view=EconomyShopContainer(guild))
                if select.values[0] == "Restrictions":
                    await interaction.response.edit_message(view=EconomyRestrictionsContainer(guild))
                if select.values[0] == "Reset economy":
                    await interaction.response.edit_message(view=EconomyResetContainer(guild))
        
        container.add_item(EconomyPluginSelect())

        self.add_item(container)


PLUGIN_OPTIONS = {
    "Bot Settings": { "plugin": PluginBotSettings,  "premium": False },
    "Welcome & Goodbye": { "plugin": PluginWelcome,  "premium": False },
    "Moderator": { "plugin": PluginModerator,  "premium": False },
    "Verification": { "plugin": PluginVerification,  "premium": False },
    # "Starboard": {"plugin": PluginStarboard, "premium": True},
    "Forms": { "plugin": PluginForms,  "premium": True },
    "Temporary Channels": { "plugin": PluginTempChannels,  "premium": True },
    # "Ticketing": {"plugin": PluginTicketing, "premium": True},
    "Leveling": { "plugin": PluginLeveling,  "premium": False },
    "Birthdays": { "plugin": PluginBirthdays,  "premium": True },
    "Economy": { "plugin": PluginEconomy,  "premium": False },
}

class PluginView(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Pick a plugin")
        container.add_text("Pick a plugin to configure in the dashboard.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        class PluginSelector(ActionRow):
            @select(
                placeholder="Select a plugin",
                options=[
                    discord.SelectOption(
                        label=name,
                        emoji=v.premium if plugin['premium'] and not v.db.get_server_config(guild, True)['premium']['status'] else None,
                    )
                    for name, plugin in PLUGIN_OPTIONS.items()
                ],
                custom_id="PluginSelect",
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                data = PLUGIN_OPTIONS.get(select.values[0])
                view_class = data['plugin']

                if data['premium'] and not v.db.get_server_config(guild, True)['premium']['status']:
                    return await interaction.response.send_message(f"{v.premium} This is a premium plugin. Please upgrade to premium to access this feature.", ephemeral=True)

                if view_class:
                    await interaction.response.send_message(view=view_class(interaction.guild, interaction.user))
                else:
                    await interaction.response.send_message("Invalid plugin selected")
        
        container.add_item(PluginSelector())

        self.add_item(container)

class DiscordDashboard(commands.Cog):
    def __init__(self, client):
        self.client: commands.Bot = client
    
    def author_is_mod(self, guild: discord.Guild, user: discord.Member):
        data = v.db.get_server_config(guild, True)['settings']

        if any(
            str(role.id) in data['admin_roles'] or 
            str(role.id) in data['bot_masters'] 
            for role in user.roles
        ):
            return True
        return False

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.client.guilds:
            self.client.add_view(PluginView(guild))

    @commands.slash_command(name="dashboard", description="Dashboard", guild_ids=v.guild_ids)
    @discord.option("plugin", 
        description="The plugin to configure", 
        required=False, 
        choices=list(PLUGIN_OPTIONS.keys())
    )
    async def dashboard(self, ctx: discord.ApplicationContext, plugin: str = None):
        # ADMINS AND BOT MASTERS ONLY
        mod = self.author_is_mod(ctx.guild, ctx.author)
        if not mod:
            return await ctx.respond("You do not have permission to use this command.", ephemeral=True)

        if plugin:
            data = PLUGIN_OPTIONS.get(plugin)
            view_class = data['plugin']
            
            if data['premium'] and not v.db.get_server_config(ctx.guild, True)['premium']['status']:
                return await ctx.respond(f"{v.premium} This is a premium plugin. Please upgrade to premium to access this feature.", ephemeral=True)

            if view_class:
                return await ctx.respond(view=view_class(ctx.guild, ctx.user))
        
        # Default dashboard
        await ctx.respond(view=PluginView(ctx.guild, ctx.user))

def setup(client):
    client.add_cog(DiscordDashboard(client))