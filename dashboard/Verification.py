import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, select, channel_select, role_select
from dashboard._components import save_dash, refresh_footer, FooterRow, StatusToggle

BUTTON_STYLES = {
    "gray": discord.ButtonStyle.gray,
    "blurple": discord.ButtonStyle.blurple,
    "green": discord.ButtonStyle.green,
    "red": discord.ButtonStyle.red
}

class MessageModal(discord.ui.DesignerModal):
    def __init__(self, guild: discord.Guild, data: dict, container_view: discord.ui.View):
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
        self.guild = guild
        self.data = data
        self.container_view = container_view

    async def callback(self, interaction: discord.Interaction):
        embed_color = self.children[0].item.value
        embed_title = self.children[1].item.value
        embed_desc = self.children[2].item.value

        old_embed = self.data['message']['embed']
        
        # Check if anything actually changed
        has_changed = (
            embed_color != old_embed.get('color') or
            embed_title != old_embed.get('title') or
            embed_desc != old_embed.get('desc')
        )

        # Update Live Preview
        self.container_view.get_item(100).content = f"# {embed_title}"
        self.container_view.get_item(101).content = f"{embed_desc}"

        # Save field values
        save_dash(self.guild, 'verification.message.embed.color', embed_color)
        save_dash(self.guild, 'verification.message.embed.title', embed_title)
        save_dash(self.guild, 'verification.message.embed.desc', embed_desc)

        # Only invalidate published state if something actually changed
        if has_changed:
            save_dash(self.guild, 'verification.message_published', False)
            pub_btn = self.container_view.get_item("publish_btn")
            if pub_btn:
                pub_btn.label = "Publish Changes"
                pub_btn.style = discord.ButtonStyle.blurple

        refresh_footer(self.container_view, self.guild)
        await interaction.response.edit_message(view=self.container_view)

class EditVerifyButtonModal(discord.ui.DesignerModal):
    def __init__(self, guild: discord.Guild, data: dict, container_view: discord.ui.View):
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
        self.guild = guild
        self.data = data
        self.container_view = container_view

    async def callback(self, interaction: discord.Interaction):
        btn_color = self.children[0].item.values[0]
        btn_emoji = self.children[1].item.value or ""
        btn_title = self.children[2].item.value

        old_btn = self.data['message']['btn']

        # Check if anything actually changed
        has_changed = (
            btn_color != old_btn.get('color') or
            btn_emoji != (old_btn.get('emoji') or "") or
            btn_title != old_btn.get('title')
        )

        # Update Live Preview
        btn = self.container_view.get_item(102)
        btn.label = btn_title
        btn.emoji = btn_emoji or None
        btn.style = BUTTON_STYLES.get(btn_color, discord.ButtonStyle.gray)

        # Save field values
        save_dash(self.guild, 'verification.message.btn.title', btn_title)
        save_dash(self.guild, 'verification.message.btn.emoji', btn_emoji)
        save_dash(self.guild, 'verification.message.btn.color', btn_color)

        # Only invalidate published state if something actually changed
        if has_changed:
            save_dash(self.guild, 'verification.message_published', False)
            pub_btn = self.container_view.get_item("publish_btn")
            if pub_btn:
                pub_btn.label = "Publish Changes"
                pub_btn.style = discord.ButtonStyle.blurple

        refresh_footer(self.container_view, self.guild)
        await interaction.response.edit_message(view=self.container_view)

class VerificationMessage(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.verification
        is_published = data.get('message_published', False)

        container = Container(color=v.style(guild))
        container.add_text("# Verification Message")
        container.add_text("Set the message that will be sent in the verification channel.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Embed Preview")
        container.add_text(f"# {data['message']['embed']['title']}", id=100)
        container.add_text(f"{data['message']['embed']['desc']}", id=101)

        class VerificationButtonPreview(ActionRow):
            @button(
                emoji=data['message']['btn']['emoji'],
                label=data['message']['btn']['title'],
                style=BUTTON_STYLES.get(data['message']['btn']['color'], discord.ButtonStyle.gray),
                disabled=True,
                id=102,
            )
            async def callback(self,b,i):
                pass

        container.add_item(VerificationButtonPreview())
        container.add_text("-# Button is disabled because this is just a preview")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class MessageButton(ActionRow):
            @button(label="Edit message", style=discord.ButtonStyle.primary)
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                current_data = Guild.get(str(guild.id)).run().dashboard.verification
                await interaction.response.send_modal(MessageModal(guild, current_data, interaction.view))
        container.add_item(MessageButton())

        class EditVerifyButton(ActionRow):
            @button(label="Edit Verify Button", style=discord.ButtonStyle.primary)
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                current_data = Guild.get(str(guild.id)).run().dashboard.verification
                await interaction.response.send_modal(EditVerifyButtonModal(guild, current_data, interaction.view))
        container.add_item(EditVerifyButton())

        container.add_separator(divider=False, spacing=discord.SeparatorSpacingSize.large)

        class VerifyButton(ActionRow):
            @button(
                label="Published" if is_published else "Publish",
                style=discord.ButtonStyle.green if is_published else discord.ButtonStyle.gray,
                custom_id="publish_btn"
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if not guild.me.guild_permissions.manage_channels:
                    return await interaction.response.send_message(
                        "I don't have permission to send messages in this server!\nPlease give me 'Manage Channels' and try again.",
                        ephemeral=True
                    )
                if not guild.me.guild_permissions.manage_roles:
                    return await interaction.response.send_message(
                        "I don't have permission to assign roles in this server!\nPlease give me 'Manage Roles' and try again.",
                        ephemeral=True
                    )

                config = Guild.get(str(guild.id)).run().dashboard.verification

                if not config.get('channel'):
                    return await interaction.response.send_message(
                        "Oops! You haven't set a verification channel yet.\nGo to 'Channel & Role' settings.",
                        ephemeral=True
                    )
                if not config.get('role'):
                    return await interaction.response.send_message(
                        "Oops! You haven't set a verification role yet.\nGo to 'Channel & Role' settings.",
                        ephemeral=True
                    )

                channel = guild.get_channel(int(config['channel']))
                role = guild.get_role(int(config['role']))

                if not channel or not role:
                    return await interaction.response.send_message(
                        "The configured channel or role no longer exists in this server.",
                        ephemeral=True
                    )

                try:
                    raw_color = str(config['message']['embed']['color']).replace("#", "")
                    embed_color = int(raw_color, 16)
                except ValueError:
                    embed_color = v.style(guild)

                embed = discord.Embed(
                    title=config['message']['embed']['title'],
                    description=config['message']['embed']['desc'],
                    color=embed_color
                )

                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label=config['message']['btn']['title'],
                    emoji=config['message']['btn']['emoji'] or None,
                    style=BUTTON_STYLES.get(config['message']['btn']['color'], discord.ButtonStyle.gray),
                    custom_id="Verification",
                ))

                if config.get('message_id'):
                    try:
                        msg = await channel.fetch_message(int(config['message_id']))
                        await msg.edit(embed=embed, view=view)

                        save_dash(guild, 'verification.message_published', True)
                        button.label = "Published"
                        button.style = discord.ButtonStyle.gray
                        refresh_footer(interaction.view, guild)
                        await interaction.response.edit_message(view=interaction.view)
                        return await interaction.followup.send_message("Verification message updated!", ephemeral=True)
                    except discord.NotFound:
                        pass  # If message was deleted manually, falls through to resend below

                await channel.set_permissions(guild.default_role, overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=False))
                await channel.set_permissions(role, overwrite=discord.PermissionOverwrite(read_messages=False, send_messages=False))

                try:
                    await guild.default_role.edit(
                        reason="Verification system enabled",
                        permissions=discord.Permissions(read_messages=False)
                    )
                except discord.Forbidden:
                    pass

                try:
                    await role.edit(
                        reason="Verification system enabled",
                        permissions=discord.Permissions(read_messages=True)
                    )
                except discord.Forbidden:
                    pass

                msg = await channel.send(embed=embed, view=view)
                save_dash(guild, 'verification.message_id', str(msg.id))
                save_dash(guild, 'verification.message_published', True)

                button.label = "Published"
                button.style = discord.ButtonStyle.green
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
                await interaction.followup.send_message("Verification message sent!", ephemeral=True)
        container.add_item(VerifyButton())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginVerification(guild)))

class VerificationChanRoleOptions(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.verification

        chan = [
            c for ch_id in [data.get('channel')]
            if ch_id and (c := guild.get_channel(int(ch_id))) is not None
        ]

        role = [
            r for r_id in [data.get('role')]
            if r_id and (r := guild.get_role(int(r_id))) is not None
        ]

        container = Container(color=v.style(guild))
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
            async def callback(self, select_obj: discord.ui.ChannelSelect, interaction: discord.Interaction):
                val = str(select_obj.values[0].id) if select_obj.values else None
                save_dash(guild, 'verification.channel', val)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(ChannelSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("### Verification Role")
        container.add_text("Select the role that will be given to verified members.")
        class RoleSelect(ActionRow):
            @role_select(
                placeholder="Select a role",
                min_values=0,
                max_values=1,
                default_values=role,
            )
            async def callback(self, select_obj: discord.ui.RoleSelect, interaction: discord.Interaction):
                val = str(select_obj.values[0].id) if select_obj.values else None
                save_dash(guild, 'verification.role', val)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(RoleSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginVerification(guild)))

class VerificationGeneralOptions(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.verification

        container = Container(color=v.style(guild))
        container.add_text("# General Verification Options")
        container.add_text("Configure general verification options.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Verification Mode")
        container.add_text("What kind of verification method do you want to use?")

        class ModeSelect(ActionRow):
            @select(
                placeholder="Select an option",
                options=[
                    discord.SelectOption(label="Instant Access", value="instant", default=data.get('mode') == "instant"),
                    discord.SelectOption(label="Captcha (DM)", value="captcha_dm", default=data.get('mode') == "captcha_dm"),
                    discord.SelectOption(label="Captcha (Channel)", value="captcha_channel", default=data.get('mode') == "captcha_channel"),
                ],
                min_values=1,
            )
            async def callback(self, select_obj, interaction: discord.Interaction):
                new_value = select_obj.values[0]

                for option in select_obj.options:
                    option.default = option.value == new_value

                save_dash(guild, 'verification.mode', new_value)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(ModeSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Fail Action")
        container.add_text("What should happen if the verification fails?")
        class FailActionSelect(ActionRow):
            @select(
                options=[
                    discord.SelectOption(label="Keep Unverified", value="unverified", default=data.get('failAction') == "unverified"),
                    discord.SelectOption(label="Kick", value="kick", default=data.get('failAction') == "kick"),
                    discord.SelectOption(label="Ban", value="ban", default=data.get('failAction') == "ban"),
                ],
                placeholder="Select an option",
                min_values=1,
            )
            async def callback(self, select_obj, interaction: discord.Interaction):
                new_value = select_obj.values[0]

                for option in select_obj.options:
                    option.default = option.value == new_value

                save_dash(guild, 'verification.failAction', new_value)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(FailActionSelect())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginVerification(guild)))

class PluginVerification(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.verification

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Verification")
        container.add_text("Verification gate that your new members need to pass in order to get access to your server.")

        container.add_item(StatusToggle(guild, 'verification.status', data.get('status', False)))

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class PluginButtons(ActionRow):
            @button(
                label="Message",
                style=discord.ButtonStyle.gray,
            )
            async def messageBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=VerificationMessage(guild))

            @button(
                label="Channel & Role",
                style=discord.ButtonStyle.gray,
            )
            async def channelBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=VerificationChanRoleOptions(guild))

            @button(
                label="Advanced",
                style=discord.ButtonStyle.gray,
            )
            async def advancedBtn(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=VerificationGeneralOptions(guild))

        container.add_item(PluginButtons())
        self.add_item(container)