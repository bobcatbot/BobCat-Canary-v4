import discord
from modules import bot as v
from discord.ext import commands

async def audit_log(client: discord.Client, ctx: commands.Context, event: str, embed: discord.Embed):
    logStatus = v.dashboard(ctx.guild.id, f"moderation.logging.events.{event}")
    if not logStatus:
        return False

    logging = v.dashboard(ctx.guild.id, "moderation.logging.channel")
    if not logging:
        return False

    channel = client.get_channel(int(logging))
    await channel.send(embed=embed)
    return True