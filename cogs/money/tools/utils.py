from modules import bot as v
from modules.models import Guild, Economy
# mainshop, get_shop, get_user_items, open_account, update_bank, buy_this, sell_this

mainshop = [
    {"name": "Teddy", "price": 50, "description": "Very sot cuddly teddy bear", "max_limit": 5},
    {"name": "Watch", "price": 100, "description": "A thing to tell the time", "max_limit": 5},
    {"name": "Phone", "price": 500, "description": "A phone", "max_limit": 5},
    {"name": "Laptop", "price": 1000, "description": "A nice laptop for work and play", "max_limit": 5},
]

async def get_shop(guild) -> list[dict]:
    economy = Guild.get(str(guild.id)).run().dashboard.economy
    return economy.get("shop", [])

async def get_user_items(guild, member):
    user = Economy.get(f"{guild.id}_{member.id}").run()
    return user.bag if user else []

async def open_account(guild, member):
    user = Economy.get(f"{guild.id}_{member.id}").run()

    if user is None:
        user = Economy(
            id=f"{guild.id}_{member.id}",
            guild_id=str(guild.id),
            user_id=str(member.id),
            wallet=0,
            bank=0,
            bag=[],
        )
        user.insert()

    return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}

async def update_bank(guild, member, mode="wallet", change=0):
    user = Economy.get(f"{guild.id}_{member.id}").run()

    if user is None:
        await open_account(guild, member)
        user = Economy.get(f"{guild.id}_{member.id}").run()

    if mode not in ["wallet", "bank"]:
        return False

    setattr(user, mode, getattr(user, mode) + change)
    user.save()

    return {"wallet": user.wallet, "bank": user.bank, "bag": user.bag}

async def buy_this(guild, member, item, amt):
    item_name = item
    amount = amt
    name_ = ""

    shop = await get_shop(guild)

    for item in shop:
        name = item["name"]
        if name == item_name:
            name_ = name
            price = item["price"]
            limit = item["max_limit"]
            break

    if name_ == "":
        return [False, 1]

    cost = int(price) * int(amount)
    bal = await update_bank(guild, member)

    if amount == "0" or amount == 0:
        return [False, 2]

    if int(amount) > int(limit):
        return [False, 3, limit]

    if bal.get("wallet") < int(cost):
        return [False, 4, cost]

    user = Economy.get(f"{guild.id}_{member.id}").run()

    for i, item in enumerate(user.bag):
        if item["item"] == item_name:
            new_amt = int(item["amount"]) + int(amount)

            if int(new_amt) > int(limit):
                return [False, 5, limit]

            user.bag[i]["amount"] = int(new_amt)
            user.save()
            await update_bank(guild, member, "wallet", cost * -1)
            return [True, "Worked"]

    obj = {"item": item_name, "amount": int(amount)}
    user.bag.append(obj)
    user.save()

    await update_bank(guild, member, "wallet", cost * -1)
    return [True, "Worked"]

async def sell_this(guild, member, item, amt):
    item_name = item
    amount = amt
    name_ = ""
    price = None

    shop = await get_shop(guild)

    for item in shop:
        name = item["name"]
        if name == item_name:
            name_ = name
            if price is None:
                price = 0.9 * item["price"]
            break

    if name_ == "":
        return [False, 1]

    cost = int(price) * int(amount)
    user = Economy.get(f"{guild.id}_{member.id}").run()

    for i, thing in enumerate(user.bag):
        if thing["item"] == item_name:
            new_amt = int(thing["amount"]) - int(amount)

            if new_amt < 0:
                return [False, 2]

            if int(new_amt) == 0:
                user.bag.pop(i)
            else:
                user.bag[i]["amount"] = int(new_amt)

            user.save()
            await update_bank(guild, member, "wallet", cost)
            return [True, "Worked"]

    # Item exists in the shop but the user doesn't have it in their bag —
    # previously this fell through and paid out anyway.
    return [False, 3]