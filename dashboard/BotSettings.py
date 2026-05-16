import discord
from datetime import datetime
from discord.ext import commands
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

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
                v.db.update_server_config(guild, True, 'settings.admins', [str(role.id) for role in select.values])
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"

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
                v.db.update_server_config(guild, True, 'settings.masters', [str(role.id) for role in select.values])
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MastersSelect())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Back",
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
            def __init__(self):
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
                await interaction.response.send_modal(ColorModal())
        container.add_item(ColorButton())
        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Back",
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
                label="Back",
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

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Configure")

        class SettingsButtons(ActionRow):
            @button(
                label="Bot Masters",
                style=discord.ButtonStyle.gray,
            )
            async def botMasters(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BotSettingsMastersAndAdmins(guild))
            
            @button(
                label="Color",
                style=discord.ButtonStyle.gray,
            )
            async def botColor(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BotSettingsColor(guild))
            
            @button(
                label="Other Options",
                style=discord.ButtonStyle.gray,
            )
            async def otherOptions(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BotSettingsOptions(guild))

        container.add_item(SettingsButtons())
        self.add_item(container)
