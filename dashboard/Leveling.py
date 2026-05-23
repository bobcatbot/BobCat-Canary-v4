import pymongo
import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

mongo_cdn_client = pymongo.MongoClient(v.mongo_cdn)
mongoRankCards = mongo_cdn_client['RankCards']['Cards']

class LevelingLevelingUpContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Leveling Up")
        container.add_text("Whenever the user gains a level, BobCat can send a message.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Level up announcement")

        class LevelUpSettingSelect(ActionRow):
            @select(
                placeholder="Select a option",
                options=[
                    discord.SelectOption(label="Disabled", value="disabled", default=data['message']['status'] == 'disabled'),
                    discord.SelectOption(label="Current Channel", value="current", default=data['message']['status'] == 'current'),
                    discord.SelectOption(label="Private Message", value="dm", default=data['message']['status'] == 'dm'),
                    discord.SelectOption(label="Custom Channel", value="custom", default=data['message']['status'] == 'custom'),
                ],
                custom_id="level_up_setting_select",
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                settingSelect: discord.ui.Select = container.get_item("level_up_setting_select")
                
                if select.values[0] == "custom":
                    for option in settingSelect.options:
                        option.default = False
                    
                    settingSelect.options[3].default = True
                    
                    lvlupChannelSelect = container.get_item("LevelUpChannel")
                    lvlupChannelSelect.disabled = False

                    v.db.update_dash(guild, 'leveling.message.status', select.values[0])
                    v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                    return await interaction.response.edit_message(view=interaction.view)

                selected_value = select.values[0]

                # Reset all defaults
                for option in settingSelect.options:
                    option.default = False

                # Apply new default
                for option in settingSelect.options:
                    if option.value == selected_value:
                        option.default = True

                v.db.update_dash(guild, 'leveling.message.status', selected_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                if selected_value != "custom": # Disable channel select if not custom
                    lvlupChannelSelect = container.get_item("LevelUpChannel")
                    lvlupChannelSelect.disabled = True

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(LevelUpSettingSelect())
        
        container.add_text("Announcement Channel")
        
        df_value = []
        if data['channel'] != None and data['message']['status'] == 'custom':
            df_value = [ guild.get_channel(int(data['channel'])) ]

        class LevelUpChannelSelect(ActionRow):
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
                custom_id="LevelUpChannel",
                default_values=df_value,
                disabled=False if data['message']['status'] == 'custom' else True,
                min_values=0
            )
            async def callback(self, select: discord.ui.ChannelSelect, interaction: discord.Interaction):
                chan: discord.TextChannel = select.values[0]

                v.db.update_dash(guild, 'leveling.channel', str(chan.id))
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                await interaction.response.edit_message(view=interaction.view)
        container.add_item(LevelUpChannelSelect())

        container.add_text("Level Up Announcement Message")
        
        class LevelUpAnnouncementModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Message (Use {user} for mention, {level} for new level)",
                        discord.ui.InputText(
                            placeholder="Congratulations {user}, you just reached level {level}!",
                            style=discord.InputTextStyle.paragraph,
                            value=data['message']['content'],
                            required=True,
                        )
                    ),
                    title="Level Up Announcement Message",
                )
            async def callback(self, interaction: discord.Interaction):
                message = self.children[0].item.value

                v.db.update_dash(guild, 'leveling.message.content', message)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.send_message("Level up announcement message updated!", ephemeral=True)

        class LevelUpAnnouncementButton(ActionRow):
            @button(
                label="Edit Announcement Message",
                style=discord.ButtonStyle.gray,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(LevelUpAnnouncementModal())
            
        container.add_item(LevelUpAnnouncementButton())
        
        self.add_item(container)

        class GoBackButton(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))
        self.add_item(GoBackButton())

class LevelingServerCardContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        DEFAULT_CARDS_URI = "https://i.postimg.cc/J4jxTTT8/defaul-gallery.png"
        FUN_CARDS_URI = "https://i.postimg.cc/jdyc888R/fun-gallery.png"

        default_cards = [
            card
            for card in mongoRankCards.find({"theme": "default"}).sort("theme", pymongo.ASCENDING)
        ]
        fun_cards = [
            card
            for card in mongoRankCards.find({"theme": "bobcat"}).sort("theme", pymongo.ASCENDING)
        ]

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Server Card")
        container.add_text("You can customize the default /rank card in your server. Every member of your server will have that rank card.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Default Colors")
        default_gallery = discord.ui.MediaGallery()
        default_gallery.add_item(
            url=DEFAULT_CARDS_URI,
        )
        container.add_item(default_gallery)

        container.add_text("## Picture Backgrounds")
        picture_gallery = discord.ui.MediaGallery()
        picture_gallery.add_item(
            url=FUN_CARDS_URI,
        )
        container.add_item(picture_gallery)

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ImgSelect(ActionRow):
            defc = [ 
                discord.SelectOption(label=f"{option['card_name']}", value=option['card'], default=data['card'] == option['card']) for option in default_cards
            ]
            func = [
                discord.SelectOption(label=f"{option['card_name']}", value=option['card'], default=data['card'] == option['card']) for option in fun_cards
            ]
            @select(
                placeholder="Select an Image",
                options=defc + func,
                custom_id="img_select",
                disabled=False,
                select_type=discord.ComponentType.string_select,
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                selected_card = select.values[0]
                print(selected_card)

                v.db.update_dash(guild, 'leveling.card', selected_card)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                # Reset all defaults
                for option in select.options:
                    option.default = False

                # Apply new default
                for option in select.options:
                    if option.value == selected_card:
                        option.default = True

                await interaction.response.edit_message(view=interaction.view)

                card = [ option['card_name'] for option in default_cards + fun_cards if option['card'] == selected_card ][0]
                await interaction.followup.send(f"Updated your rank card to {card}!", ephemeral=True)
        container.add_item(ImgSelect())

        self.add_item(container)

        class GoBackButton(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))
        self.add_item(GoBackButton())

class LevelingRoleRewardsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Role Rewards")
        container.add_text("Role Rewards are given to users when they hit the respective level.")
        container.add_text("when checked users can have multiple rewards at once but the highest reward will be given. when unchecked only the highest reward will be given and the previous rewards will be removed")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class RoleRewardsStackSelect(ActionRow):
            @select(
                placeholder="Stack or Remove Rewards",
                options=[
                    discord.SelectOption(label="Stack rewards", description="Users can have multiple rewards at once", default=True if data['roleRewards']['stacked'] == True else False),
                    discord.SelectOption(label="Remove rewards", description="Users can only have the highest reward", default=True if data['roleRewards']['stacked'] == False else False),
                ],
                min_values=1,
                max_values=1
            )
            async def callback(self, select: discord.ui.Select, interaction: discord.Interaction):
                new_value = True if select.values[0] == "Stack rewards" else False
                
                v.db.update_dash(guild, 'leveling.roleRewards.stacked', new_value)
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.send_message(view=interaction.view)

                await interaction.followup.send(f"Role rewards updated to {select.values[0].split(' ')[0]}!", ephemeral=True)
        container.add_item(RoleRewardsStackSelect())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class RoleAddRewardModal(discord.ui.DesignerModal):
            def __init__(self):
                lvlselect = discord.ui.Label(
                    "Level",
                    discord.ui.InputText(
                        placeholder="Select a number for level",
                        style=discord.InputTextStyle.short,
                        value="1",
                        required=True,
                    )
                )
                roleselect = discord.ui.Label(
                    "Role",
                    discord.ui.RoleSelect(
                        select_type=discord.ComponentType.role_select,
                        placeholder="Select a role",
                        required=True
                    )
                )
                super().__init__(
                    lvlselect,
                    roleselect,
                    title="Add Role Reward",
                )
            async def callback(self, interaction: discord.Interaction):
                level = self.children[0].item.value
                role = self.children[1].item.values[0]

                guild_role = guild.get_role(role.id)

                if guild_role.position > guild.me.top_role.position:
                    return await interaction.response.send_message("Whoops, I can't assign that role as it is higher than my highest role. Please change the role position in your server settings.", ephemeral=True)
                
                roles = data['roleRewards']['roles']
                roles.append({ 'id': str(role.id), 'level': int(level) })
                v.db.update_dash(guild, 'leveling.roleRewards.roles', roles)

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.send_message(f"Role rewards updated!\n**Level:** {self.children[0]}\n**Role:** {self.children[1]}")
        class RoleAddReward(ActionRow):
            @button(
                label="Add Role Reward",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(RoleAddRewardModal())
        container.add_item(RoleAddReward())

        if guild.me.guild_permissions.manage_roles == False:
            container.add_text("Whoops, it looks like I can't give any roles. Please fix that by giving me the MANAGE ROLES or ADMINISTRATOR permissions.")

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        for reward in data['roleRewards']['roles']:
            container.add_text(f"**Level:** {reward['level']}\n**Role:** {guild.get_role(int(reward['id'])).mention}")
            container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class LevelingXpOptionsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# XP Options & Modifiers")
        container.add_text("Customize the other options of the XP system.")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## No XP Channels")
        container.add_text("Prevent your members from gaining XP if they send messages in certain text channels.")

        class NoXpChannelsSelect(ActionRow): # TODO: make this work
            @channel_select(
                placeholder="Select a channel",
                channel_types=[discord.ChannelType.text],
            )
            async def callback(self, select, interaction: discord.Interaction):
                await interaction.response.defer()
                await interaction.followup.send(f"You selected {select.values[0].name}")
        container.add_item(NoXpChannelsSelect())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Auto Reset")
        container.add_text("Should the bot reset user's level and XP if they leave the server?")
        class AutoResetToggle(ActionRow):
            @button(
                label="Disabled" if data['auto_reset'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['auto_reset'] == False else discord.ButtonStyle.green,
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'leveling.auto_reset', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'leveling.auto_reset', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("update_at")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(AutoResetToggle())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Economy Integration")
        container.add_text("Each time a user sends a message or levels up they gain coins.")
        class EconomyToggle(ActionRow):
            @button(
                label="Disabled" if data['economy'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['economy'] == False else discord.ButtonStyle.green,
            )
            async def callback(self, button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'leveling.economy', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'leveling.economy', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red
                
                v.db.update_server_config(guild, True, 'updated_at', discord.utils.utcnow())

                update_at = interaction.view.get_item("update_at")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(EconomyToggle())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginLeveling(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class PluginLeveling(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['leveling']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Leveling")
        container.add_text("Give your members XP and Levels when they send messages")

        class StatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
                custom_id="status",
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild, 'leveling.status', True)
                    
                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild, 'leveling.status', False)

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


# options=[
#     discord.SelectOption(label="Level Message", description="Send a message when a user levels up"),
#     discord.SelectOption(label="Server Card", description="Reply with a card when they use the /rank command"),
#     discord.SelectOption(label="Role Rewards", description="Give roles to users when they hit certain levels"),
#     discord.SelectOption(label="XP Options & Modifiers", description="Customize other XP options"),
# ],