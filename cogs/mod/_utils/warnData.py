import json

async def get_warnings_data():
    with open("databases/warnings.json","r") as f:
        users = json.load(f)
    return users

async def open_account(user, guild):
    users = await get_warnings_data()
    with open("databases/warnings.json","r") as f:
        users = json.load(f)
        
    if not f"{guild.id}" in users:
        users[f"{guild.id}"] = {}
        
    if not f"{user.id}" in users:
        users[f"{guild.id}"][f"{user.id}"] = {}
        users[f"{guild.id}"][f"{user.id}"]["warnings"] = 0
        users[f"{guild.id}"][f"{user.id}"]["reasons"] = []
        
    elif f"{user.id}" in users:
        return True

    else:
        return
    with open("databases/warnings.json", "w") as f:
        json.dump(users, f)
    return True

async def add_warning(user, guild, reason):
    users = await get_warnings_data()
    with open("databases/warnings.json","r") as f:
        users = json.load(f)
    if not f"{guild.id}" in users:
        users[f"{guild.id}"] = {}
        
    if not f"{user.id}" in users:
        users[f"{guild.id}"][f"{user.id}"] = {}
        users[f"{guild.id}"][f"{user.id}"]["warnings"] = 0
        users[f"{guild.id}"][f"{user.id}"]["reasons"] = []
        
    elif f"{user.id}" in users:
        users[f"{guild.id}"][f"{user.id}"]["warnings"] += 1
        users[f"{guild.id}"][f"{user.id}"]["reasons"].append(reason)
        
    else:
        return
    with open("databases/warnings.json", "w") as f:
        json.dump(users, f)
    return True