import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, role_select
from dashboard._components import FooterRow, BackButton, refresh_footer

def get_settings(guild: discord.Guild | int) -> dict:
    guild_id = guild.id if isinstance(guild, discord.Guild) else int(guild)
    return Guild.get(str(guild_id)).run().settings

def save_setting(guild: discord.Guild | int, key: str, value) -> bool:
    guild_id = guild.id if isinstance(guild, discord.Guild) else int(guild)
    config = Guild.get(str(guild_id)).run()

    if config is None:
        return False

    current = config.settings
    parts = key.split('.')

    for part in parts[:-1]:
        current = current.setdefault(part, {})

    current[parts[-1]] = value
    config.updated_at = discord.utils.utcnow()
    config.save()
    return True

class BotSettingsMastersAndAdmins(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = get_settings(guild)

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Bot Masters & Admins")
        container.add_text("Here you can adjust the bot's permission settings.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Administrator Roles ──────────────────────────────────────────
        container.add_text("## Administrator Roles")
        container.add_text("Any role with the Administrator permission is considered a bot master.")
        
        # Safely filter out deleted roles (None)
        admin_roles = [
            role for role_id in data.get('admin_roles', []) 
            if (role := guild.get_role(int(role_id))) is not None
        ]

        class AdminsSelect(ActionRow):
            @role_select(
                placeholder="Select roles",
                max_values=max(1, len(guild.roles)),
                default_values=admin_roles,
            )
            async def select(self, select: discord.ui.RoleSelect, interaction: discord.Interaction):
                role_ids = [str(role.id) for role in select.values]
                save_setting(guild, "admin_roles", role_ids)

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)

        container.add_item(AdminsSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # ── Additional Bot Master Roles ─────────────────────────────────
        container.add_text("## Additional Bot Master Roles")
        container.add_text("Roles considered as bot masters without requiring Administrator permission.")

        master_roles = [
            role for role_id in data.get('bot_masters', []) 
            if (role := guild.get_role(int(role_id))) is not None
        ]

        class MastersSelect(ActionRow):
            @role_select(
                placeholder="Select roles",
                max_values=max(1, len(guild.roles)),
                default_values=master_roles,
            )
            async def select(self, select: discord.ui.RoleSelect, interaction: discord.Interaction):
                role_ids = [str(role.id) for role in select.values]
                save_setting(guild, "bot_masters", role_ids)

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(MastersSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginBotSettings(guild)))

class BotSettingsColor(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = get_settings(guild)

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Color")
        container.add_text("The accent color for bot embeds across this server.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ColorModal(discord.ui.DesignerModal):
            def __init__(self, parent_view: discord.ui.View):
                self.parent_view = parent_view
                super().__init__(
                    discord.ui.Label(
                        "Color Hex Code",
                        discord.ui.InputText(
                            style=discord.InputTextStyle.short,
                            value=data.get('color', '#5865F2'),
                        )
                    ),
                    title="Change Bot Color",
                )
            async def callback(self, interaction: discord.Interaction):
                color = self.children[0].item.value
                save_setting(interaction.guild, "color", color)

                refresh_footer(self.parent_view, interaction.guild)
                await interaction.response.edit_message(view=self.parent_view)

        class ColorButton(ActionRow):
            @button(
                label="Change Color",
                style=discord.ButtonStyle.primary,
            )
            async def changeColor(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(ColorModal(parent_view=interaction.view))

        container.add_item(ColorButton())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginBotSettings(guild)))

class BotSettingsOptions(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Other options")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Language")
        container.add_text("Change the default language of the bot in your server. *(Work in progress)*")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Timezone")
        container.add_text("Change the default timezone of the bot in your server. *(Work in progress)*")

        self.add_item(container)
        self.add_item(BackButton(lambda: PluginBotSettings(guild)))

class PluginBotSettings(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Settings")
        container.add_text("Configure server-wide options and permissions for the bot.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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