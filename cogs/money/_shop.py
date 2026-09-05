import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple, Union
from modules.models import Guild, Economy

# Fallback currency icon when the guild hasn't set one on the dashboard
DEFAULT_CURRENCY_ICON = "🪙"
# Fallback icon for shop items without one
DEFAULT_ITEM_ICON = "📦"

# ── daily reward + streak ────────────────────────────────
DAILY_BASE_REWARD = 250
DAILY_STREAK_STEP = 0.10        # +10% reward per consecutive streak day
DAILY_STREAK_MAX_MULTIPLIER = 2.0  # caps out at day 10 (1 + 9 * 0.10 = 1.9 -> capped to 2.0)
DAILY_COOLDOWN = timedelta(hours=24)     # must wait this long before claiming again
DAILY_STREAK_GRACE = timedelta(hours=48)  # claim again within this window to keep the streak alive

# Default shop items
mainshop = [
    {"name": "Teddy", "price": 50, "description": "Very soft cuddly teddy bear", "max_limit": 5, "icon": "🧸"},
    {"name": "Watch", "price": 100, "description": "A thing to tell the time", "max_limit": 5, "icon": "⌚"},
    {"name": "Phone", "price": 500, "description": "A phone", "max_limit": 5, "icon": "📱"},
    {"name": "Laptop", "price": 1000, "description": "A nice laptop for work and play", "max_limit": 5, "icon": "💻"},
]

def _get_economy_id(guild_id: Union[int, str], user_id: Union[int, str]) -> str:
    """Generate consistent economy document ID."""
    return f"{guild_id}_{user_id}"

async def get_shop(guild) -> List[dict]:
    """Return the shop items from the guild's dashboard, or default shop if not set."""
    try:
        doc = await Guild.get(str(guild.id))
        
        if doc is None:
            return mainshop
        
        shop = doc.dashboard.economy.get("shop", [])
        if not shop:
            doc.dashboard.economy["shop"] = mainshop
            await doc.save()
            return mainshop
        
        return shop
    except Exception as e:
        print(f"Error getting shop for guild {guild.id}: {e}")
        return mainshop

async def get_currency_icon(guild) -> str:
    """Return the guild's configured currency icon, or a coin emoji fallback."""
    try:
        doc = await Guild.get(str(guild.id))
        if doc is None:
            return DEFAULT_CURRENCY_ICON
        return doc.dashboard.economy.get("icon") or DEFAULT_CURRENCY_ICON
    except Exception as e:
        print(f"Error getting currency icon for guild {guild.id}: {e}")
        return DEFAULT_CURRENCY_ICON

async def get_user_items(guild, member) -> List[Dict[str, Any]]:
    """Return the user's inventory (bag)."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = await Economy.get(economy_id)
        return user.bag if user else []
    except Exception as e:
        print(f"Error getting user items for {member.id} in guild {guild.id}: {e}")
        return []

async def open_account(guild, member) -> Optional[Dict[str, Any]]:
    """Create an economy account if one doesn't exist, and return the user data."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = await Economy.get(economy_id)
        
        if user is None:
            user = Economy(
                id=economy_id,
                guild_id=str(guild.id),
                user_id=str(member.id),
                wallet=0,
                bank=0,
                bag=[],
            )
            await user.insert()
            user = await Economy.get(economy_id)
        
        if user is None:
            return None
            
        return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}
    except Exception as e:
        print(f"Error opening account for {member.id} in guild {guild.id}: {e}")
        return None

async def claim_daily(guild, member) -> Tuple[bool, Dict[str, Any]]:
    """
    Claim the daily reward, extending or resetting the streak.

    The claim is a compare-and-swap: the update is filtered on the exact
    last_daily value we just read, so if two requests race each other only
    one of them can actually land — the loser's filter no longer matches
    and it re-checks the (now updated) cooldown instead of double-paying.

    Returns (success, data).
        On failure: data = {"retry_after": seconds_until_next_claim}
        On success: data = {"reward": int, "streak": int, "wallet": int, "bank": int}
    """
    economy_id = _get_economy_id(guild.id, member.id)
    try:
        user = await Economy.get(economy_id)

        if user is None:
            if await open_account(guild, member) is None:
                raise RuntimeError("Failed to create economy account")
            user = await Economy.get(economy_id)

        if user is None:
            raise RuntimeError("Failed to retrieve economy account")

        for _ in range(3):
            raw_last_daily = user.last_daily
            now = datetime.now(timezone.utc)
            last = raw_last_daily
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)

            if last is not None:
                elapsed = now - last
                if elapsed < DAILY_COOLDOWN:
                    retry_after = (DAILY_COOLDOWN - elapsed).total_seconds()
                    return (False, {"retry_after": retry_after})
                # Claimed again in time to keep the streak going, otherwise it resets.
                new_streak = user.daily_streak + 1 if elapsed <= DAILY_STREAK_GRACE else 1
            else:
                new_streak = 1

            multiplier = min(
                1 + (new_streak - 1) * DAILY_STREAK_STEP,
                DAILY_STREAK_MAX_MULTIPLIER,
            )
            reward = int(DAILY_BASE_REWARD * multiplier)

            result = await Economy.find_one(
                Economy.id == economy_id,
                Economy.last_daily == raw_last_daily,
            ).update({
                "$inc": {"wallet": reward},
                "$set": {"last_daily": now, "daily_streak": new_streak},
            })

            if getattr(result, "modified_count", 0):
                user = await Economy.get(economy_id)
                if user is None:
                    raise RuntimeError("Failed to retrieve economy account after claim")
                return (True, {
                    "reward": reward,
                    "streak": new_streak,
                    "wallet": user.wallet,
                    "bank": user.bank,
                })

            # Someone else claimed in the gap between our read and write —
            # refresh and loop back to re-evaluate the (now updated) cooldown.
            user = await Economy.get(economy_id)
            if user is None:
                raise RuntimeError("Failed to retrieve economy account")

        # Lost the race repeatedly; fall back to whatever the latest state says.
        last = user.last_daily
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last) if last else DAILY_COOLDOWN
        retry_after = max(0.0, (DAILY_COOLDOWN - elapsed).total_seconds())
        return (False, {"retry_after": retry_after})
    except Exception as e:
        print(f"Error claiming daily reward for {member.id} in guild {guild.id}: {e}")
        return (False, {"error": str(e)})

async def update_bank(guild, member, mode: str = "wallet", change: int = 0) -> Optional[Dict[str, Any]]:
    """Update a user's wallet or bank balance. Returns the updated balances."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = await Economy.get(economy_id)
        
        if user is None:
            user_data = await open_account(guild, member)
            if user_data is None:
                raise RuntimeError("Failed to create economy account")
            user = await Economy.get(economy_id)
            if user is None:
                raise RuntimeError("Failed to retrieve economy account")
        
        if mode not in ["wallet", "bank"]:
            raise ValueError("mode must be 'wallet' or 'bank'")
        
        current_balance = getattr(user, mode)
        new_balance = current_balance + change
        
        if new_balance < 0:
            new_balance = 0
            
        setattr(user, mode, new_balance)
        await user.save()
        
        return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}
    except Exception as e:
        print(f"Error updating bank for {member.id} in guild {guild.id}: {e}")
        return None

async def buy_this(guild, member, item: str, amt: int) -> Tuple[bool, Union[int, str]]:
    """
    Process a purchase.
    Returns: [success, error_code_or_message]
    error codes: 
        1: Item not in shop
        2: Invalid amount
        3: Exceeds per-purchase limit
        4: Insufficient funds
        5: Would exceed max inventory
    """
    try:
        shop = await get_shop(guild)
        shop_item = next((i for i in shop if i["name"].lower() == item.lower()), None)
        
        if shop_item is None:
            return (False, 1)
        
        price = shop_item["price"]
        limit = shop_item.get("max_limit", 5)
        
        if amt <= 0:
            return (False, 2)
        if amt > limit:
            return (False, 3, limit)
        
        cost = price * amt
        economy_id = _get_economy_id(guild.id, member.id)
        user = await Economy.get(economy_id)
        
        if user is None:
            user_data = await open_account(guild, member)
            if user_data is None:
                return (False, "Failed to create account")
            user = await Economy.get(economy_id)
        
        if user is None:
            return (False, "Failed to retrieve account")
        
        if user.wallet + user.bank < cost:
            return (False, 4, cost)
        
        item_found = False
        for idx, entry in enumerate(user.bag):
            if entry.get("item", "").lower() == item.lower():
                new_amt = entry.get("amount", 0) + amt
                if new_amt > limit:
                    return (False, 5, limit)
                user.bag[idx]["amount"] = new_amt
                item_found = True
                break
        
        if not item_found:
            user.bag.append({"item": item, "amount": amt})
        
        # Spend from the wallet first, then cover any shortfall from the bank.
        from_wallet = min(user.wallet, cost)
        user.wallet -= from_wallet
        user.bank -= (cost - from_wallet)
        await user.save()
        return (True, "Worked")
    
    except Exception as e:
        print(f"Error processing purchase for {member.id}: {e}")
        return (False, f"Error: {str(e)}")

async def sell_this(guild, member, item: str, amt: int) -> Tuple[bool, Union[int, str]]:
    """
    Process a sale.
    Returns: [success, error_code_or_message]
    error codes:
        1: Item not in shop
        2: Not enough items
        3: Item not in inventory
    """
    try:
        shop = await get_shop(guild)
        shop_item = next((i for i in shop if i["name"].lower() == item.lower()), None)
        
        if shop_item is None:
            return (False, 1)
        
        price = int(0.9 * shop_item["price"])
        economy_id = _get_economy_id(guild.id, member.id)
        user = await Economy.get(economy_id)
        
        if user is None:
            return (False, 2)
        
        for idx, entry in enumerate(user.bag):
            if entry.get("item", "").lower() == item.lower():
                current_amount = entry.get("amount", 0)
                if current_amount < amt:
                    return (False, 2)
                
                new_amt = current_amount - amt
                if new_amt == 0:
                    user.bag.pop(idx)
                else:
                    user.bag[idx]["amount"] = new_amt
                
                user.wallet += price * amt
                await user.save()
                return (True, "Worked")
        
        return (False, 3)
    
    except Exception as e:
        print(f"Error processing sale for {member.id}: {e}")
        return (False, f"Error: {str(e)}")

async def get_user_balance(guild, member) -> Optional[Dict[str, Any]]:
    """Get user's current balance without modifying anything."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = await Economy.get(economy_id)
        if user is None:
            return None
        
        return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}
    except Exception as e:
        print(f"Error getting balance for {member.id}: {e}")
        return None