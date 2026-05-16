import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

PM_OPTIONS = [ 
    { "label": "Server", "desc": "Include the server name" }, 
    { "label": "Action", "desc": "Include the action of what happend" }, 
    {  "label": "Reason", "desc": "Include the reason for the kick" }, 
    { "label": "Moderator", "desc": "Include the moderator who kicked the user" }
]

AUDIT_EVENTS = {
    "Moderation": [
        { "name": "Ban", "value": "mod_ban"},
        { "name": "Unbanned", "value": "mod_unban"},
        { "name": "Kick", "value": "mod_kick"},
        { "name": "Muted", "value": "mod_mute"},
        { "name": "Unmuted", "value": "mod_unmute"},
        { "name": "Warn", "value": "mod_warn"},
        { "name": "Unwarn", "value": "mod_unwarn"},
    ],
    "Server": [
        { "name": "Updated", "value": "server_update"},
        { "name": "Emojis Updated", "value": "server_emoji"},
        { "name": "Invite Created", "value": "server_invite_create"},
        { "name": "Invite Deleted", "value": "server_invite_delete"},
    ],
    "Roles": [
        { "name": "Updated", "value": "role_update"},
        { "name": "Created", "value": "role_create"},
        { "name": "Deleted", "value": "role_delete"},
    ],
    "Channel": [
        { "name": "Updated", "value": "channel_update"},
        { "name": "Created", "value": "channel_create"},
        { "name": "Deleted", "value": "channel_delete"},
    ],
    # "Member": [
    #     { "name": "Join", "value": "member_join"},
    #     { "name": "Leave", "value": "member_leave"},
    #     { "name": "Updated", "value": "member_update"},
    #     { "name": "Banned", "value": "member_ban"},
    #     { "name": "Unbanned", "value": "member_unban"},
    # ],
    # "Message": [
    #     { "name": "Message Edit", "value": "message_edit"},
    #     { "name": "Message Delete", "value": "message_delete"},
    # ],
    # "Systems": [
    #     { "name": "Verification", "value": "sys_verification"},
    # ],
}

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
                    for option in PM_OPTIONS
                ],
                min_values=1,
                max_values=len(PM_OPTIONS),
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
                await interaction.response.edit_message(view=PluginModeration(guild))

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
                    for option in PM_OPTIONS
                ],
                min_values=1,
                max_values=len(PM_OPTIONS),
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
                await interaction.response.edit_message(view=PluginModeration(guild))

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
                    for option in PM_OPTIONS
                ],
                min_values=1,
                max_values=len(PM_OPTIONS),
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
                await interaction.response.edit_message(view=PluginModeration(guild))

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
                    for option in PM_OPTIONS
                ],
                min_values=1,
                max_values=len(PM_OPTIONS),
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
                await interaction.response.edit_message(view=PluginModeration(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, btn, itr):
                pass
        self.add_item(ViewButtons())

class AuditLoggingContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['moderation']['logging']
        enabled_events: list = data.get('events', [])
 
        container = Container(color=v.style(guild))
        container.add_text("# Audit Logging")
        container.add_text("Set a logging channel and choose which events get logged. Don't miss anything happening in your server!")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class SelectAuditChannel(DesignerView):
            def __init__(self, guild: discord.Guild):
                super().__init__(timeout=None)

                channelContainer = Container(color=v.style(guild))
                channelContainer.add_text("# Logging channel")
                channelContainer.add_text("Set a logging channel and choose which events get logged!")
                channelContainer.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                class SelectAuditChannel(ActionRow):
                    @channel_select(
                        placeholder="Select an option",
                        min_values=1,
                        max_values=1,
                    )
                    async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                        v.db.update_dash(guild, 'moderation.logging.channel', select.values[0])
                        await interaction.response.edit_message(view=interaction.view)

                channelContainer.add_item(SelectAuditChannel())

                self.add_item(channelContainer)
                
                class ViewButtons(ActionRow):
                    @button(label="Go Back", style=discord.ButtonStyle.primary)
                    async def goBack(self, button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=AuditLoggingContainer(guild))
        
                    @button(
                        label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                        style=discord.ButtonStyle.gray,
                        custom_id="SaveSuccess",
                        disabled=True,
                    )
                    async def updateStatus(self, btn, itr):
                        pass
                self.add_item(ViewButtons())
        
        class SelecAuditEvents(DesignerView):
            def __init__(self, guild: discord.Guild):
                super().__init__(timeout=None)

                eventsContainer = Container(color=v.style(guild))
                eventsContainer.add_text("# Events")
                eventsContainer.add_text("Choose which events get logged!")
                eventsContainer.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

                for group_name, events in AUDIT_EVENTS.items():
                    eventsContainer.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
                    eventsContainer.add_text(f"**{group_name}**")

                    def make_row(gevents):
                        attrs = {}
                        for evt in gevents:
                            enabled = evt["value"] in enabled_events
                            async def _cb(self, btn: discord.ui.Button, interaction: discord.Interaction, _val=evt["value"]):
                                current = v.db.get_dash(guild.id)['moderation']['audit_logging'].get('events', [])
                                if _val in current:
                                    current.remove(_val)
                                    btn.style = discord.ButtonStyle.gray
                                else:
                                    current.append(_val)
                                    btn.style = discord.ButtonStyle.green
                                v.db.update_dash(guild.id, 'moderation.audit_logging.events', current)
                                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                                update_at = interaction.view.get_item("SaveSuccess")
                                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                                await interaction.response.edit_message(view=interaction.view)

                            attrs[f'btn_{evt["value"]}'] = button(
                                label=evt["name"],
                                style=discord.ButtonStyle.green if enabled else discord.ButtonStyle.gray,
                                custom_id=f'audit_{evt["value"]}',
                            )(_cb)

                        return type('EventRow', (ActionRow,), attrs)()

                    for i in range(0, len(events), 4):
                        eventsContainer.add_item(make_row(events[i:i+4]))

                self.add_item(eventsContainer)

                class ViewButtons(ActionRow):
                    @button(label="Go Back", style=discord.ButtonStyle.primary)
                    async def goBack(self, button, interaction: discord.Interaction):
                        await interaction.response.edit_message(view=SelectAuditChannel(guild))
        
                    @button(
                        label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                        style=discord.ButtonStyle.gray,
                        custom_id="SaveSuccess",
                        disabled=True,
                    )
                    async def updateStatus(self, btn, itr):
                        pass
                self.add_item(ViewButtons())

        class Buttons(ActionRow):
            @button(
                label="Channel",
                style=discord.ButtonStyle.gray,
            )
            async def channel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                button.style = discord.ButtonStyle.primary
                await interaction.response.edit_message(view=SelectAuditChannel(guild))

            @button(
                label="Events",
                style=discord.ButtonStyle.gray,
            )
            async def events_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                button.style = discord.ButtonStyle.primary
                await interaction.response.edit_message(view=SelecAuditEvents(guild))
            
            @button(
                label="Don't log bot actions: OFF" if not data.get('ignore_bots', False) else "Don't log bot actions: ON",
                style=discord.ButtonStyle.red if not data.get('ignore_bots', False) else discord.ButtonStyle.green,
                custom_id="ignore_bots_toggle",
            )
            async def botlog_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                current = v.db.get_dash(guild.id)['moderation']['audit_logging'].get('ignore_bots', False)
                new_val = not current
                v.db.update_dash(guild.id, 'moderation.audit_logging.ignore_bots', new_val)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                button.label = "Don't log bot actions: ON" if new_val else "Don't log bot actions: OFF"
                button.style = discord.ButtonStyle.green if new_val else discord.ButtonStyle.red
                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        
        container.add_item(Buttons())
        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(label="Go Back", style=discord.ButtonStyle.primary)
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginModeration(guild))
 
            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, btn, itr):
                pass
        self.add_item(ViewButtons())

class PluginModeration(DesignerView):
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

        container.add_text("**Configure**")
        class PluginButtons(ActionRow):
            @button(
                label="Kick",
                style=discord.ButtonStyle.gray
            )
            async def kickBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=ModeratorKickContainer(guild))

            @button(
                label="Ban",
                style=discord.ButtonStyle.gray
            )
            async def banBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=ModeratorBanContainer(guild))

            @button(
                label="Mute",
                style=discord.ButtonStyle.gray
            )
            async def muteBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=ModeratorMuteContainer(guild))

            @button(
                label="Warn",
                style=discord.ButtonStyle.gray
            )
            async def warnBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=ModeratorWarnContainer(guild))

            @button(
                label="Audit Logging",
                style=discord.ButtonStyle.gray
            )
            async def auditBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=AuditLoggingContainer(guild))

        container.add_item(PluginButtons())

        self.add_item(container)
