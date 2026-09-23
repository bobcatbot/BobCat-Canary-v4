import discord
from modules import bot as v
from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(
        description=v.t.msg(None, "games.cmd.description"),
        name_localizations=v.t.localizations("games.cmd.name"),
        description_localizations=v.t.localizations("games.cmd.description"),
    )
    async def games(self, ctx):
        embed = discord.Embed(title=v.t.msg(ctx.guild, "games.title"), color=v.style(ctx.guild.id))
        # Each game cog owns its own name/title/description under its own top-level
        # key (e.g. Languages/en-GB.json -> "coinflip.cmd.*") - pulled from there
        # instead of a separate games.fields.* block, so there's one place per
        # game to translate, not two.
        for command in ("8ball", "diceroll", "coinflip", "guess", "rps", "ttt"):
            embed.add_field(
                name=v.t.msg(ctx.guild, f"{command}.cmd.title"),
                value=f"`/{v.t.msg(ctx.guild, f'{command}.cmd.name')}` \n{v.t.msg(ctx.guild, f'{command}.cmd.description')}",
                inline=False,
            )
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Games(client))