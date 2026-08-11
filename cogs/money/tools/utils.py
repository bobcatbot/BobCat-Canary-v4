import asyncio
from typing import Optional, Dict, Any, List, Tuple, Union
from modules.models import Guild, Economy

# Default shop items
mainshop = [
    {"name": "Teddy", "price": 50, "description": "Very soft cuddly teddy bear", "max_limit": 5},
    {"name": "Watch", "price": 100, "description": "A thing to tell the time", "max_limit": 5},
    {"name": "Phone", "price": 500, "description": "A phone", "max_limit": 5},
    {"name": "Laptop", "price": 1000, "description": "A nice laptop for work and play", "max_limit": 5},
]

def _get_economy_id(guild_id: Union[int, str], user_id: Union[int, str]) -> str:
    """Generate consistent economy document ID."""
    return f"{guild_id}_{user_id}"

async def get_shop(guild) -> List[dict]:
    """Return the shop items from the guild's dashboard, or default shop if not set."""
    try:
        doc = Guild.get(str(guild.id)).run()
        
        if doc is None:
            return mainshop
        
        shop = doc.dashboard.economy.get("shop", [])
        if not shop:
            doc.dashboard.economy["shop"] = mainshop
            doc.save()
            return mainshop
        
        return shop
    except Exception as e:
        print(f"Error getting shop for guild {guild.id}: {e}")
        return mainshop

async def get_user_items(guild, member) -> List[Dict[str, Any]]:
    """Return the user's inventory (bag)."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = Economy.get(economy_id).run()
        return user.bag if user else []
    except Exception as e:
        print(f"Error getting user items for {member.id} in guild {guild.id}: {e}")
        return []

async def open_account(guild, member) -> Optional[Dict[str, Any]]:
    """Create an economy account if one doesn't exist, and return the user data."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = Economy.get(economy_id).run()
        
        if user is None:
            user = Economy(
                id=economy_id,
                guild_id=str(guild.id),
                user_id=str(member.id),
                wallet=0,
                bank=0,
                bag=[],
            )
            user.insert()
            user = Economy.get(economy_id).run()
        
        if user is None:
            return None
            
        return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}
    except Exception as e:
        print(f"Error opening account for {member.id} in guild {guild.id}: {e}")
        return None

async def update_bank(guild, member, mode: str = "wallet", change: int = 0) -> Optional[Dict[str, Any]]:
    """Update a user's wallet or bank balance. Returns the updated balances."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = Economy.get(economy_id).run()
        
        if user is None:
            user_data = await open_account(guild, member)
            if user_data is None:
                raise RuntimeError("Failed to create economy account")
            user = Economy.get(economy_id).run()
            if user is None:
                raise RuntimeError("Failed to retrieve economy account")
        
        if mode not in ["wallet", "bank"]:
            raise ValueError("mode must be 'wallet' or 'bank'")
        
        current_balance = getattr(user, mode)
        new_balance = current_balance + change
        
        if new_balance < 0:
            new_balance = 0
            
        setattr(user, mode, new_balance)
        user.save()
        
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
        user = Economy.get(economy_id).run()
        
        if user is None:
            user_data = await open_account(guild, member)
            if user_data is None:
                return (False, "Failed to create account")
            user = Economy.get(economy_id).run()
        
        if user is None:
            return (False, "Failed to retrieve account")
        
        if user.wallet < cost:
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
        
        user.wallet -= cost
        user.save()
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
        user = Economy.get(economy_id).run()
        
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
                user.save()
                return (True, "Worked")
        
        return (False, 3)
    
    except Exception as e:
        print(f"Error processing sale for {member.id}: {e}")
        return (False, f"Error: {str(e)}")

async def get_user_balance(guild, member) -> Optional[Dict[str, Any]]:
    """Get user's current balance without modifying anything."""
    try:
        economy_id = _get_economy_id(guild.id, member.id)
        user = Economy.get(economy_id).run()
        if user is None:
            return None
        
        return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}
    except Exception as e:
        print(f"Error getting balance for {member.id}: {e}")
        return None