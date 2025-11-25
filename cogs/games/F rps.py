import discord
import random
import asyncio
from modules import bot as v
from discord.ext import commands

class GamesRps(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(description="Play Rock, Paper, Scissors")
    async def rps(self, ctx):
        rpsGame = ['rock', 'paper', 'scissors']
        user_name = ctx.author.name
        
        class Buttons(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.red)
            async def rock(self, button: discord.ui.Button, interaction: discord.Interaction):
                message = ctx.msg
                user_choice = "rock"
                comp_choice = random.choice(rpsGame)

                if comp_choice == "rock": emoji = "🪨"
                if comp_choice == "paper": emoji = "📃"
                if comp_choice == "scissors": emoji = "✂️"
                
                await message.edit_original_response(content=f"{user_name} plays 🪨 and their opponent {emoji}", view=None)
                await asyncio.sleep(1)
                
                if user_choice == 'rock':
                    if comp_choice == 'rock':
                        await message.edit_original_response(content=f'{user_name}, it\'s a tie.', view=None)
                    if comp_choice == 'paper':
                        await message.edit_original_response(content=f"{user_name}, you lose.", view=None)
                    if comp_choice == 'scissors':
                        await message.edit_original_response(content=f"{user_name}, you win.", view=None)
            
            @discord.ui.button(emoji="📃", style=discord.ButtonStyle.green)
            async def paper(self, button: discord.ui.Button, interaction: discord.Interaction):
                message = ctx.msg
                user_choice = "paper"
                comp_choice = random.choice(rpsGame)

                if comp_choice == "rock": emoji = "🪨"
                if comp_choice == "paper": emoji = "📃"
                if comp_choice == "scissors": emoji = "✂️"
                
                await message.edit_original_response(f"{user_name} chose 📃 and their opponent {emoji}", view=None)
                await asyncio.sleep(1)
                
                if user_choice == 'paper':
                    if comp_choice == 'rock':
                        await message.edit_original_response(content=f'{user_name}, you win.')
                    if comp_choice == 'paper':
                        await message.edit_original_response(content=f'{user_name}, it\'s a tie.')
                    if comp_choice == 'scissors':
                        await message.edit_original_response(content=f"{user_name}, you lose.")

            @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.blurple)
            async def scissors(self, button: discord.ui.Button, interaction: discord.Interaction):
                message = ctx.msg
                user_choice = "scissors"
                comp_choice = random.choice(rpsGame)

                if comp_choice == "rock": emoji = "🪨"
                if comp_choice == "paper": emoji = "📃"
                if comp_choice == "scissors": emoji = "✂️"
                
                await message.edit_original_response(content=f"{user_name} chose ✂️ and their opponent {emoji}", view=None)
                await asyncio.sleep(1)
                
                if user_choice == 'scissors':
                    if comp_choice == 'rock':
                        await message.edit_original_response(content=f'{user_name}, you lose.')
                    if comp_choice == 'paper':
                        await message.edit_original_response(content=f'{user_name} you win.')
                    if comp_choice == 'scissors':
                        await message.edit_original_response(content=f'{user_name}, it\'s a tie.')
        
        ctx.msg = await ctx.respond(f"Rock, paper, or scissors? Choose wisely...", view=Buttons())
    
def setup(client):
    client.add_cog(GamesRps(client))