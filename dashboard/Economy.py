import discord
from modules import bot as v
from modules.models import Guild, Economy
from discord.ui import DesignerView, Container, ActionRow, button
from dashboard._components import BackButton, FooterRow, StatusToggle, save_dash, refresh_footer

from cogs.money.tools.utils import mainshop

class EconomyCustomizeCoinsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.economy

        container = Container(color=v.style(guild))
        container.add_text("# Customize your currency")
        container.add_text("Customize your currency icon and name")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class CustomizeCoinButton(ActionRow):
            @button(label="Edit currency icon and name", style=discord.ButtonStyle.primary)
            async def callback(self, button, interaction: discord.Interaction):
                MainMenuView = interaction
                class CoinModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label(
                                "Currency Icon",
                                discord.ui.InputText(
                                    placeholder="Currency icon here...",
                                    value=f"{data['icon']}",
                                    style=discord.InputTextStyle.short,
                                ),
                                description="Only use default emojis or Discord emojis ( <:EMOJI_NAME:EMOJI_ID> )",
                            ),
                            discord.ui.Label(
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
                        icon = self.children[0].item.value
                        name = self.children[1].item.value

                        save_dash(guild.id, 'economy.icon', icon)
                        save_dash(guild.id, 'economy.name', name)

                        refresh_footer(MainMenuView.view, guild)
                        await interaction.response.edit_message(view=EconomyCustomizeCoinsContainer(guild))

                await interaction.response.send_modal(CoinModal())

        container.add_item(CustomizeCoinButton())

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginEconomy(guild)))

class EconomyShopContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.economy
        shop_items: list = data["shop"]

        container = Container(color=v.style(guild))
        container.add_text("# Shop Items")
        container.add_text("Customize the items in your shop")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ShopModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label(
                        "Item Icon",
                        discord.ui.InputText(placeholder="Item icon here...", value="🪙", style=discord.InputTextStyle.short),
                        description="Only use default emojis or Discord emojis ( <:EMOJI_NAME:EMOJI_ID> )",
                    ),
                    discord.ui.Label("Item Name", discord.ui.InputText(placeholder="Item name here...", value="BobCat Coin", style=discord.InputTextStyle.short)),
                    discord.ui.Label("Item Price", discord.ui.InputText(placeholder="Item price here...", value="100", style=discord.InputTextStyle.short)),
                    discord.ui.Label("Item Description", discord.ui.InputText(placeholder="Item description here...", value="", style=discord.InputTextStyle.long, required=False)),
                    discord.ui.Label("Max amount per player", discord.ui.InputText(placeholder="Item limit here...", value="5", style=discord.InputTextStyle.short, required=False)),
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
                save_dash(guild.id, 'economy.shop', shop_items)

                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)
                container.add_text(f"**{newItem['name']}**  Max: {newItem['max_limit']}")
                container.add_text(f"{newItem['icon']}")
                container.add_text(f"{data['icon']} {newItem['price']}")

                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=EconomyShopContainer(guild))

        class CustomizeShopButton(ActionRow):
            @button(
                label="Add Shop Item",
                style=discord.ButtonStyle.primary,
                disabled=len(shop_items) >= 5,
            )
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(ShopModal())

        container.add_item(CustomizeShopButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        for index, item in enumerate(shop_items):
            container.add_text(f"**{item['name']}**  Max: {item['max_limit']}")
            container.add_text(f"{item['icon']}")
            container.add_text(f"{data['icon']} {item['price']}")
            
            if index != len(shop_items) - 1:
                container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginEconomy(guild)))

class EconomyRestrictionsContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.economy

        container = Container(color=v.style(guild))
        container.add_text("# Restrictions")
        container.add_text("Handle game restrictions for all games in one place")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Max Gambling")
        class CustomizeMaxGamblingButton(ActionRow):
            @button(label="Edit Max Gambling", style=discord.ButtonStyle.primary)
            async def callback(self, button, interaction: discord.Interaction):
                MainMenuView = interaction
                class MaxGamblingModal(discord.ui.DesignerModal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.Label("Max Gambling", discord.ui.InputText(placeholder="", value=f"{data['MaxGambling']}", style=discord.InputTextStyle.short)),
                            title="Edit your max gambling amount",
                        )

                    async def callback(self, interaction: discord.Interaction):
                        save_dash(guild.id, 'economy.MaxGambling', self.children[0].item.value)
                        refresh_footer(MainMenuView.view, guild)

                await interaction.response.send_modal(MaxGamblingModal())

        container.add_item(CustomizeMaxGamblingButton())
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        container.add_text("## Max Payment")
        class MaxPaymentModal(discord.ui.DesignerModal):
            def __init__(self):
                super().__init__(
                    discord.ui.Label("Max Payment", discord.ui.InputText(placeholder="", value=f"{data['MaxPayment']}", style=discord.InputTextStyle.short)),
                    title="Edit your max Payment amount",
                )

            async def callback(self, interaction: discord.Interaction):
                save_dash(guild.id, 'economy.MaxPayment', self.children[0].item.value)
                refresh_footer(interaction.view, guild)
                await interaction.response.edit_message(view=EconomyRestrictionsContainer(guild))

        class CustomizeMaxPaymentButton(ActionRow):
            @button(label="Edit Max Payment", style=discord.ButtonStyle.primary)
            async def callback(self, button, interaction: discord.Interaction):
                await interaction.response.send_modal(MaxPaymentModal())

        container.add_item(CustomizeMaxPaymentButton())
        self.add_item(container)
        self.add_item(FooterRow(guild, lambda: PluginEconomy(guild)))

class EconomyResetContainer(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        container = Container(color=v.style(guild))
        container.add_text("# Reset Economy")
        container.add_text("This will remove all the coins or shop items from your users")
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

        class ResetEconomyButton(ActionRow):
            @button(label="Reset Economy coins", style=discord.ButtonStyle.red)
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

                        users = Economy.find(Economy.guild_id == str(guild.id)).run()
                        for user in users:
                            user.wallet = 0
                            user.bank = 0
                            user.bag = []
                            user.save()

                        config = Guild.get(str(guild.id)).run()
                        config.updated_at = discord.utils.utcnow()
                        config.save()

                        await interaction.response.edit_message(content="Economy coins have been reset.", view=self)

                await interaction.response.send_message(
                    "This action is strictly irreversible! Everyone will lose their coins.",
                    view=ConfirmResetEcoCoins(),
                    ephemeral=True
                )

            @button(label="Reset Economy shop", style=discord.ButtonStyle.red)
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

                        save_dash(guild.id, 'economy.shop', mainshop)
                        await interaction.response.edit_message(content="Economy shop has been reset.", view=self)

                await interaction.response.send_message(
                    "This action is strictly irreversible! The economy shop will be reset back to default.",
                    view=ConfirmResetEcoShop(),
                    ephemeral=True
                )

        container.add_item(ResetEconomyButton())
        self.add_item(container)
        self.add_item(BackButton(lambda: PluginEconomy(guild)))

class PluginEconomy(DesignerView):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        data = Guild.get(str(guild.id)).run().dashboard.economy

        container = Container(color=v.style(guild))
        container.add_text("# Economy")
        container.add_text("Players can gain coins once a day. A player can stake their coins at games. Use your coins to buy items from the shop.")

        container.add_item(StatusToggle(guild, 'economy.status', data.get('status', False)))
        
        container.add_separator(divider=True, spacing=discord.SeparatorSpacingSize.large)

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