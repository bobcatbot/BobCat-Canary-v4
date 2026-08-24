import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, select, channel_select
from dashboard._components import BackButton, FooterRow, StatusToggle, save_dash, refresh_footer

PRESET_LIMITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 14, 15, 16, 20, 25, 30, 40, 50, 60, 70, 80, 99]
BITRATE_STEPS = [8000, 16000, 32000, 64000, 96000, 128000, 256000, 384000]

def default_hub_data() -> dict:
    return {
        "id": v.uuid(length=12, strCase="upper/lower/nums"),
        "default": True,
        "hub_name": "Hub - Join to create",
        "name": "#{index} - {username}'s Channel",
        "user_limit": 4,
        "bitrate": 64000,
        "category_id": "",
        "channel_id": "",
        "sync_hub_category": False,
        "permissions": {
            "manage_channels": False,
            "manage_permissions": False,
            "priority_speaker": False,
            "move_members": False,
        },
    }

class TempChannelHubEditor(DesignerView):
    def __init__(
        self,
        guild: discord.Guild,
        user: discord.User,
        data: dict | None = None,
        idx: int | None = None,
        page: str = "menu",
    ):
        super().__init__(timeout=None)
        self.guild = guild
        self.user = user
        self.idx = idx
        self.is_new = idx is None

        if data is not None:
            self.data = data
        elif self.is_new:
            self.data = default_hub_data()
        else:
            self.data = Guild.get(str(guild.id)).run().dashboard.temporary_channels["hubs"][idx]

        if page == "hub":
            self._build_hub_page()
        elif page == "settings":
            self._build_settings_page()
        elif page == "permissions":
            self._build_permissions_page()
        else:
            self._build_menu()

    def editor(self, page: str = "menu"):
        return TempChannelHubEditor(
            guild=self.guild,
            user=self.user,
            data=self.data,
            idx=self.idx,
            page=page,
        )

    def save_value(self, key: str, value) -> None:
        current = self.data
        parts = key.split(".")

        for part in parts[:-1]:
            current = current[part]

        current[parts[-1]] = value

        if not self.is_new:
            save_dash(
                self.guild,
                f"temporary_channels.hubs.{self.idx}.{key}",
                value,
            )

    def _add_navigation(self, container: Container):
        editor = self

        class NavigationButtons(ActionRow):
            @button(label="Hub", style=discord.ButtonStyle.gray)
            async def hub(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=editor.editor("hub"))

            @button(label="Settings", style=discord.ButtonStyle.gray)
            async def settings(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=editor.editor("settings"))

            @button(label="Permissions", style=discord.ButtonStyle.gray)
            async def permissions(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=editor.editor("permissions"))

        container.add_item(NavigationButtons())

    def _build_menu(self):
        container = Container(color=discord.Color.embed_background())
        title = "Create New Temporary Channel Hub" if self.is_new else f"{self.data['hub_name']} ({self.data['id']})"
        container.add_text(f"## {title}")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        self._add_navigation(container)
        self.add_item(container)

        if self.is_new:
            editor = self

            class CreateHubButton(ActionRow):
                @button(label="Create", style=discord.ButtonStyle.success)
                async def create(self, btn: discord.ui.Button, interaction: discord.Interaction):
                    if editor.data.get("sync_hub_category"):
                        category_id = editor.data.get("category_id")

                        if category_id:
                            category = editor.guild.get_channel(int(category_id))
                        else:
                            category = await editor.guild.create_category_channel(
                                editor.data["hub_name"],
                                reason=f"Temporary category for hub {editor.data['id']}",
                            )
                            editor.data["category_id"] = str(category.id)
                    else:
                        category = editor.guild

                    channel = await category.create_voice_channel(
                        editor.data["hub_name"],
                        reason=f"Temporary voice channel for hub {editor.data['id']}",
                    )
                    editor.data["channel_id"] = str(channel.id)

                    was_default = editor.data.pop("default", False)
                    hubs = Guild.get(str(editor.guild.id)).run().dashboard.temporary_channels.get("hubs", [])
                    save_dash(editor.guild, f"temporary_channels.hubs.{len(hubs)}", editor.data)

                    message = f"Successfully created hub `{editor.data['id']}`."
                    if was_default:
                        message += "\n\nThe hub was created with default settings."

                    await interaction.response.send_message(message, ephemeral=True)

            self.add_item(CreateHubButton())
        else:
            self.add_item(FooterRow(self.guild, lambda: PluginTempChannels(self.guild)))

    def _build_hub_page(self):
        container = Container(color=discord.Color.embed_background())
        container.add_text("# 🏷️ Main Hub Settings")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        container.add_text("## Hub Name")

        editor = self

        class HubNameModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Hub Name",
                        discord.ui.InputText(
                            value=editor.data["hub_name"],
                            style=discord.InputTextStyle.short,
                            required=True,
                            max_length=32,
                        ),
                    ),
                    title="Edit Hub Name",
                )

            async def callback(self, interaction: discord.Interaction):
                value = self.children[0].item.value
                editor.save_value("hub_name", value)
                await interaction.response.edit_message(view=editor.editor("hub"))
                await interaction.followup.send(f"Updated Hub Name to **{value}**", ephemeral=True)

        class HubNameButton(ActionRow):
            @button(label="Edit Hub Name", style=discord.ButtonStyle.primary, emoji="✏️")
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(HubNameModal())

        container.add_item(HubNameButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        container.add_text("## Channel Naming Template")
        container.add_text("> `{username}` — channel creator\n> `{index}` — temporary channel number")

        class ChannelNameModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Channel Template",
                        discord.ui.InputText(
                            value=editor.data["name"],
                            style=discord.InputTextStyle.short,
                            required=True,
                            max_length=32,
                        ),
                    ),
                    title="Edit Channel Naming Template",
                )

            async def callback(self, interaction: discord.Interaction):
                value = self.children[0].item.value

                try:
                    value.format(index=1, username=editor.user.name)
                except (KeyError, ValueError):
                    return await interaction.response.send_message(
                        "That template contains an invalid variable.",
                        ephemeral=True,
                    )

                editor.save_value("name", value)
                await interaction.response.edit_message(view=editor.editor("hub"))
                await interaction.followup.send(f"Updated template to `{value}`", ephemeral=True)

        class ChannelNameButton(ActionRow):
            @button(label="Edit Channel Template", style=discord.ButtonStyle.primary, emoji="📝")
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_modal(ChannelNameModal())

        container.add_item(ChannelNameButton())
        container.add_text("### Live Preview")

        try:
            preview = self.data["name"].format(index=1, username=self.user.name)
        except (KeyError, ValueError):
            preview = "⚠️ Invalid format variables used!"

        class PreviewButton(ActionRow):
            @button(label=preview[:80], style=discord.ButtonStyle.secondary, disabled=True, emoji="🔊")
            async def callback(self, btn, interaction):
                pass

        container.add_item(PreviewButton())
        self.add_item(container)
        self.add_item(FooterRow(self.guild, lambda: self.editor()))

    def _build_settings_page(self):
        container = Container(color=discord.Color.embed_background())
        container.add_text("# Main Settings")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        editor = self

        current_limit = int(self.data.get("user_limit", 0))
        limits = list(PRESET_LIMITS)

        if current_limit not in limits:
            limits.append(current_limit)

        limits = sorted(set(limits))[:25]

        class UserLimitSelect(ActionRow):
            @select(
                placeholder="Select user limit",
                options=[
                    discord.SelectOption(
                        label="Unlimited (0)" if value == 0 else f"{value} users",
                        value=str(value),
                        default=value == current_limit,
                    )
                    for value in limits
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                value = int(select.values[0])
                editor.save_value("user_limit", value)
                refresh_footer(interaction.view, editor.guild)
                await interaction.response.edit_message(view=editor.editor("settings"))

        container.add_text("## User Limit")
        container.add_item(UserLimitSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        current_bitrate = int(self.data.get("bitrate", 64000))
        rates = [rate for rate in BITRATE_STEPS if rate <= int(self.guild.bitrate_limit)]

        if current_bitrate not in rates and current_bitrate <= int(self.guild.bitrate_limit):
            rates.append(current_bitrate)

        rates = sorted(set(rates))[:25]

        class BitrateSelect(ActionRow):
            @select(
                placeholder="Select bitrate",
                options=[
                    discord.SelectOption(
                        label=f"{rate // 1000} kbps",
                        value=str(rate),
                        default=rate == current_bitrate,
                    )
                    for rate in rates
                ],
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                value = int(select.values[0])
                editor.save_value("bitrate", value)
                refresh_footer(interaction.view, editor.guild)
                await interaction.response.edit_message(view=editor.editor("settings"))

        container.add_text("## Bitrate")
        container.add_item(BitrateSelect())

        if not self.is_new:
            container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
            container.add_text("## ⚠️ Danger Zone")
            container.add_text("Deleting this hub removes its configuration and Discord hub channel.")

            class DeleteHubButton(ActionRow):
                @button(label="Delete Hub", style=discord.ButtonStyle.danger)
                async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                    class ConfirmDelete(discord.ui.View):
                        @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
                        async def confirm(self, btn: discord.ui.Button, inter: discord.Interaction):
                            category_id = editor.data.get("category_id")
                            channel_id = editor.data.get("channel_id")

                            if editor.data.get("sync_hub_category") and category_id:
                                category = editor.guild.get_channel(int(category_id))
                                if category:
                                    await category.delete(reason=f"Hub {editor.data['id']} deleted")
                            elif channel_id:
                                channel = editor.guild.get_channel(int(channel_id))
                                if channel:
                                    await channel.delete(reason=f"Hub {editor.data['id']} deleted")

                            config = Guild.get(str(editor.guild.id)).run()
                            hubs = config.dashboard.temporary_channels.get("hubs", [])
                            hubs.pop(editor.idx)
                            config.dashboard.temporary_channels["hubs"] = hubs
                            config.updated_at = discord.utils.utcnow()
                            config.save()

                            await inter.response.edit_message(
                                content=f"Hub `{editor.data['id']}` has been deleted.",
                                view=None,
                            )

                        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                        async def cancel(self, btn: discord.ui.Button, inter: discord.Interaction):
                            await inter.response.edit_message(content="Cancelled.", view=None)

                    await interaction.response.send_message(
                        "Are you sure? This action cannot be undone.",
                        view=ConfirmDelete(),
                        ephemeral=True,
                    )

            container.add_item(DeleteHubButton())

        self.add_item(container)
        self.add_item(FooterRow(self.guild, lambda: self.editor()))

    def _build_permissions_page(self):
        container = Container(color=discord.Color.embed_background())
        container.add_text("# Permissions")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        editor = self

        sync_enabled = bool(self.data.get("sync_hub_category"))
        category = self.guild.get_channel(int(self.data["category_id"])) if self.data.get("category_id") else None

        class SyncToggle(ActionRow):
            @button(
                label="Enabled" if sync_enabled else "Disabled",
                style=discord.ButtonStyle.green if sync_enabled else discord.ButtonStyle.red,
            )
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                enabled = btn.label == "Disabled"
                editor.save_value("sync_hub_category", enabled)
                refresh_footer(interaction.view, editor.guild)
                await interaction.response.edit_message(view=editor.editor("permissions"))

        container.add_text("## Synchronise permissions with Hub category")
        container.add_item(SyncToggle())

        class CategorySelect(ActionRow):
            @channel_select(
                placeholder="Select a category",
                channel_types=[discord.ChannelType.category],
                min_values=0,
                max_values=1,
                disabled=not sync_enabled,
                default_values=[category] if category else None,
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                value = str(select.values[0].id) if select.values else ""
                editor.save_value("category_id", value)
                refresh_footer(interaction.view, editor.guild)
                await interaction.response.edit_message(view=editor.editor("permissions"))

        container.add_item(CategorySelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        container.add_text("## Owner Permissions")

        permission_meta = [
            ("manage_channels", "Manage Channels", False),
            ("manage_permissions", "Manage Permissions", not self.guild.me.guild_permissions.administrator),
            ("priority_speaker", "Priority Speaker", False),
            ("move_members", "Move Members", False),
        ]

        for permission, label, disabled in permission_meta:
            enabled = bool(self.data["permissions"].get(permission))
            editor_ref = editor

            def make_row(permission_name: str, button_label: str, active: bool, is_disabled: bool):
                class PermissionToggle(ActionRow):
                    @button(
                        label="Enabled" if active else "Disabled",
                        style=discord.ButtonStyle.green if active else discord.ButtonStyle.red,
                        disabled=is_disabled,
                    )
                    async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                        value = btn.label == "Disabled"
                        editor_ref.save_value(f"permissions.{permission_name}", value)
                        refresh_footer(interaction.view, editor_ref.guild)
                        await interaction.response.edit_message(view=editor_ref.editor("permissions"))

                return PermissionToggle()

            container.add_text(f"### {label}")
            container.add_item(make_row(permission, label, enabled, disabled))

        self.add_item(container)
        self.add_item(FooterRow(self.guild, lambda: self.editor()))


class PluginTempChannels(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.temporary_channels

        container = Container(color=discord.Color.embed_background())
        container.add_text("# Temporary Channels")
        container.add_text("Allow members to create temporary voice channels.")
        container.add_item(StatusToggle(guild, "temporary_channels.status", data.get("status", False)))
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CreateHubButton(ActionRow):
            @button(label="New Hub", style=discord.ButtonStyle.primary)
            async def callback(self, btn: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.send_message(
                    view=TempChannelHubEditor(guild, interaction.user),
                    ephemeral=True,
                )

        container.add_item(CreateHubButton())

        hubs = data.get("hubs", [])
        if hubs:
            container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.small)
            container.add_text("## Your Hubs")

            class HubSelect(ActionRow):
                @select(
                    placeholder="Select a hub",
                    options=[
                        discord.SelectOption(label=hub["hub_name"], value=str(index))
                        for index, hub in enumerate(hubs)
                    ],
                )
                async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                    index = int(select.values[0])
                    await interaction.response.edit_message(
                        view=TempChannelHubEditor(
                            guild,
                            interaction.user,
                            idx=index,
                        )
                    )

            container.add_item(HubSelect())
        else:
            container.add_text("*No hubs configured yet.*")

        self.add_item(container)