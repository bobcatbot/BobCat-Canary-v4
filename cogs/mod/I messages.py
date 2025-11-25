import discord
import tempfile
import os
from modules import bot as v
from discord.ext import commands

class DuplicateMsg(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.message_command(name="Duplicate Message")
    @discord.default_permissions(manage_messages=True)
    async def duplicate_message(self, ctx, message: discord.Message):
        if len(message.embeds):
            embed_message = discord.Embed(color=v.style(ctx.guild.id))
            embed_message.set_author(icon_url=message.author.avatar.url, name=f"{message.author} ({message.author.name})")

            embeds = [embed_message]
            for embed in message.embeds:
                embeds.append(embed)
            return await ctx.send(embeds=embeds)

        await ctx.respond(f"{message.content}")

class Echo(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def echo(self, ctx, *, message, channel: discord.TextChannel=None):
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.send("You do not have permission to use this command.")
        
        channel = ctx.channel if not channel else channel
        await channel.send(f"{message}")

        await ctx.respond("Sent!", ephemeral=True)

def setup(client):
    client.add_cog(DuplicateMsg(client))
    client.add_cog(Echo(client))