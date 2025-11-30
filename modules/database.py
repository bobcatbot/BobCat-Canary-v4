import json
import discord
import pymongo

config = json.load(open('modules/config.json'))

mongoClient = pymongo.MongoClient(
    config['mongoURI_db'],
)
db = mongoClient['Bot']['Bot']

# Main DB class #
class Database:
    def __init__(self):
        super().__init__()
        self.db = db
        self.Bot = "Bot"
    
    # Main DB #
    def create_server_config(self, guild_data: dict) -> bool:
        data = db.insert_one(guild_data)
        if data:
            return True
        return False
    
    def get_all_server_config(self) -> list[dict]:
        data = db.find({})
        if data:
            return data
    
    def get_server_config(self, guild: discord.Guild, all=False) -> dict:
        """
        Gets a server's config from the database.

        Args:
            guild: The guild to get the config for.
            all: If True, returns the entire config document.
                \n   If False, returns only the "Bot" part of the config.

        Returns:
            The server's config, or None if no config exists for this server.
        """

        try:
            guildID = guild.id
        except AttributeError:
            guildID = guild
        
        data: dict = db.find_one({"_id": str(guildID)})
        if data is None:
            return None
        
        if all:
            return data
        return data["Bot"]
    
    def update_server_config(self, guild: discord.Guild, all: bool = False, key: str = '', value: dict | list | str = '') -> bool:
        """
        Updates a server's config in the database.

        Args:
            guild: The guild to update the config for.
            all: If True, updates the entire config document.
            \n       If False, updates only the "Bot" part of the config.
            key: The key to update in the config.
            value: The value to set the key to.

        Returns:
            True if the update was successful, False otherwise.
        """

        try:
            guildID = guild.id
        except AttributeError:
            guildID = guild

        if all:
            data = { key: value }
        else:
            data = { "Bot." + key: value }
        
        data = db.update_one(
            { "_id": str(guildID) }, 
            { "$set": data }
        )
        if data:
            return True
        return False
    
    # Dashboard DB #
    def get_dash(self, guild):
        try:
            guildID = guild.id
        except AttributeError:
            guildID = guild
        
        data: dict = db.find_one({"_id": str(guildID)})
        if data is None:
            return None
        return data["Dash"]
    
    def update_dash(self, guild, key, value):
        """
        Updates a value in the `Dash` config. 

        Args:
            guild: The guild to update the config for.
            key: The key to update in the config. EG `plugin.status`
            value: The value to set the key to.

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            guildID = guild.id
        except AttributeError:
            guildID = guild
        
        data = db.update_one(
            { "_id": str(guildID) }, 
            { "$set": { "Dash." + key: value } }
        )
        if data:
            return True
        return False