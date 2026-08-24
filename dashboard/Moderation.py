import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, select, channel_select, role_select
from dashboard._components import save_dash, refresh_footer, FooterRow, StatusToggle

PM_OPTIONS = [ 
    { "label": "Server", "desc": "Include the server name" }, 
    { "label": "Action", "desc": "Include the action of what happend" }, 
    {  "label": "Reason", "desc": "Include the reason for the kick" }, 
    { "label": "Moderator", "desc": "Include the moderator who kicked the user" }
]

AUDIT_EVENTS = {
    "Moderation": [
        {"name": "Ban", "value": "ModerationBan"},
        {"name": "Unban", "value": "ModerationUnban"},
        {"name": "Kick", "value": "ModerationKick"},
        {"name": "Mute", "value": "ModerationMute"},
        {"name": "Unmute", "value": "ModerationUnmute"},
        {"name": "Warn", "value": "ModerationWarn"},
        {"name": "Unwarn", "value": "ModerationUnwarn"},
        {"name": "Message Edited", "value": "MessageEdit"},
        {"name": "Message Deleted", "value": "MessageDelete"},
    ],
    "Server": [
        {"name": "Server Updated", "value": "ServerUpdate"},
        {"name": "Emojis Updated", "value": "ServerEmojis"},
        {"name": "Invite Created", "value": "ServerInviteCreate"},
        {"name": "Invite Deleted", "value": "ServerInviteDelete"},
    ],
    "Roles & Channels": [
        {"name": "Role Updated", "value": "RoleUpdate"},
        {"name": "Role Created", "value": "RoleCreate"},
        {"name": "Role Deleted", "value": "RoleDelete"},
        {"name": "Channel Updated", "value": "ChannelUpdate"},
        {"name": "Channel Created", "value": "ChannelCreate"},
        {"name": "Channel Deleted", "value": "ChannelDelete"},
    ],
    "Members": [
        {"name": "Member Joined", "value": "MemberJoin"},
        {"name": "Member Left", "value": "MemberLeave"},
        {"name": "Member Updated", "value": "MemberUpdate"},
    ],
    "Systems": [
        {"name": "Verification Events", "value": "Verification"},
    ],
}

class ModeratorKickContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['settings']['kick']
        active_dm_options = data.get('dm', [])

        container = Container(color=v.style(guild))
        container.add_text("# Kick Settings")
        container.add_text("Configure options for kicking members.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Private Message")
        container.add_text("Send a private message to the user when they are kicked.")
        class KickMessageSelect(ActionRow):
            @select(
                placeholder="Select DM details to include",
                options=[
                    discord.SelectOption(
                        label=option['label'],
                        description=option['desc'],
                        default=option['label'].lower() in active_dm_options,
                    )
                    for option in PM_OPTIONS
                ],
                min_values=0,
                max_values=len(PM_OPTIONS),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [opt.lower() for opt in select.values]
                save_dash(guild, 'moderation.settings.kick.dm', new_values)

                for option in select.options:
                    option.default = option.label.lower() in new_values

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(KickMessageSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginModeration(guild)))

class ModeratorBanContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['settings']['ban']
        active_dm_options = data.get('dm', [])
        active_purge_days = str(data.get('deleteMessageDays', '0'))

        container = Container(color=v.style(guild))
        container.add_text("# Ban Settings")
        container.add_text("Configure options for banning members.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Private Message ──────────────────────────────────────────────
        container.add_text("## Private Message")
        container.add_text("Send a private message to the user when they are banned.")
        class BanMessageSelect(ActionRow):
            @select(
                placeholder="Select DM details to include",
                options=[
                    discord.SelectOption(
                        label=option['label'],
                        description=option['desc'],
                        default=option['label'].lower() in active_dm_options,
                    )
                    for option in PM_OPTIONS
                ],
                min_values=0,
                max_values=len(PM_OPTIONS),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [opt.lower() for opt in select.values]
                save_dash(guild, 'moderation.settings.ban.dm', new_values)

                for option in select.options:
                    option.default = option.label.lower() in new_values

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BanMessageSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Message Purge ────────────────────────────────────────────────
        container.add_text("## Default Message Purge")
        container.add_text("Select the previous days of messages to purge when a user is banned.")
        class BanPurgeSelect(ActionRow):
            @select(
                placeholder="Select purge duration",
                options=[
                    discord.SelectOption(
                        label=f"{day} Day(s)" if day > 0 else "Don't Delete Any",
                        value=str(day),
                        default=str(day) == active_purge_days,
                    )
                    for day in range(8)
                ],
                min_values=1,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = select.values[0]
                save_dash(guild, 'moderation.settings.ban.deleteMessageDays', new_value)

                for option in select.options:
                    option.default = option.value == new_value

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(BanPurgeSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginModeration(guild)))

class ModeratorMuteContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['settings']['mute']
        active_dm_options = data.get('dm', [])
        active_type = data.get('type', 'timeout').lower()
        active_duration = data.get('duration', '10-min').lower()

        container = Container(color=v.style(guild))
        container.add_text("# Mute Settings")
        container.add_text("Configure options for muting members.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Private Message ──────────────────────────────────────────────
        container.add_text("### Private Message")
        container.add_text("Send a private message to the user when they are muted.")
        class MuteMessageSelect(ActionRow):
            @select(
                placeholder="Select DM details to include",
                options=[
                    discord.SelectOption(
                        label=option['label'],
                        description=option['desc'],
                        default=option['label'].lower() in active_dm_options,
                    )
                    for option in PM_OPTIONS
                ],
                min_values=0,
                max_values=len(PM_OPTIONS),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [opt.lower() for opt in select.values]
                save_dash(guild, 'moderation.settings.mute.dm', new_values)

                for option in select.options:
                    option.default = option.label.lower() in new_values

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MuteMessageSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Mute Type ───────────────────────────────────────────────────
        container.add_text("### Mute Type")
        container.add_text("Select the mechanism to apply when muting.")
        class MuteTypeSelect(ActionRow):
            @select(
                placeholder="Select mute method",
                options=[
                    discord.SelectOption(label="Role", value="role", default=active_type == "role"),
                    discord.SelectOption(label="Timeout", value="timeout", default=active_type == "timeout"),
                ],
                min_values=1,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = select.values[0]
                save_dash(guild, 'moderation.settings.mute.type', new_value)

                for option in select.options:
                    option.default = option.value == new_value

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MuteTypeSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Duration ────────────────────────────────────────────────────
        container.add_text("### Default Mute Duration")
        container.add_text("Select default timeout duration.")
        class MuteTimeSelect(ActionRow):
            time_options = [
                ("60 SEC", "60-sec"),
                ("5 MIN", "5-min"),
                ("10 MIN", "10-min"),
                ("1 HOUR", "1-hour"),
                ("1 DAY", "1-day"),
                ("1 WEEK", "1-week"),
            ]

            @select(
                placeholder="Select duration",
                options=[
                    discord.SelectOption(label=label, value=val, default=val == active_duration)
                    for label, val in time_options
                ],
                min_values=1,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = select.values[0]
                save_dash(guild, 'moderation.settings.mute.duration', new_value)

                for option in select.options:
                    option.default = option.value == new_value

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MuteTimeSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginModeration(guild)))

class ModeratorWarnContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['settings']['warn']
        active_dm_options = data.get('dm', [])

        container = Container(color=v.style(guild))
        container.add_text("# Warn Settings")
        container.add_text("Configure options for warning members.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Private Message")
        container.add_text("Send a private message to the user when they are warned.")

        class WarnMessageSelect(ActionRow):
            @select(
                placeholder="Select DM details to include",
                options=[
                    discord.SelectOption(
                        label=option['label'],
                        description=option['desc'],
                        default=option['label'].lower() in active_dm_options,
                    )
                    for option in PM_OPTIONS
                ],
                min_values=0,
                max_values=len(PM_OPTIONS),
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_values = [opt.lower() for opt in select.values]
                save_dash(guild, 'moderation.settings.warn.dm', new_values)

                for option in select.options:
                    option.default = option.label.lower() in new_values

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(WarnMessageSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginModeration(guild)))

class SelectAuditChannel(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['logging']

        channel_container = Container(color=v.style(guild))
        channel_container.add_text("# Logging Channel")
        channel_container.add_text("Select the channel where audit logs should be sent.")
        channel_container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # Safe channel lookup guard
        current_chan = [
            chan for ch_id in [data.get('channel')]
            if ch_id and (chan := guild.get_channel(int(ch_id))) is not None
        ]

        class SelectAuditChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                min_values=1,
                max_values=1,
                default_values=current_chan,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                save_dash(guild, 'moderation.logging.channel', str(select.values[0].id))
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        channel_container.add_item(SelectAuditChannelSelect())

        self.add_item(channel_container)
        self.add_item(FooterRow(guild, lambda: AuditLoggingContainer(guild)))

class SelectAuditEvents(DesignerView):
    def __init__(self, guild: discord.Guild, active_category: str = "Moderation"):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['logging']
        enabled_events: dict = data.get('events', {})

        container = Container(color=v.style(guild))
        container.add_text("# Audit Event Logging")
        container.add_text("Select a category, then pick which events to log.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Category Selector Dropdown ─────────────────────────────────
        class CategorySelectRow(ActionRow):
            @select(
                placeholder="Choose Event Category...",
                options=[
                    discord.SelectOption(
                        label=cat, 
                        default=cat == active_category
                    ) for cat in AUDIT_EVENTS.keys()
                ],
                min_values=1,
                max_values=1,
            )
            async def callback(self, select_obj: discord.ui.Select, interaction: discord.Interaction):
                chosen_cat = select_obj.values[0]
                await interaction.response.edit_message(view=SelectAuditEvents(guild, active_category=chosen_cat))
        container.add_item(CategorySelectRow())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

        # ── Event Multi-Select Dropdown ────────────────────────────────
        category_events = AUDIT_EVENTS.get(active_category, [])

        class EventMultiSelectRow(ActionRow):
            @select(
                placeholder=f"Configure {active_category} Events...",
                options=[
                    discord.SelectOption(
                        label=evt["name"],
                        value=evt["value"],
                        default=bool(enabled_events.get(evt["value"], False)),
                    ) for evt in category_events
                ],
                min_values=0,
                max_values=len(category_events),
            )
            async def callback(self, select_obj: discord.ui.Select, interaction: discord.Interaction):
                current_events = Guild.get(str(guild.id)).run().dashboard.moderation['logging'].get('events', {})
                
                # Update status for all events in this category
                selected_set = set(select_obj.values)
                for evt in category_events:
                    current_events[evt["value"]] = evt["value"] in selected_set

                # Update options default state visually
                for option in select_obj.options:
                    option.default = option.value in selected_set

                save_dash(guild, 'moderation.logging.events', current_events)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)

        container.add_item(EventMultiSelectRow())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: AuditLoggingContainer(guild)))

class AuditLoggingContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation['logging']

        container = Container(color=v.style(guild))
        container.add_text("# Audit Logging")
        container.add_text("Set a logging channel and choose which events get logged.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class Buttons(ActionRow):
            @button(label="Channel", style=discord.ButtonStyle.gray)
            async def channel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=SelectAuditChannel(guild))

            @button(label="Events", style=discord.ButtonStyle.gray)
            async def events_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=SelectAuditEvents(guild))

            @button(
                label="Don't log bot actions: ON" if data.get('bots', False) else "Don't log bot actions: OFF",
                style=discord.ButtonStyle.green if data.get('bots', False) else discord.ButtonStyle.red,
                custom_id="ignore_bots_toggle",
            )
            async def botlog_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                current = Guild.get(str(guild.id)).run().dashboard.moderation['logging'].get('bots', False)
                new_val = not current

                save_dash(guild, 'moderation.logging.bots', new_val)

                button.label = "Don't log bot actions: ON" if new_val else "Don't log bot actions: OFF"
                button.style = discord.ButtonStyle.green if new_val else discord.ButtonStyle.red

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(Buttons())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginModeration(guild)))

class PluginModeration(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.moderation

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Moderation")
        container.add_text("Keep your server safe with auto-moderation & empower your mods with powerful moderation tools")

        container.add_item(StatusToggle(guild, 'moderation.status', data['status']))

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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