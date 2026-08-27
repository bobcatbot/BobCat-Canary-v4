import discord
import random
from typing import Optional
from modules import bot as v
from modules.models import Economy
from discord.ext import commands
from discord.commands import SlashCommandGroup
from .tools.utils import get_shop, get_user_items, open_account, update_bank, buy_this, sell_this, get_user_balance

class Money(commands.Cog):
    def __init__(self, client):
        self.client = client

    eco = SlashCommandGroup(name="economy", description="Economy commands")

    async def get_guild_shop(ctx: discord.AutocompleteContext):
        shop = await get_shop(ctx.interaction.guild)
        return [item['name'] for item in shop]

    async def get_user_items(ctx: discord.AutocompleteContext):
        uitems = await get_user_items(ctx.interaction.guild, ctx.interaction.user)
        return [item['item'] for item in uitems]
    
    @eco.command(description="List items from the shop")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def shop(self, ctx):
        shop = await get_shop(ctx.guild)
        
        if not shop:
            embed = discord.Embed(
                title="Shop",
                description="The shop is currently empty!",
                color=v.style(ctx.guild)
            )
            return await ctx.respond(embed=embed)

        embed = discord.Embed(title="🛒 Shop", color=v.style(ctx.guild))
        for item in shop:
            name = item.get("name", "Unknown")
            price = item.get("price", 0)
            description = item.get("description", "No description")
            limit = item.get("max_limit", "No limit")
            embed.add_field(
                name=f"**{name}**",
                value=f"💰 Price: `{price}` coins\n📝 {description}\n📦 Max per purchase: `{limit}`",
                inline=False
            )
        await ctx.respond(embed=embed)
    
    @eco.command(description="Economy leaderboard")
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.guild)
    async def leaderboard(self, ctx: discord.ApplicationContext):
        pipeline = [
            {"$match": {"guild_id": str(ctx.guild.id)}},
            {"$addFields": {"total": {"$add": ["$wallet", "$bank"]}}},
            {"$sort": {"total": -1}},
            {"$limit": 10},
            {"$project": {"user_id": 1, "wallet": 1, "bank": 1, "total": 1}}
        ]
        
        try:
            result = await Economy.aggregate(pipeline).to_list()
            
            if not result:
                embed = discord.Embed(
                    title="🏆 Economy Leaderboard",
                    description="No users found!",
                    color=v.style(ctx.guild)
                )
                return await ctx.respond(embed=embed)
            
            desc = ""
            for idx, data in enumerate(result, start=1):
                try:
                    # ✅ Add error handling for user fetching
                    try:
                        member = await v.client.fetch_user(int(data["user_id"]))
                        display_name = member.display_name
                    except (discord.NotFound, discord.HTTPException):
                        display_name = f"Unknown User ({data['user_id']})"
                    
                    cash = data.get("wallet", 0) + data.get("bank", 0)
                    desc += f"\n#{idx} ● {display_name} ● `{cash}` coins"
                except Exception as e:
                    print(f"Error processing leaderboard entry: {e}")
                    continue
            
            embed = discord.Embed(
                title="🏆 Top 10 Richest People",
                description=desc or "No valid users found!",
                color=v.style(ctx.guild)
            )
            await ctx.respond(embed=embed)
            
        except Exception as e:
            print(f"Leaderboard error: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching the leaderboard. Please try again later.",
                color=v.error
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @eco.command(description="Get the balance of a member")
    @commands.cooldown(rate=2, per=20, type=commands.BucketType.user)
    async def balance(self, ctx, member: Optional[discord.Member] = None):
        member = ctx.author if not member else member
        
        # Try to get existing balance first
        user_data = await get_user_balance(ctx.guild, member)
        if user_data is None:
            user_data = await open_account(ctx.guild, member)
        
        if user_data is None:
            embed = discord.Embed(
                title="❌ Error",
                description="Could not retrieve balance information.",
                color=v.error
            )
            return await ctx.respond(embed=embed)
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Balance",
            color=v.style(ctx.guild)
        )
        embed.add_field(name="💰 Wallet Balance", value=f"`{user_data['wallet']}` coins", inline=True)
        embed.add_field(name="🏦 Bank Balance", value=f"`{user_data['bank']}` coins", inline=True)
        embed.add_field(name="📦 Total Worth", value=f"`{user_data['wallet'] + user_data['bank']}` coins", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.respond(embed=embed)
        
    @eco.command(description="Work for one hour and come back to claim your paycheck")
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def work(self, ctx):
        user_data = await open_account(ctx.guild, ctx.author)
        if user_data is None:
            return await ctx.respond("Failed to create or retrieve your account!")
        
        earnings = random.randrange(50, 500)
        updated_data = await update_bank(ctx.guild, ctx.author, "bank", earnings)
        
        if updated_data is None:
            return await ctx.respond("Failed to update your balance!")
        
        embed = discord.Embed(
            color=v.style(ctx.guild),
            description=f"✅ {ctx.author.display_name}, you started working again! You earned `{earnings}` coins in your bank account.\n\n⏰ Come back in 1 hour to claim your next paycheck!",
        )
        embed.set_footer(text="Work smarter, not harder!")
        await ctx.respond(embed=embed)
    
    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            remaining = round(error.retry_after / 60, 1)
            embed = discord.Embed(
                color=v.error,
                description=f"⏰ {ctx.author.display_name}, you're already working! Come back in **{remaining} minutes** to claim your next paycheck."
            )
            await ctx.respond(embed=embed, ephemeral=True)
    
    @eco.command(description="Withdraw money from your bank")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def withdraw(self, ctx, amount: str):
        # Validate and parse amount
        try:
            if amount.lower() == 'max':
                user_data = await get_user_balance(ctx.guild, ctx.author)
                if user_data is None:
                    return await ctx.respond("You don't have an account yet! Use `/economy balance` to create one.")
                
                withdraw_amount = user_data.get('bank', 0)
                if withdraw_amount == 0:
                    return await ctx.respond("You don't have any money in your bank!")
            else:
                withdraw_amount = int(amount)
                if withdraw_amount <= 0:
                    return await ctx.respond("Amount must be positive!")
        except ValueError:
            return await ctx.respond("Please enter a valid number or 'max'")
        
        # Check if user has enough in bank
        user_data = await get_user_balance(ctx.guild, ctx.author)
        if user_data is None:
            return await ctx.respond("You don't have an account yet! Use `/economy balance` to create one.")
        
        if withdraw_amount > user_data.get('bank', 0):
            return await ctx.respond(f"You only have `{user_data['bank']}` coins in your bank!")
        
        # Perform withdrawal
        await update_bank(ctx.guild, ctx.author, 'bank', -withdraw_amount)
        await update_bank(ctx.guild, ctx.author, 'wallet', withdraw_amount)
        
        # Get updated balance
        updated_balance = await get_user_balance(ctx.guild, ctx.author)
        if updated_balance is None:
            return await ctx.respond("Failed to retrieve updated balance!")
        
        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=f"💰 Withdrawn {withdraw_amount} coins",
        )
        embed.add_field(name="💰 Wallet", value=f"`{updated_balance['wallet']}` coins", inline=True)
        embed.add_field(name="🏦 Bank", value=f"`{updated_balance['bank']}` coins", inline=True)
        embed.add_field(name="📦 Total", value=f"`{updated_balance['wallet'] + updated_balance['bank']}` coins", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.respond(embed=embed)

    @eco.command(description="Deposit money into your bank")
    @commands.cooldown(rate=1, per=100, type=commands.BucketType.user)
    async def deposit(self, ctx, amount: str):
        # Validate and parse amount
        try:
            if amount.lower() == 'max':
                user_data = await get_user_balance(ctx.guild, ctx.author)
                if user_data is None:
                    return await ctx.respond("You don't have an account yet! Use `/economy balance` to create one.")
                
                deposit_amount = user_data.get('wallet', 0)
                if deposit_amount == 0:
                    return await ctx.respond("You don't have any money in your wallet!")
            else:
                deposit_amount = int(amount)
                if deposit_amount <= 0:
                    return await ctx.respond("Amount must be positive!")
        except ValueError:
            return await ctx.respond("Please enter a valid number or 'max'")
        
        # Check if user has enough in wallet
        user_data = await get_user_balance(ctx.guild, ctx.author)
        if user_data is None:
            return await ctx.respond("You don't have an account yet! Use `/economy balance` to create one.")
        
        if deposit_amount > user_data.get('wallet', 0):
            return await ctx.respond(f"You only have `{user_data['wallet']}` coins in your wallet!")
        
        # Perform deposit
        await update_bank(ctx.guild, ctx.author, 'wallet', -deposit_amount)
        await update_bank(ctx.guild, ctx.author, 'bank', deposit_amount)
        
        # Get updated balance
        updated_balance = await get_user_balance(ctx.guild, ctx.author)
        if updated_balance is None:
            return await ctx.respond("Failed to retrieve updated balance!")
        
        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=f"🏦 Deposited {deposit_amount} coins",
        )
        embed.add_field(name="💰 Wallet", value=f"`{updated_balance['wallet']}` coins", inline=True)
        embed.add_field(name="🏦 Bank", value=f"`{updated_balance['bank']}` coins", inline=True)
        embed.add_field(name="📦 Total", value=f"`{updated_balance['wallet'] + updated_balance['bank']}` coins", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.respond(embed=embed)
    
    @eco.command(description="Buy an item from the shop")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    @discord.option('item', description="The item you want to buy", required=True, autocomplete=get_guild_shop)
    @discord.option('amount', int, description="The amount of the item you want to buy", required=False, choices=[i for i in range(1, 11)])
    async def buy(self, ctx, item: str, amount: int = 1):
        shop = await get_shop(ctx.guild)
        if not shop:
            return await ctx.respond("The shop is currently empty!", ephemeral=True)
        
        await open_account(ctx.guild, ctx.author)
        res = await buy_this(ctx.guild, ctx.author, item, amount)
        
        # Handle errors
        if not res[0]:
            error_code = res[1]
            if error_code == 1:
                return await ctx.respond("❌ This item doesn't exist in the shop!", ephemeral=True)
            elif error_code == 2:
                return await ctx.respond("❌ Please select a valid amount (1 or more)!", ephemeral=True)
            elif error_code == 3:
                return await ctx.respond(f"❌ {item} has a max limit of {res[2]} per purchase!", ephemeral=True)
            elif error_code == 4:
                return await ctx.respond(f"❌ You don't have enough money in your wallet! You need `{res[2]}` coins.", ephemeral=True)
            elif error_code == 5:
                return await ctx.respond(f"❌ You already have the maximum amount of {item} ({res[2]} items) in your inventory!", ephemeral=True)
            else:
                return await ctx.respond(f"❌ An error occurred: {error_code}", ephemeral=True)
        
        # Get item details for embed
        shop_item = next((i for i in shop if i["name"].lower() == item.lower()), None)
        if not shop_item:
            return await ctx.respond("❌ An error occurred with the shop item!", ephemeral=True)
        
        total_cost = amount * shop_item['price']
        embed = discord.Embed(
            color=v.style(ctx.guild),
            title="✅ Purchase Successful!",
        )
        embed.add_field(name="🛍️ Item", value=f"**{shop_item['name']}**", inline=False)
        embed.add_field(name="📦 Quantity", value=f"`{amount}`", inline=True)
        embed.add_field(name="💰 Total Cost", value=f"`{total_cost}` coins", inline=True)
        embed.add_field(name="📝 Description", value=shop_item.get('description', 'No description'), inline=False)
        embed.set_footer(text=f"Thank you for your purchase, {ctx.author.display_name}!")
        await ctx.respond(embed=embed)
    
    @eco.command(description="Sell an item from your inventory")
    @discord.option('item', description="The item you want to sell", required=True, autocomplete=get_user_items)
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def sell(self, ctx, item: str):
        amount = 1
        await open_account(ctx.guild, ctx.author)
        
        res = await sell_this(ctx.guild, ctx.author, item, amount)
        
        if not res[0]:
            error_code = res[1]
            if error_code == 1:
                return await ctx.respond("❌ That item doesn't exist in the shop!", ephemeral=True)
            elif error_code == 2:
                return await ctx.respond(f"❌ You don't have enough {item} in your inventory!", ephemeral=True)
            elif error_code == 3:
                return await ctx.respond(f"❌ You don't have any {item} in your inventory!", ephemeral=True)
            else:
                return await ctx.respond(f"❌ An error occurred: {error_code}", ephemeral=True)
        
        embed = discord.Embed(
            color=v.style(ctx.guild),
            title="💰 Sale Successful!",
            description=f"✅ You sold **1** **{item}**!",
        )
        
        # Get updated balance
        updated_balance = await get_user_balance(ctx.guild, ctx.author)
        if updated_balance:
            embed.add_field(name="💰 New Wallet Balance", value=f"`{updated_balance['wallet']}` coins", inline=True)
        
        await ctx.respond(embed=embed)

    @eco.command(description="View your inventory")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def inventory(self, ctx):
        await open_account(ctx.guild, ctx.author)
        items = await get_user_items(ctx.guild, ctx.author)

        if not items:
            embed = discord.Embed(
                title=f"{ctx.author.display_name}'s Inventory",
                description="🈳 Your inventory is empty! Buy items from the shop!",
                color=v.style(ctx.guild)
            )
            return await ctx.respond(embed=embed)
        
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Inventory",
            color=v.style(ctx.guild)
        )
        
        for item in items:
            item_name = item.get("item", "Unknown")
            item_amount = item.get("amount", 0)
            embed.add_field(
                name=f"📦 {item_name}",
                value=f"Quantity: `{item_amount}`",
                inline=False
            )
        
        embed.set_footer(text=f"Total items: {len(items)}")
        await ctx.respond(embed=embed)

    # Moderation Commands
    @eco.command(name="give-coins", description="Give coins to another member")
    @discord.default_permissions(moderate_members=True)
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def give_coins(self, ctx, member: discord.Member, amount: str):
        if member.id == ctx.author.id:
            return await ctx.respond("❌ You cannot give coins to yourself!", ephemeral=True)
        
        await open_account(ctx.guild, ctx.author)
        await open_account(ctx.guild, member)
        
        # Parse amount
        try:
            if amount.lower() == 'all':
                user_balance = await get_user_balance(ctx.guild, ctx.author)
                if user_balance is None:
                    return await ctx.respond("Failed to get your balance!")
                give_amount = user_balance.get('wallet', 0)
                if give_amount == 0:
                    return await ctx.respond("You don't have any coins in your wallet!")
            else:
                give_amount = int(amount)
                if give_amount <= 0:
                    return await ctx.respond("Amount must be positive!")
        except ValueError:
            return await ctx.respond("Please enter a valid number or 'all'")
        
        # Check balance
        user_balance = await get_user_balance(ctx.guild, ctx.author)
        if user_balance is None:
            return await ctx.respond("Failed to get your balance!")
        
        if give_amount > user_balance.get('wallet', 0):
            return await ctx.respond(f"You only have `{user_balance['wallet']}` coins in your wallet!")
        
        if give_amount < 10:
            return await ctx.respond("You must give at least 10 coins!")
        
        # Perform transfer
        await update_bank(ctx.guild, ctx.author, "wallet", -give_amount)
        await update_bank(ctx.guild, member, "wallet", give_amount)
        
        embed = discord.Embed(
            color=v.style(ctx.guild),
            description=f"✅ {ctx.author.mention} gave {member.mention} **`{give_amount}`** coins!",
        )
        embed.set_footer(text="Generosity is a virtue!")
        await ctx.respond(embed=embed)
    
    @eco.command(name="rob-coins", description="Rob coins from another member")
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.user)
    async def rob_coins(self, ctx, member: discord.Member):
        if member.id == ctx.author.id:
            return await ctx.respond("❌ You cannot rob yourself!", ephemeral=True)
        
        await open_account(ctx.guild, ctx.author)
        await open_account(ctx.guild, member)
        
        # Check victim's balance
        victim_balance = await get_user_balance(ctx.guild, member)
        if victim_balance is None:
            return await ctx.respond(f"Failed to get {member.display_name}'s balance!")
        
        if victim_balance.get('wallet', 0) < 100:
            return await ctx.respond(f"💀 {member.display_name} is too poor to rob! They only have `{victim_balance['wallet']}` coins.")
        
        # Calculate robbery amount (random between 10% and 50% of victim's wallet)
        robbery_percent = random.uniform(0.1, 0.5)
        earning = int(victim_balance['wallet'] * robbery_percent)
        earning = max(10, min(earning, victim_balance['wallet'] // 2))  # Min 10, max 50% of wallet
        
        # Perform robbery
        await update_bank(ctx.guild, member, "wallet", -earning)
        await update_bank(ctx.guild, ctx.author, "wallet", earning)
        
        embed = discord.Embed(
            color=v.style(ctx.guild),
            description=f"🔫 {ctx.author.mention} robbed {member.mention} and got **`{earning}`** coins!",
        )
        embed.set_footer(text="Crime doesn't pay... or does it?")
        await ctx.respond(embed=embed)
    
    @eco.command(name="remove-coins", description="Remove coins from a member (admin only)")
    @discord.default_permissions(administrator=True)
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.guild)
    async def remove_coins(self, ctx, member: discord.Member, amount: str):
        if member.id == ctx.author.id:
            return await ctx.respond("❌ You cannot remove coins from yourself!", ephemeral=True)
        
        # Parse amount
        try:
            if amount.lower() == 'all':
                user_balance = await get_user_balance(ctx.guild, member)
                if user_balance is None:
                    return await ctx.respond(f"Failed to get {member.display_name}'s balance!")
                remove_amount = user_balance.get('wallet', 0) + user_balance.get('bank', 0)
                if remove_amount == 0:
                    return await ctx.respond(f"{member.display_name} has no coins to remove!")
            else:
                remove_amount = int(amount)
                if remove_amount <= 0:
                    return await ctx.respond("Amount must be positive!")
        except ValueError:
            return await ctx.respond("Please enter a valid number or 'all'")
        
        # Check if user has enough
        user_balance = await get_user_balance(ctx.guild, member)
        if user_balance is None:
            return await ctx.respond(f"Failed to get {member.display_name}'s balance!")
        
        total_balance = user_balance.get('wallet', 0) + user_balance.get('bank', 0)
        if remove_amount > total_balance:
            return await ctx.respond(f"{member.display_name} only has `{total_balance}` coins total!")
        
        # Remove from wallet first, then bank if needed
        wallet_amount = min(remove_amount, user_balance.get('wallet', 0))
        bank_amount = remove_amount - wallet_amount
        
        if wallet_amount > 0:
            await update_bank(ctx.guild, member, "wallet", -wallet_amount)
        if bank_amount > 0:
            await update_bank(ctx.guild, member, "bank", -bank_amount)
        
        embed = discord.Embed(
            color=v.error,
            description=f"🗑️ Removed **`{remove_amount}`** coins from {member.mention}!",
        )
        embed.set_footer(text=f"Action performed by {ctx.author.display_name}")
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Money(client))