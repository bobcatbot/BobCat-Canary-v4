import discord
from discord.ext import commands
from modules import bot as v
from modules.models.custom_commands import role_is_grantable

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
            if not command.enabled:
                continue
            trigger = command.trigger.lower()
            if command.match == "exact":
                hit = content == trigger
            elif command.match == "startswith":
                hit = content.startswith(trigger)
            else:
                hit = trigger in content
            if not hit:
                continue

            try:
                if command.action != "reply":
                    role = message.guild.get_role(int(command.role_id)) if command.role_id else None
                    # Checked here as well as in the dashboard, since the saved rule could be edited by hand.
                    if role is None or not role_is_grantable(role, message.guild.me):
                        return
                    if command.action == "add_role":
                        await message.author.add_roles(role)
                    else:
                        await message.author.remove_roles(role)

                if command.reply:
                    reply = command.reply.replace("{user}", message.author.mention).replace("{server}", message.guild.name)
                    await message.channel.send(reply)
            except discord.Forbidden:
                pass
            return  # first matching command wins

def setup(client):
    client.add_cog(CustomCommands(client))
