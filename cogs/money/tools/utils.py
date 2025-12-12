import json
from modules import bot as v
# mainshop, get_bank_data, get_shop, open_account, update_bank, buy_this, sell_this

mainshop = [
    {"name": "Teddy", "price": 50, "description": "Very sot cuddly teddy bear", "max_limit": 5},
    {"name": "Watch", "price": 100, "description": "A thing to tell the time", "max_limit": 5},
    {"name": "Phone", "price": 500, "description": "A phone", "max_limit": 5},
    {"name": "Laptop", "price": 1000, "description": "A nice laptop for work and play", "max_limit": 5},
]

async def get_shop(guild) -> list[dict]:
    data = v.db.get_dash(guild.id)['economy']['shop']
    return data.get('shop')

async def get_user_items(guild, member):
    data = v.db.get_server_config(guild.id)
    user = data['economy'].get(f'{member.id}')
    return user.get('bag')

async def open_account(guild, member):
    data = v.db.get_server_config(guild.id)
    user = data['economy'].get(f'{member.id}')
    
    if user is None:
        val = {'wallet': 0, 'bank': 0, 'bag': []}
        v.db.update_server_config(guild.id, key=f'economy.{member.id}', value=val)
        return {'wallet': user.get('wallet'), 'bank': user.get('bank'), 'bag': user.get('bag')}

    return {'wallet': user.get('wallet'), 'bank': user.get('bank'), 'bag': user.get('bag')}

async def update_bank(guild, member, mode='wallet', change=0):
    data = v.db.get_server_config(guild.id)
    user = data['economy'].get(f'{member.id}')

    if user is None:
        val = {'wallet': 0, 'bank': 0, 'bag': []}
        v.db.update_server_config(guild.id, key=f'economy.{member.id}', value=val)
        return {'wallet': user.get('wallet'), 'bank': user.get('bank'), 'bag': user.get('bag')}
    
    if not mode in ['wallet', 'bank']:
        return False
    
    user[mode] += change
    v.db.update_server_config(guild.id, key=f'economy.{member.id}', value=user)

    return {'wallet': user.get('wallet'), 'bank': user.get('bank'), 'bag': user.get('bag')}

async def buy_this(guild, member, item, amt):
    item_name = item
    amount = amt
    name_ = ""

    data = v.db.get_server_config(guild.id)
    shop = await get_shop(guild)
    
    for item in shop:
        name = item["name"]
        if name == item_name:
            name_ = name
            price = item["price"]
            limit = item["max_limit"]
            break
    
    cost = int(price) * int(amount)
    bal = await update_bank(guild, member)
    
    if name_ == "":
        return [False, 1]
    
    if amount == "0" or amount == 0:
        return [False, 2]
    
    if int(amount) > int(limit):
        return [False, 3, limit]

    if bal.get('wallet') < int(cost):
        return [False, 4, cost]
    
    user = data['economy'].get(f'{member.id}')
    for i, item in enumerate(user["bag"]):
        if item["item"] == item_name:
            new_amt = int(item["amount"]) + int(amount)

            if int(new_amt) > int(limit):
                return [False, 5, limit]
            
            user["bag"][i]["amount"] = int(new_amt)
            v.db.update_server_config(guild.id, key=f'economy.{member.id}', value=user)
            await update_bank(guild, member, "wallet", cost * -1)
            return [True, "Worked"]
    
    obj = {"item": item_name, "amount": int(amount)}
    user["bag"].append(obj)

    v.db.update_server_config(guild.id, key=f'economy.{member.id}', value=user)
    await update_bank(guild, member, 'wallet', cost * -1)
    return [True, "Worked"]

async def sell_this(guild, user, item, amt):
    item_name = item
    amount = amt
    name_ = ""
    price = None

    data = v.db.get_server_config(guild.id)
    shop = await get_shop(guild)
         
    for item in shop:
        name = item["name"]
        if name == item_name:
            name_ = name
            if price == None:
                price = 0.9 * item["price"]
            break

    if name_ == "":
        return [False, 1]

    cost = int(price) * int(amount)

    user = data['economy'].get(f'{user.id}')
    for i, thing in enumerate(user["bag"]):
        if thing["item"] == item_name:
            new_amt = int(thing["amount"]) - int(amount)
            
            if new_amt < 0:
                return [False, 2]
            
            if int(new_amt) == 0:
                user["bag"].pop(i)
            
            user["bag"][i]["amount"] = int(new_amt)
    
    v.db.update_server_config(guild.id, key=f'economy.{user.id}', value=user)
    await update_bank(guild, user, cost, "wallet")
    return [True, "Worked"]