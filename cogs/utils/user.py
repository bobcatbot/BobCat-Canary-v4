import discord
from discord.ext import commands
from modules import bot as v

class UserCmd(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(description="View yours or a members information")
    @discord.option("member", description="The member to view", required=False)
    async def user(self, ctx, member: discord.Member=None):
        member = ctx.author if not member else member
        usr = await self.client.fetch_user(member.id)
        
        user_roles = [ role.mention for role in member.roles ]
        user_roles.reverse()
        
        userName = f"\n> Username: {member.name}" if member.display_name != member.name else ""
        accent_color = usr.accent_color
        roles = ", ".join(user_roles)
        
        joined = f"{member.joined_at.timestamp()}".split(".")[0]
        created = f"{member.created_at.timestamp()}".split(".")[0]

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"{member.name}'s Infomation",
            description=(
                "**General Information**"
                f"\n**Name:** `{member.display_name}`"
                    f"{userName} \n> Tag: {member} \n> ID: {member.id}"              
                f"\n**Created:** <t:{created}:R>"
                f"\n**Joined:** <t:{joined}:R>"
                f"\n**Color:** `{accent_color}`"
                f"\n**Roles:** `{len(member.roles)}`"
                
                "\n\n**Account Accessories**"
                f"\n**Roles**: {roles}"
            )
        )
        embed.set_thumbnail(url=member.avatar.url)
        await ctx.respond(embed=embed, view=None)

def setup(client):
    client.add_cog(UserCmd(client))