import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

TIME_OPTIONS = [
    {
        "time": f"{hour:02d}:00 - "
                f"{12 if hour % 12 == 0 else hour % 12}"
                f"{'am' if hour < 12 else 'pm'}",
        "value": str(hour)
    }
    for hour in range(24)
]

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
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

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
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

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
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

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

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(StatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("**Configure**")
        class PluginButtons(ActionRow):
            @button(
                label="Message",
                style=discord.ButtonStyle.gray,
            )
            async def msgCallback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BirthdaysBirthdayMessageContainer(guild))
            
            @button(
                label="Role",
                style=discord.ButtonStyle.gray,
            )
            async def roleCallback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BirthdaysBirthdayRoleContainer(guild))

        container.add_item(PluginButtons())

        self.add_item(container)
