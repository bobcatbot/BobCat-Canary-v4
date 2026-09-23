import discord
import random
from typing import Optional
from modules import bot as v
from modules.models import Economy
from discord.ext import commands
from discord.commands import SlashCommandGroup
from ._shop import get_shop, get_currency_icon, get_user_items, open_account, update_bank, buy_this, sell_this, get_user_balance, claim_daily, DEFAULT_ITEM_ICON

# ── rob-coins success odds ───────────────────────────────────
ROB_BASE_CHANCE = 0.5     # odds when robber and victim wallets are equal
ROB_WEALTH_SWING = 0.4    # how far the wallet gap shifts the odds
ROB_MIN_CHANCE = 0.15     # never a guaranteed failure
ROB_MAX_CHANCE = 0.85     # never a guaranteed success

def _rob_success_chance(robber_wallet: int, victim_wallet: int) -> float:
    """Success odds for a robbery, based on the wallet gap.
    Equal wallets → ROB_BASE_CHANCE; richer victim → lower; poorer victim → higher."""
    total = robber_wallet + victim_wallet
    if total <= 0:
        return ROB_BASE_CHANCE
    victim_share = victim_wallet / total
    chance = ROB_BASE_CHANCE - (victim_share - 0.5) * ROB_WEALTH_SWING
    return max(ROB_MIN_CHANCE, min(ROB_MAX_CHANCE, chance))

class Money(commands.Cog):
    def __init__(self, client):
        self.client = client

    eco = SlashCommandGroup(
        name="economy",
        description=v.t.msg(None, "economy.cmd.description"),
        name_localizations=v.t.localizations("economy.cmd.name"),
        description_localizations=v.t.localizations("economy.cmd.description"),
    )

    async def get_guild_shop(ctx: discord.AutocompleteContext):
        shop = await get_shop(ctx.interaction.guild)
        return [item['name'] for item in shop]

    async def get_user_items(ctx: discord.AutocompleteContext):
        uitems = await get_user_items(ctx.interaction.guild, ctx.interaction.user)
        return [item['item'] for item in uitems]
    
    @eco.command(
        description=v.t.msg(None, "economy.shop.cmd.description"),
        name_localizations=v.t.localizations("economy.shop.cmd.name"),
        description_localizations=v.t.localizations("economy.shop.cmd.description"),
    )
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def shop(self, ctx):
        await ctx.defer()
        shop = await get_shop(ctx.guild)
        currency = await get_currency_icon(ctx.guild)

        if not shop:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "economy.shop.empty_title"),
                description=v.t.msg(ctx.guild, "economy.shop.empty_description"),
                color=v.style(ctx.guild)
            )
            return await ctx.respond(embed=embed)

        embed = discord.Embed(title=v.t.msg(ctx.guild, "economy.shop.title"), color=v.style(ctx.guild))
        for item in shop:
            name = item.get("name", v.t.msg(ctx.guild, "economy.shop.unknown_name"))
            price = item.get("price", 0)
            description = item.get("description", v.t.msg(ctx.guild, "economy.shop.no_description"))
            limit = item.get("max_limit", v.t.msg(ctx.guild, "economy.shop.no_limit"))
            icon = item.get("icon") or DEFAULT_ITEM_ICON
            embed.add_field(
                name=f"{icon} **{name}**",
                value=v.t.msg(ctx.guild, "economy.shop.field_value", currency=currency, price=price, description=description, limit=limit),
                inline=False
            )
        await ctx.respond(embed=embed)
    
    @eco.command(
        description=v.t.msg(None, "economy.leaderboard.cmd.description"),
        name_localizations=v.t.localizations("economy.leaderboard.cmd.name"),
        description_localizations=v.t.localizations("economy.leaderboard.cmd.description"),
    )
    @commands.cooldown(rate=1, per=30, type=commands.BucketType.guild)
    async def leaderboard(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        pipeline = [
            {"$match": {"guild_id": str(ctx.guild.id)}},
            {"$addFields": {"total": {"$add": ["$wallet", "$bank"]}}},
            {"$sort": {"total": -1}},
            {"$limit": 10},
            {"$project": {"user_id": 1, "wallet": 1, "bank": 1, "total": 1, "daily_streak": 1}}
        ]

        try:
            result = await Economy.aggregate(pipeline).to_list()

            if not result:
                embed = discord.Embed(
                    title=v.t.msg(ctx.guild, "economy.leaderboard.no_users_title"),
                    description=v.t.msg(ctx.guild, "economy.leaderboard.no_users_description"),
                    color=v.style(ctx.guild)
                )
                return await ctx.respond(embed=embed)

            desc = ""
            for idx, data in enumerate(result, start=1):
                try:
                    # ✅ Add error handling for user fetching
                    try:
                        member = await self.client.fetch_user(int(data["user_id"]))
                        display_name = member.display_name
                    except (discord.NotFound, discord.HTTPException):
                        display_name = v.t.msg(ctx.guild, "economy.leaderboard.unknown_user", id=data['user_id'])

                    cash = data.get("wallet", 0) + data.get("bank", 0)
                    streak = data.get("daily_streak", 0)
                    streak_suffix = v.t.msg(ctx.guild, "economy.leaderboard.streak_suffix", streak=streak) if streak > 0 else ""
                    desc += v.t.msg(ctx.guild, "economy.leaderboard.line", rank=idx, name=display_name, cash=cash, streak=streak_suffix)
                except Exception as e:
                    print(f"Error processing leaderboard entry: {e}")
                    continue

            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "economy.leaderboard.title"),
                description=desc or v.t.msg(ctx.guild, "economy.leaderboard.no_valid_users"),
                color=v.style(ctx.guild)
            )
            await ctx.respond(embed=embed)

        except Exception as e:
            print(f"Leaderboard error: {e}")
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "economy.leaderboard.error_title"),
                description=v.t.msg(ctx.guild, "economy.leaderboard.error_description"),
                color=v.error
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @eco.command(
        description=v.t.msg(None, "economy.balance.cmd.description"),
        name_localizations=v.t.localizations("economy.balance.cmd.name"),
        description_localizations=v.t.localizations("economy.balance.cmd.description"),
    )
    @commands.cooldown(rate=2, per=20, type=commands.BucketType.user)
    async def balance(self, ctx, member: Optional[discord.Member] = None):
        await ctx.defer()
        member = ctx.author if not member else member

        # Try to get existing balance first
        user_data = await get_user_balance(ctx.guild, member)
        if user_data is None:
            user_data = await open_account(ctx.guild, member)

        if user_data is None:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "economy.balance.error_title"),
                description=v.t.msg(ctx.guild, "economy.balance.error_description"),
                color=v.error
            )
            return await ctx.respond(embed=embed)

        embed = discord.Embed(
            title=v.t.msg(ctx.guild, "economy.balance.title", member=member.display_name),
            color=v.style(ctx.guild)
        )
        embed.add_field(name=v.t.msg(ctx.guild, "economy.balance.wallet_field"), value=f"`{user_data['wallet']}` coins", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.balance.bank_field"), value=f"`{user_data['bank']}` coins", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.balance.total_field"), value=f"`{user_data['wallet'] + user_data['bank']}` coins", inline=True)
        await ctx.respond(embed=embed)
        
    @eco.command(
        description=v.t.msg(None, "economy.daily.cmd.description"),
        name_localizations=v.t.localizations("economy.daily.cmd.name"),
        description_localizations=v.t.localizations("economy.daily.cmd.description"),
    )
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def daily(self, ctx):
        await ctx.defer()
        await open_account(ctx.guild, ctx.author)
        success, data = await claim_daily(ctx.guild, ctx.author)

        if not success:
            if "retry_after" not in data:
                embed = discord.Embed(
                    title=v.t.msg(ctx.guild, "economy.daily.error_title"),
                    description=v.t.msg(ctx.guild, "economy.daily.error_description"),
                    color=v.error
                )
                return await ctx.respond(embed=embed, ephemeral=True)

            retry_after = int(data["retry_after"])
            hours, remainder = divmod(retry_after, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours:
                time_left = f"{hours}h {minutes}m"
            elif minutes:
                time_left = f"{minutes}m {seconds}s"
            else:
                time_left = f"{seconds}s"
            embed = discord.Embed(
                color=v.error,
                description=v.t.msg(ctx.guild, "economy.daily.cooldown_description", member=ctx.author.display_name, time=time_left),
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        streak = data["streak"]
        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=v.t.msg(ctx.guild, "economy.daily.title"),
            description=v.t.msg(ctx.guild, "economy.daily.success_description", member=ctx.author.display_name, reward=data['reward']),
        )
        embed.add_field(name=v.t.msg(ctx.guild, "economy.daily.streak_field"), value=v.t.msg(ctx.guild, "economy.daily.streak_value", streak=streak, plural='s' if streak != 1 else ''), inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.daily.wallet_field"), value=f"`{data['wallet']}` coins", inline=True)
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.daily.footer"))
        await ctx.respond(embed=embed)

    @eco.command(
        description=v.t.msg(None, "economy.work.cmd.description"),
        name_localizations=v.t.localizations("economy.work.cmd.name"),
        description_localizations=v.t.localizations("economy.work.cmd.description"),
    )
    @commands.cooldown(rate=1, per=3600, type=commands.BucketType.user)
    async def work(self, ctx):
        await ctx.defer()
        user_data = await open_account(ctx.guild, ctx.author)
        if user_data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.work.create_failed"))

        earnings = random.randrange(50, 500)
        updated_data = await update_bank(ctx.guild, ctx.author, "bank", earnings)

        if updated_data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.work.update_failed"))

        embed = discord.Embed(
            color=v.style(ctx.guild),
            description=v.t.msg(ctx.guild, "economy.work.success_description", member=ctx.author.display_name, earnings=earnings),
        )
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.work.footer"))
        await ctx.respond(embed=embed)

    @work.error
    async def work_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            remaining = round(error.retry_after / 60, 1)
            embed = discord.Embed(
                color=v.error,
                description=v.t.msg(ctx.guild, "economy.work.cooldown_description", member=ctx.author.display_name, minutes=remaining)
            )
            await ctx.respond(embed=embed, ephemeral=True)
    
    @eco.command(
        description=v.t.msg(None, "economy.withdraw.cmd.description"),
        name_localizations=v.t.localizations("economy.withdraw.cmd.name"),
        description_localizations=v.t.localizations("economy.withdraw.cmd.description"),
    )
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def withdraw(self, ctx, amount: str):
        await ctx.defer()
        # Validate and parse amount
        try:
            if amount.lower() == 'max':
                user_data = await get_user_balance(ctx.guild, ctx.author)
                if user_data is None:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.no_account"))

                withdraw_amount = user_data.get('bank', 0)
                if withdraw_amount == 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.withdraw.no_bank_money"))
            else:
                withdraw_amount = int(amount)
                if withdraw_amount <= 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.amount_positive"))
        except ValueError:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.invalid_number_max"))

        # Check if user has enough in bank
        user_data = await get_user_balance(ctx.guild, ctx.author)
        if user_data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.no_account"))

        if withdraw_amount > user_data.get('bank', 0):
            return await ctx.respond(v.t.msg(ctx.guild, "economy.withdraw.insufficient", bank=user_data['bank']))

        # Perform withdrawal
        await update_bank(ctx.guild, ctx.author, 'bank', -withdraw_amount)
        await update_bank(ctx.guild, ctx.author, 'wallet', withdraw_amount)

        # Get updated balance
        updated_balance = await get_user_balance(ctx.guild, ctx.author)
        if updated_balance is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.withdraw.update_failed"))

        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=v.t.msg(ctx.guild, "economy.withdraw.title", amount=withdraw_amount),
        )
        embed.add_field(name=v.t.msg(ctx.guild, "economy.withdraw.wallet_field"), value=f"`{updated_balance['wallet']}` coins", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.withdraw.bank_field"), value=f"`{updated_balance['bank']}` coins", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.withdraw.total_field"), value=f"`{updated_balance['wallet'] + updated_balance['bank']}` coins", inline=False)
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.helpers.requested_by_footer", name=ctx.author.display_name))
        await ctx.respond(embed=embed)

    @eco.command(
        description=v.t.msg(None, "economy.deposit.cmd.description"),
        name_localizations=v.t.localizations("economy.deposit.cmd.name"),
        description_localizations=v.t.localizations("economy.deposit.cmd.description"),
    )
    @commands.cooldown(rate=1, per=100, type=commands.BucketType.user)
    async def deposit(self, ctx, amount: str):
        await ctx.defer()
        # Validate and parse amount
        try:
            if amount.lower() == 'max':
                user_data = await get_user_balance(ctx.guild, ctx.author)
                if user_data is None:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.no_account"))

                deposit_amount = user_data.get('wallet', 0)
                if deposit_amount == 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.deposit.no_wallet_money"))
            else:
                deposit_amount = int(amount)
                if deposit_amount <= 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.amount_positive"))
        except ValueError:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.invalid_number_max"))

        # Check if user has enough in wallet
        user_data = await get_user_balance(ctx.guild, ctx.author)
        if user_data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.no_account"))

        if deposit_amount > user_data.get('wallet', 0):
            return await ctx.respond(v.t.msg(ctx.guild, "economy.deposit.insufficient", wallet=user_data['wallet']))

        # Perform deposit
        await update_bank(ctx.guild, ctx.author, 'wallet', -deposit_amount)
        await update_bank(ctx.guild, ctx.author, 'bank', deposit_amount)

        # Get updated balance
        updated_balance = await get_user_balance(ctx.guild, ctx.author)
        if updated_balance is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.deposit.update_failed"))

        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=v.t.msg(ctx.guild, "economy.deposit.title", amount=deposit_amount),
        )
        embed.add_field(name=v.t.msg(ctx.guild, "economy.deposit.wallet_field"), value=f"`{updated_balance['wallet']}` coins", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.deposit.bank_field"), value=f"`{updated_balance['bank']}` coins", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.deposit.total_field"), value=f"`{updated_balance['wallet'] + updated_balance['bank']}` coins", inline=False)
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.helpers.requested_by_footer", name=ctx.author.display_name))
        await ctx.respond(embed=embed)
    
    @eco.command(
        description=v.t.msg(None, "economy.buy.cmd.description"),
        name_localizations=v.t.localizations("economy.buy.cmd.name"),
        description_localizations=v.t.localizations("economy.buy.cmd.description"),
    )
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    @discord.option(
        'item',
        description=v.t.msg(None, "economy.buy.cmd.options.item.description"),
        name_localizations=v.t.localizations("economy.buy.cmd.options.item.name"),
        description_localizations=v.t.localizations("economy.buy.cmd.options.item.description"),
        required=True, autocomplete=get_guild_shop,
    )
    @discord.option(
        'amount', int,
        description=v.t.msg(None, "economy.buy.cmd.options.amount.description"),
        name_localizations=v.t.localizations("economy.buy.cmd.options.amount.name"),
        description_localizations=v.t.localizations("economy.buy.cmd.options.amount.description"),
        required=False, choices=[i for i in range(1, 11)],
    )
    async def buy(self, ctx, item: str, amount: int = 1):
        await ctx.defer()
        shop = await get_shop(ctx.guild)
        if not shop:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.empty_shop"), ephemeral=True)

        pre = await open_account(ctx.guild, ctx.author)
        res = await buy_this(ctx.guild, ctx.author, item, amount)

        # Handle errors
        if not res[0]:
            error_code = res[1]
            if error_code == 1:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.not_in_shop"), ephemeral=True)
            elif error_code == 2:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.invalid_amount"), ephemeral=True)
            elif error_code == 3:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.max_limit", item=item, limit=res[2]), ephemeral=True)
            elif error_code == 4:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.insufficient_funds", cost=res[2]), ephemeral=True)
            elif error_code == 5:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.max_inventory", item=item, limit=res[2]), ephemeral=True)
            else:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.generic_error", code=error_code), ephemeral=True)

        # Get item details for embed
        shop_item = next((i for i in shop if i["name"].lower() == item.lower()), None)
        if not shop_item:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.buy.item_error"), ephemeral=True)

        total_cost = amount * shop_item['price']
        wallet_before = pre.get('wallet', 0) if pre else 0
        from_bank = max(0, total_cost - wallet_before)
        updated = await get_user_balance(ctx.guild, ctx.author)

        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=v.t.msg(ctx.guild, "economy.buy.title"),
        )
        embed.add_field(name=v.t.msg(ctx.guild, "economy.buy.item_field"), value=f"**{shop_item['name']}**", inline=False)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.buy.quantity_field"), value=f"`{amount}`", inline=True)
        embed.add_field(name=v.t.msg(ctx.guild, "economy.buy.cost_field"), value=f"`{total_cost}` coins", inline=True)
        if from_bank > 0:
            embed.add_field(
                name=v.t.msg(ctx.guild, "economy.buy.bank_covered_field"),
                value=v.t.msg(ctx.guild, "economy.buy.bank_covered_value", amount=from_bank),
                inline=False,
            )
        if updated:
            embed.add_field(
                name=v.t.msg(ctx.guild, "economy.buy.remaining_field"),
                value=v.t.msg(ctx.guild, "economy.buy.remaining_value", wallet=updated['wallet'], bank=updated['bank']),
                inline=False,
            )
        embed.add_field(name=v.t.msg(ctx.guild, "economy.buy.description_field"), value=shop_item.get('description', v.t.msg(ctx.guild, "economy.buy.no_description")), inline=False)
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.buy.footer", member=ctx.author.display_name))
        await ctx.respond(embed=embed)
    
    @eco.command(
        description=v.t.msg(None, "economy.sell.cmd.description"),
        name_localizations=v.t.localizations("economy.sell.cmd.name"),
        description_localizations=v.t.localizations("economy.sell.cmd.description"),
    )
    @discord.option(
        'item',
        description=v.t.msg(None, "economy.sell.cmd.options.item.description"),
        name_localizations=v.t.localizations("economy.sell.cmd.options.item.name"),
        description_localizations=v.t.localizations("economy.sell.cmd.options.item.description"),
        required=True, autocomplete=get_user_items,
    )
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def sell(self, ctx, item: str):
        await ctx.defer()
        amount = 1
        await open_account(ctx.guild, ctx.author)

        res = await sell_this(ctx.guild, ctx.author, item, amount)

        if not res[0]:
            error_code = res[1]
            if error_code == 1:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.sell.not_in_shop"), ephemeral=True)
            elif error_code == 2:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.sell.not_enough", item=item), ephemeral=True)
            elif error_code == 3:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.sell.not_owned", item=item), ephemeral=True)
            else:
                return await ctx.respond(v.t.msg(ctx.guild, "economy.sell.generic_error", code=error_code), ephemeral=True)

        embed = discord.Embed(
            color=v.style(ctx.guild),
            title=v.t.msg(ctx.guild, "economy.sell.title"),
            description=v.t.msg(ctx.guild, "economy.sell.description", item=item),
        )

        # Get updated balance
        updated_balance = await get_user_balance(ctx.guild, ctx.author)
        if updated_balance:
            embed.add_field(name=v.t.msg(ctx.guild, "economy.sell.wallet_field"), value=f"`{updated_balance['wallet']}` coins", inline=True)

        await ctx.respond(embed=embed)

    @eco.command(
        description=v.t.msg(None, "economy.inventory.cmd.description"),
        name_localizations=v.t.localizations("economy.inventory.cmd.name"),
        description_localizations=v.t.localizations("economy.inventory.cmd.description"),
    )
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def inventory(self, ctx):
        await ctx.defer()
        await open_account(ctx.guild, ctx.author)
        items = await get_user_items(ctx.guild, ctx.author)

        if not items:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "economy.inventory.title", member=ctx.author.display_name),
                description=v.t.msg(ctx.guild, "economy.inventory.empty_description"),
                color=v.style(ctx.guild)
            )
            return await ctx.respond(embed=embed)

        embed = discord.Embed(
            title=v.t.msg(ctx.guild, "economy.inventory.title", member=ctx.author.display_name),
            color=v.style(ctx.guild)
        )

        for item in items:
            item_name = item.get("item", v.t.msg(ctx.guild, "economy.shop.unknown_name"))
            item_amount = item.get("amount", 0)
            embed.add_field(
                name=f"📦 {item_name}",
                value=v.t.msg(ctx.guild, "economy.inventory.item_value", amount=item_amount),
                inline=False
            )

        embed.set_footer(text=v.t.msg(ctx.guild, "economy.inventory.footer", count=len(items)))
        await ctx.respond(embed=embed)

    @eco.command(
        name="rob-coins",
        description=v.t.msg(None, "economy.rob.cmd.description"),
        name_localizations=v.t.localizations("economy.rob.cmd.name"),
        description_localizations=v.t.localizations("economy.rob.cmd.description"),
    )
    @commands.cooldown(rate=1, per=300, type=commands.BucketType.user)
    async def rob_coins(self, ctx, member: discord.Member):
        await ctx.defer()

        if member.id == ctx.author.id:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.rob.self_error"), ephemeral=True)

        if member.bot:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.rob.bot_error"), ephemeral=True)

        await open_account(ctx.guild, ctx.author)
        await open_account(ctx.guild, member)

        robber_balance = await get_user_balance(ctx.guild, ctx.author)
        victim_balance = await get_user_balance(ctx.guild, member)

        if robber_balance is None or victim_balance is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.rob.balance_error"))

        robber_wallet = robber_balance.get("wallet", 0)
        victim_wallet = victim_balance.get("wallet", 0)

        if victim_wallet < 100:
            return await ctx.respond(
                v.t.msg(ctx.guild, "economy.rob.too_poor", member=member.display_name, wallet=victim_wallet)
            )

        # Success odds scale with the wallet gap — robbing up is hard, robbing down is easy.
        chance = _rob_success_chance(robber_wallet, victim_wallet)
        odds_pct = round(chance * 100)

        if random.random() < chance:
            robbery_percent = random.uniform(0.1, 0.5)
            earning = int(victim_wallet * robbery_percent)
            earning = max(10, min(earning, victim_wallet // 2))

            await update_bank(ctx.guild, member, "wallet", -earning)
            await update_bank(ctx.guild, ctx.author, "wallet", earning)

            embed = discord.Embed(
                color=v.style(ctx.guild),
                description=v.t.msg(ctx.guild, "economy.rob.success_description", robber=ctx.author.mention, victim=member.mention, earning=earning),
            )
            embed.set_footer(text=v.t.msg(ctx.guild, "economy.rob.success_footer", odds=odds_pct))

            return await ctx.respond(embed=embed)

        # You got caught! Fine is 10–30% of the robber's wallet.
        if robber_wallet <= 0:
            fine = 0
        else:
            fine_percent = random.uniform(0.1, 0.3)
            fine = int(robber_wallet * fine_percent)
            fine = min(fine, robber_wallet)

        if fine > 0:
            await update_bank(ctx.guild, ctx.author, "wallet", -fine)
            await update_bank(ctx.guild, member, "wallet", fine)

        embed = discord.Embed(
            color=v.error,
            title=v.t.msg(ctx.guild, "economy.rob.caught_title"),
            description=v.t.msg(ctx.guild, "economy.rob.caught_description", robber=ctx.author.mention, victim=member.mention, fine=fine),
        )
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.rob.caught_footer", odds=odds_pct))

        return await ctx.respond(embed=embed)


    # ── Moderation Commands ──────────────────────────────────
    
    @eco.command(
        name="give-coins",
        description=v.t.msg(None, "economy.give_coins.cmd.description"),
        name_localizations=v.t.localizations("economy.give_coins.cmd.name"),
        description_localizations=v.t.localizations("economy.give_coins.cmd.description"),
    )
    @discord.default_permissions(moderate_members=True)
    @commands.cooldown(rate=1, per=120, type=commands.BucketType.user)
    async def give_coins(self, ctx, member: discord.Member, amount: str):
        await ctx.defer()
        if member.id == ctx.author.id:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.give_coins.self_error"), ephemeral=True)

        await open_account(ctx.guild, ctx.author)
        await open_account(ctx.guild, member)

        # Parse amount
        try:
            if amount.lower() == 'all':
                user_balance = await get_user_balance(ctx.guild, ctx.author)
                if user_balance is None:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.give_coins.balance_failed"))
                give_amount = user_balance.get('wallet', 0)
                if give_amount == 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.give_coins.no_wallet_coins"))
            else:
                give_amount = int(amount)
                if give_amount <= 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.amount_positive"))
        except ValueError:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.invalid_number_all"))

        # Check balance
        user_balance = await get_user_balance(ctx.guild, ctx.author)
        if user_balance is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.give_coins.balance_failed"))

        if give_amount > user_balance.get('wallet', 0):
            return await ctx.respond(v.t.msg(ctx.guild, "economy.give_coins.insufficient", wallet=user_balance['wallet']))

        if give_amount < 10:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.give_coins.min_amount"))

        # Perform transfer
        await update_bank(ctx.guild, ctx.author, "wallet", -give_amount)
        await update_bank(ctx.guild, member, "wallet", give_amount)

        embed = discord.Embed(
            color=v.style(ctx.guild),
            description=v.t.msg(ctx.guild, "economy.give_coins.success_description", giver=ctx.author.mention, receiver=member.mention, amount=give_amount),
        )
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.give_coins.footer"))
        await ctx.respond(embed=embed)
    
    @eco.command(
        name="remove-coins",
        description=v.t.msg(None, "economy.remove_coins.cmd.description"),
        name_localizations=v.t.localizations("economy.remove_coins.cmd.name"),
        description_localizations=v.t.localizations("economy.remove_coins.cmd.description"),
    )
    @discord.default_permissions(administrator=True)
    @commands.cooldown(rate=1, per=60, type=commands.BucketType.guild)
    async def remove_coins(self, ctx, member: discord.Member, amount: str):
        await ctx.defer()
        if member.id == ctx.author.id:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.remove_coins.self_error"), ephemeral=True)

        # Parse amount
        try:
            if amount.lower() == 'all':
                user_balance = await get_user_balance(ctx.guild, member)
                if user_balance is None:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.remove_coins.balance_failed", member=member.display_name))
                remove_amount = user_balance.get('wallet', 0) + user_balance.get('bank', 0)
                if remove_amount == 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.remove_coins.no_coins", member=member.display_name))
            else:
                remove_amount = int(amount)
                if remove_amount <= 0:
                    return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.amount_positive"))
        except ValueError:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.helpers.invalid_number_all"))

        # Check if user has enough
        user_balance = await get_user_balance(ctx.guild, member)
        if user_balance is None:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.remove_coins.balance_failed", member=member.display_name))

        total_balance = user_balance.get('wallet', 0) + user_balance.get('bank', 0)
        if remove_amount > total_balance:
            return await ctx.respond(v.t.msg(ctx.guild, "economy.remove_coins.insufficient", member=member.display_name, total=total_balance))

        # Remove from wallet first, then bank if needed
        wallet_amount = min(remove_amount, user_balance.get('wallet', 0))
        bank_amount = remove_amount - wallet_amount

        if wallet_amount > 0:
            await update_bank(ctx.guild, member, "wallet", -wallet_amount)
        if bank_amount > 0:
            await update_bank(ctx.guild, member, "bank", -bank_amount)

        embed = discord.Embed(
            color=v.error,
            description=v.t.msg(ctx.guild, "economy.remove_coins.success_description", amount=remove_amount, member=member.mention),
        )
        embed.set_footer(text=v.t.msg(ctx.guild, "economy.remove_coins.footer", member=ctx.author.display_name))
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Money(client))