import os

def loadcogs(client):
    for foldername in os.listdir('./cogs'):
        if foldername == "__pycache__":
            continue
        for filename in os.listdir(f"./cogs/{foldername}"):
            if filename.endswith('.py'):
                client.load_extension(f'cogs.{foldername}.{filename[:-3]}')
        
        # print(f"/cogs/{foldername} -> loaded")