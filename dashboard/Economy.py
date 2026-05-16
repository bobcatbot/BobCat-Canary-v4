import discord
from datetime import datetime
from modules import bot as v
from discord.ui import (
    DesignerView, Container, ActionRow, button, select, channel_select, role_select
)

class EconomyCustomizeCoinsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Customize your currency")
        container.add_text("Customize your currency icon and name")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CoinModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Currency Icon
                        "Currency Icon",
                        discord.ui.InputText(
                            placeholder="Currency icon here...",
                            value=f"{data['icon']}",
                            style=discord.InputTextStyle.short,
                        ),
                        description="Only use default emojis or Discord emojis ( <:EMOJI_NAME:EMOJI_ID> )",
                    ),
                    discord.ui.Label( # Currency Name
                        "Currency Name",
                        discord.ui.InputText(
                            placeholder="Currency name here...",
                            value=f"{data['name']}",
                            style=discord.InputTextStyle.short,
                        ),
                        description="Your currency name will be displayed in the currency shop and in the currency leaderboard",
                    ),
                    title="Customize Your Currency Name and Icon",
                )
            async def callback(self, interaction: discord.Interaction):
                newCoinIcon = self.children[0].item.value
                newCoinName = self.children[1].item.value
                
                v.db.update_dash(guild.id, 'economy.icon', newCoinIcon)
                v.db.update_dash(guild.id, 'economy.name', newCoinName)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        
        class CustomizeCoinButton(ActionRow):
            @button(
                label="Edit currency icon and name",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(CoinModal())
        container.add_item(CustomizeCoinButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def go_back(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class EconomyShopContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']
        shop_items: list = data["shop"]
        
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Shop Items")
        container.add_text("Customize the items in your shop")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ShopModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Item Icon
                        "Item Icon",
                        discord.ui.InputText(
                            placeholder="Item icon here...",
                            value="🪙",
                            style=discord.InputTextStyle.short,
                        ),
                        description="Only use default emojis or Discord emojis ( <:EMOJI_NAME:EMOJI_ID> )",
                    ),
                    discord.ui.Label( # Item Name
                        "Item Name",
                        discord.ui.InputText(
                            placeholder="Item name here...",
                            value="BobCat Coin",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    discord.ui.Label( # Item Price
                        "Item Price",
                        discord.ui.InputText(
                            placeholder="Item price here...",
                            value="100",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    discord.ui.Label( # Item Description
                        "Item Description",
                        discord.ui.InputText(
                            placeholder="Item description here...",
                            value="",
                            style=discord.InputTextStyle.long,
                            required=False
                        )
                    ),
                    discord.ui.Label( # Item Max Limit
                        "Max amount per player",
                        discord.ui.InputText(
                            placeholder="Item limit here...",
                            value="5",
                            style=discord.InputTextStyle.short,
                            required=False
                        ),
                    ),
                    # discord.ui.Label( "Type", discord.ui.Select(placeholder="Select an option", options=[ discord.SelectOption(label="Usable Item", default=True), discord.SelectOption(label="Role") ]) ) # Item Type
                    title="Create a shop item",
                )
            async def callback(self, interaction: discord.Interaction):
                newItem = {
                    "icon": self.children[0].item.value, 
                    "name": self.children[1].item.value, 
                    "price": self.children[2].item.value, 
                    "description": self.children[3].item.value, 
                    "max_limit": self.children[4].item.value,
                    "type": "usable-item"
                }
                
                shop_items.append(newItem)

                v.db.update_dash(guild.id, 'shop', shop_items)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                # update the main container view
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                container.add_text(f"**{newItem['name']}**  Max: {newItem['max_limit']}")
                container.add_text(f"{newItem['icon']}")
                container.add_text(f"{newItem['price']} {data['icon']}")
                
                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=container.view)
        class CustomizeShopButton(ActionRow):
            @button(
                label="Add Shop Item",
                style=discord.ButtonStyle.primary,
                disabled=True if len(shop_items) >= 5 else False,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(ShopModal())
        container.add_item(CustomizeShopButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        for index, item in enumerate(shop_items):
            container.add_text(f"**{item['name']}**  Max: {item['max_limit']}")
            container.add_text(f"{item['icon']}")
            container.add_text(f"{item['price']} {data['icon']}")
            
            # Only show separator if NOT the last item
            if index != len(shop_items) - 1:
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
        
        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class EconomyRestrictionsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Restrictions")
        container.add_text("Handle game restrictions for all games in one place")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Max Gambling")
        class MaxGamblingModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Max Gambling
                        "Max Gambling",
                        discord.ui.InputText(
                            placeholder="",
                            value=f"{data['MaxGambling']}",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    title="Edit your max gambling amount",
                )
            async def callback(self, interaction: discord.Interaction):
                maxGambling = self.children[0].item.value

                v.db.update_dash(guild.id, 'economy.MaxGambling', maxGambling)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        class CustomizeMaxGamblingButton(ActionRow):
            @button(
                label="Edit Max Gambling",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(MaxGamblingModal())
        container.add_item(CustomizeMaxGamblingButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Max Payment")
        class MaxPaymentModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label( # Max Payment
                        "Max Payment",
                        discord.ui.InputText(
                            placeholder="",
                            value=f"{data['MaxPayment']}",
                            style=discord.InputTextStyle.short,
                        ),
                    ),
                    title="Edit your max Payment amount",
                )
            async def callback(self, interaction: discord.Interaction):
                maxPayment = self.children[0].item.value

                v.db.update_dash(guild.id, 'economy.MaxPayment', maxPayment)
                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                update_at = container.view.get_item("SaveSuccess")
                update_at.label = f"Updated at: {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M')}"
                await interaction.response.edit_message(view=interaction.view)
        class CustomizeMaxPaymentButton(ActionRow):
            @button(
                label="Edit Max Payment",
                style=discord.ButtonStyle.primary,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(MaxPaymentModal())
        container.add_item(CustomizeMaxPaymentButton())

        self.add_item(container)

        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))

            @button(
                label=f"Updated at: {datetime.fromisoformat(str(v.db.get_server_config(guild.id, True)['updated_at'])).strftime('%Y-%m-%d %H:%M')}",
                style=discord.ButtonStyle.gray,
                custom_id="SaveSuccess",
                disabled=True,
            )
            async def updateStatus(self, button, interaction):
                pass
        self.add_item(ViewButtons())

class EconomyResetContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Reset Economy")
        container.add_text("This will remove all the coins or shop items from your users")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ResetEconomyButton(ActionRow):
            @button(
                label="Reset Economy coins",
                style=discord.ButtonStyle.red,
            )
            async def ResetEcoCoins(self, button, interaction: discord.Interaction):
                class ConfirmResetEcoCoins(discord.ui.View):
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True
                        await interaction.response.edit_message(content="Reset cancelled.", view=self)
                    
                    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red)
                    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True

                        users = v.db.get_server_config(guild.id)['economy']
                        for user in users:
                            users[user]['wallet'] = 0
                            users[user]['bank'] = 0
                            users[user]['bag'] = []
                            v.db.update_server_config(guild.id, False, 'economy', users)
                        
                        v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())

                        await interaction.response.edit_message(content="Economy coins have been reset.", view=self)
                await interaction.response.send_message(f"This action is strictly irreversible! Everyone will lose their coins.", view=ConfirmResetEcoCoins(), ephemeral=True)
            
            @button(
                label="Reset Economy shop",
                style=discord.ButtonStyle.red,
            )
            async def resetecoshop(self, button, interaction: discord.Interaction):
                class ConfirmResetEcoShop(discord.ui.View):
                    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
                    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True
                        await interaction.response.edit_message(content="Reset cancelled.", view=self)
                    
                    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red)
                    async def confirm(self, button: discord.ui.Button, interaction: discord.Interaction):
                        for child in self.children:
                            child.disabled = True

                        shop = [
                            {"name": "Teddy", "price": 50, "icon": "🧸", "description": "Very sot cuddly teddy bear", "type": "string", "max_limit": 5},
                            {"name": "Watch", "price": 100, "icon": "⌚", "description": "A thing to tell the time", "type": "string", "max_limit": 5},
                            {"name": "Phone", "price": 500, "icon": "📱", "description": "A phone", "type": "string", "max_limit": 5},
                            {"name": "Laptop", "price": 1000, "icon": "💻", "description": "A nice laptop for work and play", "type": "string", "max_limit": 5},
                        ]
                        v.db.update_dash(guild.id, 'economy.shop', shop)

                        v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())
                        
                        await interaction.response.edit_message(content="Economy shop has been reset.", view=self)
                await interaction.response.send_message(f"This action is strictly irreversible! The economy shop will be reset back to default.", view=ConfirmResetEcoShop(), ephemeral=True)
        container.add_item(ResetEconomyButton())

        self.add_item(container)
        
        class ViewButtons(ActionRow):
            @button(
                label="Go Back",
                style=discord.ButtonStyle.primary,
            )
            async def goBack(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=PluginEconomy(guild))
        self.add_item(ViewButtons())

class PluginEconomy(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = v.db.get_dash(guild.id)['economy']

        container = Container(
            color=v.style(guild),
        )
        container.add_text("# Economy")
        container.add_text("Players can gain coins once a day. A player can stake their coins at games. Use your coins to buy items from the shop.")
        
        class EconomyStatusButton(ActionRow):
            @button(
                label="Disabled" if data['status'] == False else "Enabled",
                style=discord.ButtonStyle.red if data['status'] == False else discord.ButtonStyle.green,
            )
            async def callback(self, button: discord.ui.Button, interaction: discord.Interaction):
                if button.label == "Disabled":
                    v.db.update_dash(guild.id, 'economy.status', True)

                    button.label = "Enabled"
                    button.style = discord.ButtonStyle.green
                else:
                    v.db.update_dash(guild.id, 'economy.status', False)

                    button.label = "Disabled"
                    button.style = discord.ButtonStyle.red

                v.db.update_server_config(guild.id, True, 'updated_at', discord.utils.utcnow())
                await interaction.response.edit_message(view=interaction.view)
        container.add_item(EconomyStatusButton())

        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("**Configure**")

        class PluginButtons(ActionRow):
            @button(
                label="Customization",
                style=discord.ButtonStyle.gray,
            )
            async def coin_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=EconomyCustomizeCoinsContainer(guild))

            @button(
                label="Shop",
                style=discord.ButtonStyle.gray,
            )
            async def shop_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=EconomyShopContainer(guild))

            @button(
                label="Restrictions",
                style=discord.ButtonStyle.gray,
            )
            async def restrictions_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=EconomyRestrictionsContainer(guild))

            @button(
                label="Reset Economy",
                style=discord.ButtonStyle.gray,
            )
            async def reset_callback(self, button, interaction: discord.Interaction):
                await interaction.response.edit_message(view=EconomyResetContainer(guild))
        
        container.add_item(PluginButtons())

        self.add_item(container)
