import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild, Starboard

class JumpToMsg(discord.ui.View):
    def __init__(self, msg):
        super().__init__()
        button = discord.ui.Button(
            label="Jump to message",
            style=discord.ButtonStyle.link,
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

        starbaord_data = Guild.get(str(payload.guild_id)).run().dashboard.starboard

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
        
        if not starSelf and payload.user_id == message.author.id:
            await message.remove_reaction(payload.emoji, payload.member)
            try:
                await payload.member.send("❌ You cannot star your own messages!")
            except:
                pass
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

        try:
            embed.set_author(icon_url=message.author.avatar.url, name=f"{message.author}")
        except:
            embed.set_author(name=f"{message.author}")

        if message.attachments:
            embed.set_image(url=message.attachments[0].url)

        result = Starboard.find_one(
            Starboard.guild_id == str(guild.id),
            Starboard.root_message_id == str(message.id),
        ).run()

        chan = await v.client.fetch_channel(int(starChannel))

        if starCount == int(starLimit):
            star_message = await chan.send(
                content=f"⭐ **{starCount}** **|** {channel.mention}",
                embed=embed,
                view=JumpToMsg(message) if starJumpLink else None
            )

            Starboard(
                guild_id=str(guild.id),
                root_message_id=str(message.id),
                star_message_id=str(star_message.id),
                stars=starCount,
            ).insert()
            return

        if starCount > int(starLimit) and result:
            star_message = await chan.fetch_message(int(result.star_message_id))
            await star_message.edit(content=f"⭐ **{starCount}** **|** {channel.mention}")

            result.stars = starCount
            result.save()
            return

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        starboard_data = Guild.get(str(payload.guild_id)).run().dashboard.starboard

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

        result = Starboard.find_one(
            Starboard.guild_id == str(guild.id),
            Starboard.root_message_id == str(message.id),
        ).run()

        if result is None:
            return

        chan = v.client.get_channel(int(starChannel))

        if starCount < int(starLimit):
            star_message = await chan.fetch_message(int(result.star_message_id))
            result.delete()

            await star_message.delete()
            return

        if starCount < result.stars:
            star_message = await chan.fetch_message(int(result.star_message_id))
            await star_message.edit(content=f"⭐ **{starCount}** **|** {channel.mention}")

            result.stars = starCount
            result.save()
            return

    @commands.Cog.listener()
    async def on_raw_reaction_clear(self, payload):
        message = await v.client.get_channel(payload.channel_id).fetch_message(payload.message_id)
        guild = v.client.get_guild(payload.guild_id)

        starbaord_data = Guild.get(str(payload.guild_id)).run().dashboard.starboard
        starChannel = starbaord_data['channel']
        chan = v.client.get_channel(int(starChannel))

        result = Starboard.find_one(
            Starboard.guild_id == str(guild.id),
            Starboard.root_message_id == str(message.id),
        ).run()
        
        if result is None:
            return

        star_message = await chan.fetch_message(int(result.star_message_id))
        result.delete()

        await star_message.delete()

def setup(client):
    client.add_cog(starboard(client))