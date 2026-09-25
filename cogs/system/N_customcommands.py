import discord
from discord.ext import commands
from modules import bot as v

class CustomCommands(commands.Cog):
    def __init__(self, client: discord.Client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        dash = await v.dashboard(message.guild.id)
        if not dash or not dash.custom_commands.status:
            return

        content = message.content.lower()
        for command in dash.custom_commands.commands:
            trigger = command.trigger.lower()
            if command.match == "exact":
                hit = content == trigger
            elif command.match == "startswith":
                hit = content.startswith(trigger)
            else:
                hit = trigger in content
            if not hit:
                continue

            reply = command.reply.replace("{user}", message.author.mention).replace("{server}", message.guild.name)
            try:
                await message.channel.send(reply)
            except discord.Forbidden:
                pass
            return  # first matching command wins

def setup(client):
    client.add_cog(CustomCommands(client))
