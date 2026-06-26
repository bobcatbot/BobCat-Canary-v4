import discord
from discord.ext import commands
from modules import bot as v

class JumpToMsg(discord.ui.View):
  def __init__(self, msg):
    super().__init__()
    button = discord.ui.Button(
        label="Jump to message", style=discord.ButtonStyle.link,
        url=msg.jump_url
    )
    self.add_item(button)

class starboard(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return
        
        starbaord_data = v.db.get_dash(payload.guild_id)['starboard']
        
        starCount = 0
        starReaction = "⭐"
        starSatus = starbaord_data['status']
        starChannel = starbaord_data['channel']
        starLimit = starbaord_data['limit']
        starJumpLink = starbaord_data['jumpLink']
        starSelf = starbaord_data['selfStar']
        
        guild = await v.client.fetch_guild(payload.guild_id)
        channel = await v.client.fetch_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        if payload.emoji.name != starReaction:
            return
        
        if not starSatus:
            return
        if not starSelf:
            return
        if not starChannel:
            return

        for r in message.reactions:
            if r.emoji == starReaction:
                starCount += r.count
        
        embed = discord.Embed(
            color=0xeac02a,
            description=f"{message.content}",
            timestamp=message.created_at
        )
        embed.set_footer(text=f"{message.id}")

        try: embed.set_author(icon_url=message.author.avatar.url, name=f"{message.author}")
        except: embed.set_author(name=f"{message.author}")

        if message.attachments:
            embed.set_image(url=message.attachments[0].url)
        
        # system #
        guild_data = v.db.get_server_config(guild)
        for index, starboard in enumerate(guild_data['starboards']):
            if starboard['RootMessageID'] == message.id:
                idx, result = index, starboard
                break
        
        chan = await v.client.fetch_channel(int(starChannel))
        
        if starCount == int(starLimit):
            star_message = await chan.send(
                content=f"⭐ **{starCount}** **|** {channel.mention}", embed=embed,
                view = JumpToMsg(message) if starJumpLink else None
            )
            
            stars = len(guild_data['starboards'])
            v.db.update_server_config(
                guild, 
                key=f'starboards.{stars}', 
                value={"RootMessageID": message.id, "StarMessageID": star_message.id, "Stars": starCount}
            )
            return
        
        if starCount > int(starLimit):
            star_message = await chan.fetch_message(result.get("StarMessageID"))
            await star_message.edit(content=f"⭐ **{starCount}** **|** {channel.mention}")
            
            v.db.update_server_config(guild, key=f'starboards.{idx}.Stars', value=starCount)
            return
    

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):

        starboard_data = v.db.get_dash(payload.guild_id)['starboard']

        starCount = 0
        starReaction = "⭐"
        starSatus = starboard_data['status']
        starChannel = starboard_data['channel']
        starLimit = starboard_data['limit']
        
        if payload.emoji.name != starReaction:
            return
        if not starSatus:
            return
        if not starChannel:
            return
        
        guild = v.client.get_guild(payload.guild_id)
        channel = v.client.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        for r in message.reactions:
            if r.emoji == starReaction:
                starCount += r.count
        
        # system #
        guild_data = v.db.get_server_config(guild)
        for index, starboard in enumerate(guild_data['starboards']):
            if starboard['RootMessageID'] == message.id:
                idx, result = index, starboard
                break
        
        chan = v.client.get_channel(int(starChannel))
        
        if starCount < int(starLimit):
            star_message = await chan.fetch_message(result.get('StarMessageID'))
            
            guild_data['starboards'].pop(idx)
            v.db.update_server_config(guild, key=f'starboards', value=guild_data['starboards'])

            await star_message.delete()
            return

        if starCount < result.get("Stars"):
            stars = result.get("Stars")

            star_message = await chan.fetch_message( result.get('StarMessageID') )
            await star_message.edit(
                content=f"⭐ **{stars-1}** **|** {channel.mention}",
            )
            
            v.db.update_server_config(guild, key=f'starboards.{idx}.Stars', value=stars-1)
            return
    
    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        message = await self.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        guild = v.client.get_guild(payload.guild_id)

        starbaord_data = v.db.get_dash(payload.guild_id)['starboard']
        starChannel = starbaord_data['channel']
        chan = self.client.get_channel(int(starChannel))
        
        guild_data = v.db.get_server_config(guild)
        for index, starboard in enumerate(guild_data['starboards']):
            if starboard['RootMessageID'] == message.id:
                idx, result = index, starboard
                break
        
        star_message = await chan.fetch_message(result.get('StarMessageID'))
        
        guild_data['starboards'].pop(idx)
        v.db.update_server_config(guild, key=f'starboards', value=guild_data['starboards'])

        await star_message.delete()
        
def setup(client):
    client.add_cog(starboard(client))