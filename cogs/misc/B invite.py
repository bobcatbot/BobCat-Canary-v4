import discord
from modules import bot as v
from discord.ext import commands

invite_url = "https://discord.com/oauth2/authorize?client_id=854845827109486623&permissions=141667192055&scope=bot%20applications.commands"

class MiscInvite(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(name="invite", description="Gets a invite link to add me to your server")
    async def slash_invite(self, ctx):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label='Invite', 
            url=invite_url
        ))
        
        embed=discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"Invite Bobcat",
            description=f"Click the button"
        )
        await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(MiscInvite(client))