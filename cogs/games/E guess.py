import discord
import random
from modules import bot as v
from discord.ext import commands

class GamesGtn(commands.Cog):
    def __init__(self, client):
        self.client = client
    # TODO: support economy plugin
    # economy plugin - Guess and win gain coins
    
    # Guess the number
    @commands.slash_command(description="Guess the random number between 1 and 10")
    async def guess(self, ctx):
        if ctx.author.id == self.client.user.id:
            return
        
        await ctx.respond(f"{ctx.author.name}, the mystery machine is ready, you have **5 attempts** to guess the number **between 1 and 20**... type your answer")
        
        answer = random.randint(1, 20)
        
        guess = 5
        overall_count = 0
        while guess <= 5:
            def is_correct(m):
                return m.author == ctx.author and m.content.isdigit()
            
            message = await self.client.wait_for("message", check=is_correct, timeout=None)
            attempt = message.content

            if int(attempt) < answer:
                guess -= 1
                overall_count += 1
                count =  f"{guess} attempt left" if guess > 1 else f"{guess} attempts left"
                await ctx.send(f"{ctx.author.name}, the number you are looking for is **greater then {attempt}** \n*{count}*")

            if int(attempt) > answer:
                guess -= 1
                overall_count += 1
                count =  f"{guess} attempt left" if guess > 1 else f"{guess} attempts left"
                await ctx.send(f"{ctx.author.name}, the number you are looking for is **less then {attempt}** \n*{count}*")
            
            if int(attempt) == answer:
                overall_count += 1
                counter =  f"{overall_count} attempt" if overall_count == 1 else f"{overall_count} attempts"
                return await ctx.send(f"{ctx.author.name}, You won in {counter}!")
            if guess == 0:
                return await ctx.send(f"{ctx.author.name}, you did not find the number. The number was {answer}.")

def setup(client):
    client.add_cog(GamesGtn(client))