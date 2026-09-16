import discord
from modules import bot as v
from discord.ext import commands

class Games(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(description="Show the list and information of server's games")
    async def games(self, ctx):
        embed = discord.Embed(title="Discord Games", color=v.style(ctx.guild.id))
        embed.add_field(name="Magic 8ball", value="`/8ball <question>` \nAsk the magic 8ball a question", inline=False)
        embed.add_field(name="Diceroll", value="`/diceroll <amount>` \nThrow two dice and bet coins on the outcome", inline=False)
        embed.add_field(name="Coinflip", value="`/coinflip` \nFlip a coin for Heads/Tails", inline=False)
        embed.add_field(name="Guess The Number", value="`/guess <amount>` \nGuess the number between 1 and 100 to win your bet", inline=False)
        embed.add_field(name="Rock Paper Scissors", value="`/rps <amount> <opponent>` \nPlay Rock, Paper, Scissors against AI or another member and bet coins", inline=False)
        embed.add_field(name="Tic Tac Toe", value="`/ttt <amount> <opponent>` \nPlay Tic Tac Toe against AI or another member and bet coins", inline=False)
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Games(client))