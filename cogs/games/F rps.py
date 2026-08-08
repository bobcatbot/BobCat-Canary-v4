import discord
import random
import asyncio
from discord.ext import commands

class GamesRps(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(description="Play Rock, Paper, Scissors")
    async def rps(self, ctx):
        rpsGame = ['rock', 'paper', 'scissors']
        user_name = ctx.author.name

        class Buttons(discord.ui.View):
            def __init__(self, user_name, original_interaction):
                super().__init__(timeout=60)
                self.user_name = user_name
                self.original_interaction = original_interaction
                self.used = False  # prevent double handling

            async def interaction_check(self, interaction):
                return interaction.user == ctx.author

            @discord.ui.button(emoji="🪨", style=discord.ButtonStyle.red)
            async def rock(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.used:
                    return
                await self.handle_choice(interaction, "rock")

            @discord.ui.button(emoji="📃", style=discord.ButtonStyle.green)
            async def paper(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.used:
                    return
                await self.handle_choice(interaction, "paper")

            @discord.ui.button(emoji="✂️", style=discord.ButtonStyle.blurple)
            async def scissors(self, button: discord.ui.Button, interaction: discord.Interaction):
                if self.used:
                    return
                await self.handle_choice(interaction, "scissors")

            async def handle_choice(self, interaction, user_choice):
                comp_choice = random.choice(rpsGame)
                comp_emoji = {"rock": "🪨", "paper": "📃", "scissors": "✂️"}[comp_choice]

                # Disable all buttons immediately
                for child in self.children:
                    child.disabled = True
                self.used = True
                self.stop()

                await interaction.response.edit_message(
                    content=f"{self.user_name} plays {user_choice} and their opponent {comp_emoji}",
                    view=self
                )
                await asyncio.sleep(1)

                # Determine winner
                if user_choice == comp_choice:
                    result = "It's a tie!"
                elif (user_choice == "rock" and comp_choice == "scissors") or \
                     (user_choice == "paper" and comp_choice == "rock") or \
                     (user_choice == "scissors" and comp_choice == "paper"):
                    result = f"{self.user_name}, you win!"
                else:
                    result = f"{self.user_name}, you lose."

                await interaction.edit_original_response(content=result, view=None)

            async def on_timeout(self):
                if self.used:
                    return
                for child in self.children:
                    child.disabled = True
                await self.original_interaction.edit_original_response(
                    content="Time's up! No one made a choice.",
                    view=self
                )

        view = Buttons(user_name, ctx.interaction)
        await ctx.respond(
            f"Rock, paper, or scissors? Choose wisely...",
            view=view
        )

def setup(client):
    client.add_cog(GamesRps(client))