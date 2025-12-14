import discord
import json
import random
from modules import bot as v
from discord.ext import commands
from discord.commands import SlashCommandGroup
from .tools.utils import get_shop, get_user_items, open_account, update_bank, buy_this, sell_this

class Money(commands.Cog):
    def __init__(self, client):
        self.client = client

    eco = SlashCommandGroup(name="economy", description="Economy commands")
    
    @eco.command(description="List items from the shop")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def shop(self, ctx):
        shop = await get_shop(ctx.guild)

        em = discord.Embed(title="Shop")
        for item in shop:
            name = item["name"]
            price = item["price"]
            description = item["description"]
            em.add_field(name=f"{name}", value=f"Price: {price} - {description}", inline=False)
        await ctx.respond(embed=em)
    
    @commands.command(aliases=["eco-leaderboard"])
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def _leaderboard(self, ctx):
        users = None
        index = 0

        em = discord.Embed(color=0xFFCC4D, title="Top 10 Richest People", description="")
        for user in users:
            print(user)
            index += 1
            member = self.client.get_user(int(user))
            print(member)

            wallet = int(user["wallet"])
            bank = int(user["bank"])
            cash = int(wallet) + int(bank)
            em.description += f"#{index} ● {user} ● {cash}\n"

        await ctx.respond(embed=em)

    @eco.command(description="Get the balance of a member")
    @commands.cooldown(rate=2, per=20, type=commands.BucketType.user)
    async def balance(self, ctx, member: discord.Member=None):
        member = ctx.author if not member else member
        user = await open_account(ctx.guild, member)
        
        em = discord.Embed(title=f'{member.name}\'s Balance', color=0xFFCC4D)
        em.add_field(name="Wallet Balance", value=user["wallet"], inline=True)
        em.add_field(name="Bank Balance", value=user["bank"], inline=True)
        await ctx.respond(embed=em)
        
    @eco.command(description="Work for one hour and come back to claim your paycheck")
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def work(self, ctx):
        await open_account(ctx.guild, ctx.author)
        earnings = random.randrange(1, 500)
        await update_bank(ctx.guild, ctx.author, "bank", earnings)
        
        em = discord.Embed(
            color=0xFFCC4D,
            description = f"{ctx.author.name} you started working again. You gain `{earnings}` from your last work. \nCome back in 1 hour to claim your",
        )
        await ctx.respond(embed=em)
    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                color=0xED5757,
                description=f"{ctx.author.name}, you are already working. Come back in 1 hour."
            )
            return await ctx.respond(embed=embed)
    
    @eco.command(description="Withwdraw money from your bank")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def withdraw(self, ctx, amount):
        user = await open_account(ctx.guild, ctx.author)
        bal = user.get('bank')

        if int(amount) > bal:
            return await ctx.respond("You don't have that much money in your bank")
                
        if amount == 'max':
            amount = bal
        amount = int(amount)
        
        await update_bank(ctx.guild, ctx.author, 'bank', -1 * amount)
        await update_bank(ctx.guild, ctx.author, 'wallet', amount)

        acc = await open_account(ctx.guild, ctx.author)
        em = discord.Embed(title=f"You withdrew {amount}", color=0xFFCC4D)
        em.add_field(name="Wallet", value=acc["wallet"], inline=True)
        em.add_field(name="Bank", value=acc["bank"], inline=True)
        await ctx.respond(embed=em)

    @eco.command(descriprion="Deposit money into your bank")
    @commands.cooldown(rate=1, per=100, type=commands.BucketType.user)
    async def deposit(self, ctx, amount):
        user = await open_account(ctx.guild, ctx.author)
        bal = user.get('wallet')
        
        if int(amount) > bal:
            return await ctx.respond("You don't have that much money in your wallet")
        
        if amount == 'max':
            amount = bal
        amount = int(amount)
        
        await update_bank(ctx.guild, ctx.author, 'wallet', -1 * amount)
        await update_bank(ctx.guild, ctx.author, 'bank', amount)

        acc = await open_account(ctx.guild, ctx.author)
        em = discord.Embed(title=f"You deposited {amount}", color=0xFFCC4D)
        em.add_field(name="Wallet", value=acc["wallet"], inline=True)
        em.add_field(name="Bank", value=acc["bank"], inline=True)
        await ctx.respond(embed=em)

    async def get_guild_shop(ctx: discord.AutocompleteContext):
        shop = await get_shop(ctx.interaction.guild)
        return [item['name'] for item in shop]

    @eco.command(description="Buy an item from the shop")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    @discord.option('item', description="The item you want to buy", required=True, autocomplete=get_guild_shop)
    @discord.option('amount', int, description="The amount of the item you want to buy", required=False, choices=[i for i in range(1, 10+1)])
    async def buy(self, ctx, item, amount=1):
        shoplist = await get_shop(ctx.guild)

        await open_account(ctx.guild, ctx.author)
        res = await buy_this(ctx.guild, ctx.author, item, amount)

        if not res[0]:
            if res[1] == 1:
                return await ctx.respond("Item seems to not exist in the shop", ephemeral=True)
            if res[1] == 2:
                return await ctx.respond("Select a valid amount", ephemeral=True)
            if res[1] == 3:
                return await ctx.respond(f"{ctx.author.display_name}, {item} has a max limit of {res[2]}",  ephemeral=True)
            if res[1] == 4:
                return await ctx.respond(f"{ctx.author.display_name}, you don't have enough money in your wallet", ephemeral=True)
            if res[1] == 5:
                return await ctx.respond(f"{ctx.author.display_name}, {item} has a max limit of {res[2]} items on your inventory", ephemeral=True)
        #

        _item = None
        for i in shoplist:
            if i["name"] == item:
                _item = i
                break
        
        embed = discord.Embed(title=f"You just bought an item from the shop", color=0xFFCC4D)
        embed.add_field(name="Item", value=_item['name'], inline=False)
        embed.add_field(name="quantity", value=amount, inline=False)
        embed.add_field(name="Total", value=amount * _item['price'], inline=False)
        await ctx.respond(embed=embed)

    async def get_user_items(ctx: discord.AutocompleteContext):
        uitems = await get_user_items(ctx.interaction.guild, ctx.interaction.user)
        return [item['item'] for item in uitems]
    
    @eco.command(description="Sell an item from your inventory")
    @discord.option('item', description="The item you want to sell", required=True, autocomplete=get_user_items)
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def sell(self, ctx, item):
        data = v.db.eco.get(ctx.guild.id)
        
        amount = 1
        await open_account(ctx.guild, ctx.author)
        
        res = await sell_this(ctx.guild, ctx.author, item, amount)
        if not res[0]:
            if res[1] == 1:
                return await ctx.respond("That Object isn't there!", ephemeral=True)
            if res[1] == 2:
                return await ctx.respond(f"You don't have {amount} {item} in your bag.", ephemeral=True)
            if res[1] == 3:
                return await ctx.respond(f"You don't have {item} in your bag.", ephemeral=True)
        
        await ctx.respond(f"You sold **{amount}** **{item}**")

    @eco.command(description="View your inventory")
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def inventory(self, ctx):
        await open_account(ctx.guild, ctx.author)
        items = await get_user_items(ctx.guild, ctx.author)

        if not items:
            return await ctx.respond(f"{ctx.author.display_name}, you don't have any items in your inventory.")
        
        embed = discord.Embed(title=f"{ctx.author.display_name}'s inventory", color=0xFFCC4D)
        for item in items:
            embed.add_field(name=item["item"], value=item["amount"], inline=False)
        await ctx.respond(embed=embed)

    # Moderation Commands
    @eco.command(name="give-coins", description="Give coins to another member")
    @discord.default_permissions(moderate_members=True)
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def give_coins(self, ctx, member: discord.Member, amount):
        await open_account(ctx.guild, ctx.author)
        await open_account(ctx.guild, member)
        bal = await update_bank(ctx.guild, ctx.author)

        if amount == 'all':
            amount = bal.get('wallet')
        amount = int(amount)

        if amount > bal.get('wallet'):
            return await ctx.respond('You do not have sufficient balance')

        if amount < 0:
            return await ctx.respond('Amount must be positive!')
        if amount <= 2:
            return await ctx.respond('Amount must be higher than 2')

        await update_bank(ctx.guild, ctx.author, -1 * amount, 'bank')
        await update_bank(ctx.guild, member, amount, 'bank')
        
        em = discord.Embed(
            color=0xFFCC4D,
            description=f"{ctx.author.mention} gave {member.mention} `{amount}`",
        )
        await ctx.respond(embed=em)
    
    @eco.command(name="remove-coins", description="Removes coins from another member")
    @discord.default_permissions(moderate_members=True)
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def remove_coins(self, ctx, member : discord.Member):
        await open_account(ctx.guild, ctx.author)
        await open_account(ctx.guild, member)
        bal = await update_bank(ctx.guild, member)
        
        if bal.get('wallet') < 100:
            return await ctx.respond('It is useless to rob him :(')
        
        earning = random.randrange(0, bal.get('wallet'))
        await update_bank(ctx.guild, ctx.author, earning)
        await update_bank(ctx.guild, member, -1 * earning)

        em = discord.Embed(
            color=0xFFCC4D,
            description=f"{ctx.author.mention} robbed {member.mention} and got {earning}",
        )
        await ctx.respond(embed=em)
    
def setup(client):
    client.add_cog(Money(client))