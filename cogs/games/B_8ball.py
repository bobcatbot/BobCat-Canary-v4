import discord
import random
from modules import bot as v
from discord.ext import commands

class Games8ball(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(
        name="8ball",
        description=v.t.msg(None, "8ball.cmd.description"),
        name_localizations=v.t.localizations("8ball.cmd.name"),
        description_localizations=v.t.localizations("8ball.cmd.description"),
    )
    @discord.option(
        "question",
        description=v.t.msg(None, "8ball.cmd.options.question.description"),
        name_localizations=v.t.localizations("8ball.cmd.options.question.name"),
        description_localizations=v.t.localizations("8ball.cmd.options.question.description"),
        required=True,
    )
    @discord.option(
        "amount",
        description=v.t.msg(None, "8ball.cmd.options.amount.description"),
        name_localizations=v.t.localizations("8ball.cmd.options.amount.name"),
        description_localizations=v.t.localizations("8ball.cmd.options.amount.description"),
        required=True,
    )
    async def _8ball(self, ctx, *, question, amount: int):

        embed = discord.Embed(
            color=0x0099ff,
            description=v.t.msg(
                ctx.guild, "8ball.embed.description",
                question=question, answer=random.choice(v.t.choices(ctx.guild, "8ball.responses")),
            )
        )
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Games8ball(client))