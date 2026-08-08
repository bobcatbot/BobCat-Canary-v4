import discord
import random
from modules import bot as v
from discord.ext import commands

class Games8ball(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(name="8ball", description="Ask the magic 8ball a question")
    @discord.option("question", description="What question do you want to ask", required=True)
    async def _8ball(self, ctx, *, question):
        if question == None:
            em = discord.Embed(title='❌ Please ask a question', color=v.error)
            return await ctx.respond(embed=em)

        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", 
            "Yes - definitely.", "You may rely on it.", "As I see it, yes.", 
            "Most likely.", "Outlook good.", "Yes.", 
            "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", 
            "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.", 
            "Don't count on it.", "My send is no.", "My sources say no.", 
            "Outlook not so good.", "Very doubtful."
        ]
        
        embed = discord.Embed(
            color=0x0099ff,
            description=(
                f"**Question:** {question}"
                f"\n**Answer:** {random.choice(responses)}"
            )
        )
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(Games8ball(client))