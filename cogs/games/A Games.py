import discord
from modules import bot as v
from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(description="Show the list and information of server's games")
    async def games(self, ctx):
        embed = discord.Embed(title="Discord Games", color=v.style(ctx.guild.id))
        embed.add_field(name="Diceroll", value="`/diceroll` \nRoles a dice", inline=False)
        embed.add_field(name="Guess The Number", value="`/guess` \nGuess the random number between 1 and 10", inline=False)
        embed.add_field(name="rock peper scissors", value="`/rps` \nWin at Rock, Paper, Scissors against your opponent", inline=False)
        embed.add_field(name="TicTacToe", value="`/tictactoe <member>` \nRoles a dice", inline=False)
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Games(client))