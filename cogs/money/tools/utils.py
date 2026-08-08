import asyncio
from modules.models import Guild, Economy

mainshop = [
    {"name": "Teddy", "price": 50, "description": "Very sot cuddly teddy bear", "max_limit": 5},
    {"name": "Watch", "price": 100, "description": "A thing to tell the time", "max_limit": 5},
    {"name": "Phone", "price": 500, "description": "A phone", "max_limit": 5},
    {"name": "Laptop", "price": 1000, "description": "A nice laptop for work and play", "max_limit": 5},
]

async def _run_sync(func, *args, **kwargs):
    """Run a synchronous Bunnet operation in a thread to avoid blocking the event loop."""
    return await asyncio.to_thread(func, *args, **kwargs)

async def get_shop(guild) -> list[dict]:
    """Return the shop items from the guild's dashboard."""
    def _get_guild():
        return Guild.get(str(guild.id)).run()
    
    doc = await _run_sync(_get_guild)
    if doc is None:
        return []
    return doc.dashboard.economy.get("shop", [])

async def get_user_items(guild, member):
    """Return the user's inventory (bag)."""
    def _get_economy():
        return Economy.get(f"{guild.id}_{member.id}").run()
    
    user = await _run_sync(_get_economy)
    return user.bag if user else []

async def open_account(guild, member):
    """Create an economy account if one doesn't exist, and return the user data."""
    def _get_economy():
        return Economy.get(f"{guild.id}_{member.id}").run()
    
    user = await _run_sync(_get_economy)
    if user is None:
        user = Economy(
            id=f"{guild.id}_{member.id}",
            guild_id=str(guild.id),
            user_id=str(member.id),
            wallet=0,
            bank=0,
            bag=[],
        )
        await _run_sync(user.insert)
    
    # Re-fetch to get the updated data
    user = await _run_sync(_get_economy)
    return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}

async def update_bank(guild, member, mode="wallet", change=0):
    """Update a user's wallet or bank balance. Returns the updated balances."""
    def _get_economy():
        return Economy.get(f"{guild.id}_{member.id}").run()
    
    user = await _run_sync(_get_economy)
    if user is None:
        await open_account(guild, member)
        user = await _run_sync(_get_economy)
        if user is None:
            raise RuntimeError("Failed to create or retrieve economy account")

    if mode not in ["wallet", "bank"]:
        raise ValueError("mode must be 'wallet' or 'bank'")

    setattr(user, mode, getattr(user, mode) + change)
    await _run_sync(user.save)
    return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}

async def buy_this(guild, member, item, amt):
    """Process a purchase. Returns [success, error_code, extra]."""
    shop = await get_shop(guild)
    shop_item = next((i for i in shop if i["name"] == item), None)
    if shop_item is None:
        return [False, 1]  # Item not in shop

    price = shop_item["price"]
    limit = shop_item.get("max_limit", 5)

    if amt <= 0:
        return [False, 2]  # Invalid amount
    if amt > limit:
        return [False, 3, limit]  # Exceeds per‑purchase limit

    cost = price * amt

    def _get_economy():
        return Economy.get(f"{guild.id}_{member.id}").run()
    
    user = await _run_sync(_get_economy)
    if user is None:
        await open_account(guild, member)
        user = await _run_sync(_get_economy)

    if user.wallet < cost:
        return [False, 4, cost]  # Insufficient funds

    # Check if the user already has this item in their bag
    for idx, entry in enumerate(user.bag):
        if entry["item"] == item:
            new_amt = entry["amount"] + amt
            if new_amt > limit:
                return [False, 5, limit]  # Would exceed max inventory
            user.bag[idx]["amount"] = new_amt
            break
    else:
        # Item not in bag, add it
        user.bag.append({"item": item, "amount": amt})

    # Deduct coins
    user.wallet -= cost
    await _run_sync(user.save)
    return [True, "Worked"]

async def sell_this(guild, member, item, amt):
    """Process a sale. Returns [success, error_code]."""
    shop = await get_shop(guild)
    shop_item = next((i for i in shop if i["name"] == item), None)
    if shop_item is None:
        return [False, 1]  # Item not in shop

    # Sell price is 90% of original
    price = int(0.9 * shop_item["price"])

    def _get_economy():
        return Economy.get(f"{guild.id}_{member.id}").run()
    
    user = await _run_sync(_get_economy)
    if user is None:
        return [False, 2]  # No account

    # Find the item in the user's bag
    for idx, entry in enumerate(user.bag):
        if entry["item"] == item:
            if entry["amount"] < amt:
                return [False, 2]  # Not enough items
            new_amt = entry["amount"] - amt
            if new_amt == 0:
                user.bag.pop(idx)
            else:
                user.bag[idx]["amount"] = new_amt
            user.wallet += price * amt
            await _run_sync(user.save)
            return [True, "Worked"]

    # User doesn't have the item
    return [False, 2]