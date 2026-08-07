import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, select, channel_select, role_select
from dashboard._components import FooterRow, StatusToggle, save_dash, refresh_footer

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
        data = Guild.get(str(guild.id)).run().dashboard.birthdays

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Birthday Message & Schedule")
        container.add_text("BobCat can remember members' birthdays and send them a automated birthday greeting.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- SECTION 1: CHANNEL SELECTION ---
        container.add_text("## Announcement Channel")
        container.add_text("Choose the channel where happy birthday wishes will be posted.")

        chan_obj = guild.get_channel(int(data['channel_id'])) if data.get('channel_id') else None
        default_chan = [chan_obj] if chan_obj else None

        class BirthdayChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                default_values=default_chan,
                max_values=1,
                min_values=0
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                new_channel = str(select.values[0].id) if select.values else None

                save_dash(guild, 'birthdays.channel_id', new_channel)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=BirthdaysBirthdayMessageContainer(guild))

        container.add_item(BirthdayChannelSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- SECTION 2: WISHING HOUR SELECTION ---
        container.add_text("## Wishing Hour")
        container.add_text("Select the hour at which birthday messages should be posted (with respect to your server timezone).")

        class BirthdayMessageSelect(ActionRow):
            @select(
                placeholder="Select a time",
                options=[
                    discord.SelectOption(
                        label=message['time'],
                        value=message['value'],
                        default=(message['value'] == str(data.get('message_hour', '0')))
                    )
                    for message in TIME_OPTIONS
                ],
                max_values=1,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = select.values[0]

                save_dash(guild, 'birthdays.message_hour', new_value)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=BirthdaysBirthdayMessageContainer(guild))

        container.add_item(BirthdayMessageSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- SECTION 3: MESSAGE CONTENT TEMPLATE ---
        container.add_text("## Birthday Message")
        class BirthdayMessageModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Birthday Message",
                        discord.ui.InputText(
                            placeholder="Write your happy birthday message...",
                            value=data['message'],
                            style=discord.InputTextStyle.long,
                            required=True
                        )
                    ),
                    title="Edit Birthday Message",
                )
            async def callback(self, interaction: discord.Interaction):
                item = self.children[0]
                new_message = item.item.value if hasattr(item, 'item') else item.value

                save_dash(guild, 'birthdays.message', new_message)
                refresh_footer(interaction.view, guild)

                await interaction.response.edit_message(view=BirthdaysBirthdayMessageContainer(guild))
                await interaction.followup.send("Updated birthday message template!", ephemeral=True)

        class BirthdayMessageButton(ActionRow):
            @button(
                label="Edit Message",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(BirthdayMessageModal())

        container.add_item(BirthdayMessageButton())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginBirthdays(guild)))

class BirthdaysBirthdayRoleContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.birthdays

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Birthday Role")
        container.add_text("Automatically assign a special temporary role to members on their birthday.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        role_obj = guild.get_role(int(data['birthday_role'])) if data.get('birthday_role') else None
        default_role = [role_obj] if role_obj else None

        class BirthdayRoleSelect(ActionRow):
            @role_select(
                placeholder="Select a role",
                max_values=1,
                min_values=0,
                default_values=default_role
            )
            async def callback(self, select: discord.ui.RoleSelect, interaction: discord.Interaction):
                new_role = str(select.values[0].id) if select.values else None

                save_dash(guild, 'birthdays.birthday_role', new_role)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=BirthdaysBirthdayRoleContainer(guild))

        container.add_item(BirthdayRoleSelect())

        if not guild.me.guild_permissions.manage_roles:
            container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
            container.add_text("⚠️ **Bot Permissions Missing:** Grant BobCat the `Manage Roles` permission to assign birthday roles.")

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginBirthdays(guild)))

class PluginBirthdays(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.birthdays

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Birthdays")
        container.add_text("Track your members' birthdays and wish them a happy birthday.")

        container.add_item(StatusToggle(guild, 'birthdays.status', data.get('status', False)))

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class PluginButtons(ActionRow):
            @button(
                label="Message & Schedule",
                style=discord.ButtonStyle.gray,
            )
            async def msgCallback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BirthdaysBirthdayMessageContainer(guild))
            
            @button(
                label="Birthday Role",
                style=discord.ButtonStyle.gray,
            )
            async def roleCallback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=BirthdaysBirthdayRoleContainer(guild))

        container.add_item(PluginButtons())
        self.add_item(container)