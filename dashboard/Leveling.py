import pymongo
import discord
from modules import bot as v
from modules.models import Guild
from discord.ui import DesignerView, Container, ActionRow, button, select, channel_select
from dashboard._components import BackButton, FooterRow, StatusToggle, save_dash, refresh_footer

mongo_cdn_client = pymongo.MongoClient(v.mongo_cdn)
mongoRankCards = mongo_cdn_client['RankCards']['Cards']

GALLERY_ORDER = [
    # Default Colors
    "Blurple", "Yellow", "Red", "Green", "Black", "White", "Fuchsia",
    # Picture Backgrounds
    "BobCat", "BobCat Blob", "Discord Games", "Discord", "Galaxy", "Mountains", "Forest", "Purple Sky"
]

class LevelingLevelingUpContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.leveling

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Leveling Up")
        container.add_text("Whenever the user gains a level, BobCat can send a message.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- SECTION 1: ANNOUNCEMENT LOCATION ---
        container.add_text("## Level Up Announcement")
        class LevelUpSettingSelect(ActionRow):
            @select(
                placeholder="Select a option",
                options=[
                    discord.SelectOption(label="Disabled", value="disabled", default=data['message']['status'] == 'disabled'),
                    discord.SelectOption(label="Current Channel", value="current", default=data['message']['status'] == 'current'),
                    discord.SelectOption(label="Private Message (DM)", value="dm", default=data['message']['status'] == 'dm'),
                    discord.SelectOption(label="Custom Channel", value="custom", default=data['message']['status'] == 'custom'),
                ],
                custom_id="level_up_setting_select",
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                selected_value = select.values[0]

                for option in select.options:
                    option.default = (option.value == selected_value)

                save_dash(guild, 'leveling.message.status', selected_value)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=LevelingLevelingUpContainer(guild))

        container.add_item(LevelUpSettingSelect())

        # --- SECTION 2: CUSTOM ANNOUNCEMENT CHANNEL ---
        container.add_text("### Announcement Channel")
        
        df_value = []
        if data['channel'] and data['message']['status'] == 'custom':
            chan_obj = guild.get_channel(int(data['channel']))
            if chan_obj:
                df_value = [chan_obj]

        class LevelUpChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a custom channel",
                channel_types=[discord.ChannelType.text],
                custom_id="LevelUpChannel",
                default_values=df_value,
                disabled=(data['message']['status'] != 'custom'),
                min_values=0
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                selected_channel = str(select.values[0].id) if select.values else None
                
                save_dash(guild, 'leveling.channel', selected_channel)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=LevelingLevelingUpContainer(guild))

        container.add_item(LevelUpChannelSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- SECTION 3: ANNOUNCEMENT MESSAGE TEMPLATE & PREVIEW ---
        container.add_text("## Level Up Announcement Message")
        container.add_text(
            "> **Available Variables:**\n"
            "> • `{user}` - Mentions the user who leveled up\n"
            "> • `{level}` - The new level reached"
        )
        class LevelUpAnnouncementButton(ActionRow):
            @button(
                label="Edit Announcement Message",
                style=discord.ButtonStyle.primary,
                # emoji="📝"
            )
            async def callback(self, btn, interaction: discord.Interaction):
                MainMenuView = interaction.view
                class LevelUpAnnouncementModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label(
                                "Message Template",
                                discord.ui.InputText(
                                    value=data['message']['content'],
                                    style=discord.InputTextStyle.long,
                                    placeholder="Congratulations {user}, you reached level {level}!",
                                    required=True
                                )
                            ),
                            title="Edit Level Up Message",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        new_message = self.children[0].item.value

                        save_dash(guild, 'leveling.message.content', new_message)
                        refresh_footer(MainMenuView, guild)

                        await interaction.response.edit_message(view=LevelingLevelingUpContainer(guild))
                        await interaction.followup.send("Level up announcement message updated!", ephemeral=True)

                await interaction.response.send_modal(LevelUpAnnouncementModal())
        container.add_item(LevelUpAnnouncementButton())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginLeveling(guild)))

class LevelingServerCardContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.leveling

        DEFAULT_CARDS_URI = "https://i.ibb.co/3mj3F5LL/default-gallery.png"
        FUN_CARDS_URI = "https://i.ibb.co/JRF2c977/fun-gallery.png"

        # Fetch cards from DB
        raw_cards = list(mongoRankCards.find({"theme": {"$in": ["default", "bobcat"]}}))

        # Sort according to GALLERY_ORDER index
        all_cards = sorted(
            raw_cards,
            key=lambda c: GALLERY_ORDER.index(c['card_name']) if c['card_name'] in GALLERY_ORDER else 99
        )

        current_card_id = data.get('card')

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Server Rank Card")
        container.add_text("Customize the default rank card background for all members in your server.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Default Colors")
        default_gallery = discord.ui.MediaGallery()
        default_gallery.add_item(url=DEFAULT_CARDS_URI)
        container.add_item(default_gallery)

        container.add_text("## Picture Backgrounds")
        picture_gallery = discord.ui.MediaGallery()
        picture_gallery.add_item(url=FUN_CARDS_URI)
        container.add_item(picture_gallery)

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        card_options = [
            discord.SelectOption(
                label=card['card_name'],
                value=card['card'],
                default=(current_card_id == card['card'])
            )
            for card in all_cards
        ]
        class ImgSelect(ActionRow):
            @select(
                placeholder="Select a Rank Card Background",
                options=card_options,
                custom_id="img_select",
                select_type=discord.ComponentType.string_select,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                selected_card = select.values[0]

                save_dash(guild, 'leveling.card', selected_card)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=LevelingServerCardContainer(guild))

                card_name = next((c['card_name'] for c in all_cards if c['card'] == selected_card), "Selected Card")
                await interaction.followup.send(f"Updated server rank card to **{card_name}**!", ephemeral=True)

        container.add_item(ImgSelect())
        
        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginLeveling(guild)))

class LevelingRoleRewardsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.leveling

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Role Rewards")
        container.add_text("Role rewards are automatically assigned to users when they reach specific levels.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # Stacking preference
        is_stacked = data['roleRewards'].get('stacked', True)
        class RoleRewardsStackSelect(ActionRow):
            @select(
                placeholder="Stacking Behavior",
                options=[
                    discord.SelectOption(label="Stack rewards", description="Users keep all unlocked reward roles", default=is_stacked),
                    discord.SelectOption(label="Remove rewards", description="Users only keep the highest level reward role", default=not is_stacked),
                ],
                min_values=1,
                max_values=1
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = (select.values[0] == "Stack rewards")
                
                save_dash(guild, 'leveling.roleRewards.stacked', new_value)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=LevelingRoleRewardsContainer(guild))
                await interaction.followup.send(f"Role rewards stacking set to **{'Enabled' if new_value else 'Disabled'}**!", ephemeral=True)
                return
        container.add_item(RoleRewardsStackSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # Add Reward Modal
        class RoleAddRewardModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Level Required",
                        discord.ui.InputText(
                            placeholder="e.g. 5",
                            style=discord.InputTextStyle.short,
                            value="1",
                            required=True,
                        )
                    ),
                    discord.ui.Label(
                        "Role",
                        discord.ui.RoleSelect(
                            select_type=discord.ComponentType.role_select,
                            placeholder="Select a role",
                            required=True
                        )
                    ),
                    title="Add Role Reward",
                )
            async def callback(self, interaction: discord.Interaction):
                try:
                    level = int(self.children[0].item.value)
                except ValueError:
                    return await interaction.response.send_message("Please enter a valid number for the level.", ephemeral=True)

                role = self.children[1].item.values[0]
                guild_role = guild.get_role(role.id)

                if guild_role and guild_role.position >= guild.me.top_role.position:
                    return await interaction.response.send_message(
                        "⚠️ I cannot assign that role because it is higher than or equal to my highest role in the role hierarchy.",
                        ephemeral=True
                    )

                roles = data['roleRewards'].get('roles', [])
                roles.append({'id': str(role.id), 'level': level})
                
                save_dash(guild, 'leveling.roleRewards.roles', roles)
                refresh_footer(interaction.view, guild)

                await interaction.response.edit_message(view=LevelingRoleRewardsContainer(guild))
                await interaction.followup.send(f"Added reward: **Level {level}** -> {role.mention}", ephemeral=True)
        class RoleAddReward(ActionRow):
            @button(
                label="Add Role Reward",
                style=discord.ButtonStyle.primary,
                emoji="➕"
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(RoleAddRewardModal())
        container.add_item(RoleAddReward())

        if not guild.me.guild_permissions.manage_roles:
            container.add_text("⚠️ **Bot Permissions Missing:** Grant me `Manage Roles` or `Administrator` permission to assign roles.")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # List Existing Rewards
        container.add_text("### Active Role Rewards")
        existing_roles = data['roleRewards'].get('roles', [])
        if not existing_roles:
            container.add_text("*No role rewards configured yet.*")
        else:
            for reward in existing_roles:
                role_obj = guild.get_role(int(reward['id']))
                role_mention = role_obj.mention if role_obj else f"*(Deleted Role ID: {reward['id']})*"
                container.add_text(f"• **Level {reward['level']}**: {role_mention}")

        self.add_item(container)
        self.add_item(BackButton(lambda: PluginLeveling(guild)))

class LevelingXpOptionsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.leveling

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# XP Options & Modifiers")
        container.add_text("Fine-tune XP gain rates, blacklists, and system behaviors.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- COOLDOWN ---
        container.add_text("## XP Cooldown")
        class XPCooldownButton(ActionRow):
            @button(
                label="Set Cooldown",
                style=discord.ButtonStyle.primary,
                emoji="⏱️"
            )
            async def callback(self, button, interaction: discord.Interaction):
                MainMenuView = interaction
                class XPCooldownModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label(
                                "Cooldown (seconds)",
                                discord.ui.InputText(
                                    placeholder="Enter seconds (e.g. 60)",
                                    style=discord.InputTextStyle.short,
                                    value=data['cooldown'],
                                    required=True
                                )
                            ),
                            title="Set XP Cooldown",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        try:
                            xpcooldown = int(self.children[0].item.value)
                        except ValueError:
                            return await interaction.response.send_message("Please enter a valid number.", ephemeral=True)

                        save_dash(guild, 'leveling.cooldown', xpcooldown)
                        refresh_footer(MainMenuView.view, guild)

                        await interaction.response.edit_message(view=LevelingXpOptionsContainer(guild))
                        await interaction.followup.send(f"XP Cooldown set to **{xpcooldown} seconds**!", ephemeral=True)
                await interaction.response.send_modal(XPCooldownModal())
        container.add_item(XPCooldownButton())
       
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- NO XP CHANNELS ---
        container.add_text("## No XP Channels")
        container.add_text("Prevent members from gaining XP when sending messages in specific text channels.")

        no_xp_channels = [guild.get_channel(int(ch_id)) for ch_id in data.get('noXP', []) if guild.get_channel(int(ch_id))]

        class NoXpChannelsSelect(ActionRow):
            @channel_select(
                placeholder="Select channels to disable XP",
                channel_types=[discord.ChannelType.text],
                custom_id="noXPChannels",
                default_values=no_xp_channels if no_xp_channels else None,
                max_values=25,
                min_values=0
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                channels: list[discord.TextChannel] = select.values

                save_dash(guild, 'leveling.noXP', [str(ch.id) for ch in channels])
                refresh_footer(interaction.view, guild)

                await interaction.response.edit_message(view=LevelingXpOptionsContainer(guild))
        container.add_item(NoXpChannelsSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- AUTO RESET TOGGLE ---
        auto_reset = data.get('auto_reset', False)
        container.add_text("## Auto Reset on Leave")
        container.add_text("Automatically reset a member's XP and Level if they leave the server.")
        class AutoResetToggle(ActionRow):
            @button(
                label="Enabled" if auto_reset else "Disabled",
                style=discord.ButtonStyle.green if auto_reset else discord.ButtonStyle.red,
            )
            async def callback(self, button, interaction: discord.Interaction):
                new_state = not auto_reset
                save_dash(guild, 'leveling.auto_reset', new_state)
                refresh_footer(interaction.view, guild)

                await interaction.response.edit_message(view=LevelingXpOptionsContainer(guild))
        container.add_item(AutoResetToggle())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        # --- ECONOMY INTEGRATION ---
        economy = data.get('economy', False)
        container.add_text("## Economy Integration")
        container.add_text("Award server coins to users whenever they chat or level up.")
        class EconomyToggle(ActionRow):
            @button(
                label="Enabled" if economy else "Disabled",
                style=discord.ButtonStyle.green if economy else discord.ButtonStyle.red,
            )
            async def callback(self, button, interaction: discord.Interaction):
                new_state = not economy
                save_dash(guild, 'leveling.economy', new_state)
                refresh_footer(interaction.view, guild)

                await interaction.response.edit_message(view=LevelingXpOptionsContainer(guild))
        container.add_item(EconomyToggle())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginLeveling(guild)))

class PluginLeveling(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.leveling

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Leveling")
        container.add_text("Give your members XP and Levels when they send messages")

        container.add_item(StatusToggle(guild, 'leveling.status', data.get('status', False)))

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        class PluginButtons(ActionRow):
            @button(
                label="Message",
                style=discord.ButtonStyle.gray
            )
            async def message_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=LevelingLevelingUpContainer(guild))

            @button(
                label="Server Card",
                style=discord.ButtonStyle.gray
            )
            async def serverCard_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=LevelingServerCardContainer(guild))

            @button(
                label="Role Rewards",
                style=discord.ButtonStyle.gray
            )
            async def roleRewards_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=LevelingRoleRewardsContainer(guild))

            @button(
                label="XP Options & Modifiers",
                style=discord.ButtonStyle.gray
            )
            async def xpOptions_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=LevelingXpOptionsContainer(guild))

        container.add_item(PluginButtons())
        self.add_item(container)