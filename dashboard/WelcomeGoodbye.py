import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, channel_select, role_select
from dashboard._components import save_dash, refresh_footer, FooterRow, StatusToggle

class WelcomeWelcomeContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.welcome

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Welcome")
        container.add_text("Automatically send messages and give roles to your new members")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Welcome Join Toggle ──────────────────────────────────────────
        container.add_text("### Send a message when a user joins the server")
        container.add_item(StatusToggle(guild, 'welcome.join.status', data['join']['status'], custom_id="welcome_toggle"))
        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

        # ── Welcome Message Channel ─────────────────────────────────────
        container.add_text("### Welcome message channel")
        
        # Safe channel lookup (prevents None crash if channel deleted or not set)
        join_chan = [
            chan for ch_id in [data['join'].get('channel')]
            if ch_id and (chan := guild.get_channel(int(ch_id))) is not None
        ]

        class WelcomeChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                default_values=join_chan,
            )
            async def callback(self, select, interaction: discord.Interaction):
                save_dash(guild, 'welcome.join.channel', str(select.values[0].id))
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(WelcomeChannelSelect())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

        # ── Welcome Message Text Modal ──────────────────────────────────
        container.add_text("### Welcome message")
        class WelcomeMessageModal(discord.ui.DesignerModal):
            def __init__(self, parent_view: discord.ui.View):
                self.parent_view = parent_view
                super().__init__(
                    discord.ui.Label(
                        "Message",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.long,
                            value=data['join']['message']['content'],
                        ),
                    ),
                    title="Welcome Message",
                )
            async def callback(self, interaction: discord.Interaction):
                new_content = self.children[0].item.value
                data['join']['message']['content'] = new_content
                save_dash(guild, 'welcome.join.message.content', new_content)
                refresh_footer(self.parent_view, guild)
                await interaction.response.edit_message(view=self.parent_view)
        class WelcomeMessageButton(ActionRow):
            @button(label="Edit message", style=discord.ButtonStyle.primary)
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(WelcomeMessageModal(parent_view=interaction.view))
        container.add_item(WelcomeMessageButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Welcome DM Toggle & Message ─────────────────────────────────
        container.add_text("### Send a private message to new users")
        container.add_item(StatusToggle(guild, 'welcome.dm.status', data['dm']['status'], custom_id="welcome_dm_toggle"))
        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

        container.add_text("### Message")
        class WelcomeDMModal(discord.ui.DesignerModal):
            def __init__(self, parent_view: discord.ui.View):
                self.parent_view = parent_view
                super().__init__(
                    discord.ui.Label(
                        "Message",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.long,
                            value=data['dm']['message']['content'],
                        ),
                    ),
                    title="Welcome DM Message",
                )
            async def callback(self, interaction: discord.Interaction):
                new_content = self.children[0].item.value
                data['dm']['message']['content'] = new_content
                save_dash(guild, 'welcome.dm.message.content', new_content)
                refresh_footer(self.parent_view, guild)
                await interaction.response.edit_message(view=self.parent_view)
        class WelcomeDMMessageButton(ActionRow):
            @button(label="Edit message", style=discord.ButtonStyle.primary)
            async def callback(self, btn, interaction: discord.Interaction):
                await interaction.response.send_modal(WelcomeDMModal(parent_view=interaction.view))
        container.add_item(WelcomeDMMessageButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Welcome Auto Roles ──────────────────────────────────────────
        container.add_text("## Give roles to new users")
        container.add_item(StatusToggle(guild, 'welcome.autoRoles.status', data['autoRoles']['status'], custom_id="welcome_autoRoles_toggle"))
        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)

        container.add_text("### Roles to give")

        # Safe role lookup (prevents None crash if roles deleted)
        auto_roles = [
            role for r_id in data['autoRoles'].get('roles', [])
            if r_id and (role := guild.get_role(int(r_id))) is not None
        ]

        class WelcomeAutoRoleSelect(ActionRow):
            @role_select(
                placeholder="Select roles",
                max_values=min(5, max(1, len(guild.roles))),
                default_values=auto_roles,
            )
            async def callback(self, select, interaction: discord.Interaction):
                save_dash(guild, 'welcome.autoRoles.roles', [str(role.id) for role in select.values])
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(WelcomeAutoRoleSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginWelcomeGoodbye(guild)))

class WelcomeGoodbyeContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.welcome

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Goodbye")
        container.add_text("Automatically send a message when a member leaves your server.")

        container.add_item(StatusToggle(guild, 'welcome.leave.status', data['leave']['status'], custom_id="welcome_goodbye_toggle"))
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Leave Channel ────────────────────────────────────────────────
        container.add_text("### Leave message channel")

        # Safe channel lookup
        leave_chan = [
            chan for ch_id in [data['leave'].get('channel')]
            if ch_id and (chan := guild.get_channel(int(ch_id))) is not None
        ]

        class LeaveChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                default_values=leave_chan,
            )
            async def callback(self, select, interaction: discord.Interaction):
                save_dash(guild, 'welcome.leave.channel', str(select.values[0].id))
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(LeaveChannelSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Leave Message ────────────────────────────────────────────────
        container.add_text("### Send a message when a user leaves the server")
        class LeaveMessageModal(discord.ui.DesignerModal):
            def __init__(self, parent_view: discord.ui.View):
                self.parent_view = parent_view
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
                new_content = self.children[0].item.value
                data['leave']['message']['content'] = new_content
                save_dash(guild, 'welcome.leave.message.content', new_content)
                refresh_footer(self.parent_view, guild)
                await interaction.response.edit_message(view=self.parent_view)

        class LeaveMessageButton(ActionRow):
            @button(
                label="Edit message",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(LeaveMessageModal(parent_view=interaction.view))

        container.add_item(LeaveMessageButton())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginWelcomeGoodbye(guild)))

class PluginWelcomeGoodbye(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.welcome

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Welcome & Goodbye")
        container.add_text("Automatically send messages and give roles to your new members and send a message when a members leaves your server")

        container.add_item(StatusToggle(guild, 'welcome.status', data['status'], custom_id="status"))

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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