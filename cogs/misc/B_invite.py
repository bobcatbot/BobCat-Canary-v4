import discord
from modules import bot as v
from discord.ext import commands

invite_url = "https://discord.com/oauth2/authorize?client_id=854845827109486623&permissions=141667192055&scope=bot%20applications.commands"

class MiscInvite(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        name="invite",
        description=v.t.msg(None, "invite.cmd.description"),
        name_localizations=v.t.localizations("invite.cmd.name"),
        description_localizations=v.t.localizations("invite.cmd.description"),
    )
    async def slash_invite(self, ctx):
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label=v.t.msg(ctx.guild, "invite.button"),
            url=invite_url
        ))

        embed=discord.Embed(
            color=v.style(ctx.guild.id),
            title=v.t.msg(ctx.guild, "invite.title"),
            description=v.t.msg(ctx.guild, "invite.description")
        )
        await ctx.respond(embed=embed, view=view)

def setup(client):
    client.add_cog(MiscInvite(client))