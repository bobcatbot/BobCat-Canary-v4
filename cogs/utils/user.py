import discord
from modules import bot as v
from discord.ext import commands

class usercmd(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.user_command(name="User ID")
    async def user_id(self, ctx, member: discord.Member):
        await ctx.respond(f"`{member.id}`", ephemeral=True)
    
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
        await ctx.respond(embed=embed)

    @commands.user_command(name="User")
    async def _user(self, ctx, member: discord.Member):
        usr = await self.client.fetch_user(member.id)
        
        user_roles = [ role.mention for role in member.roles ]
        user_roles.reverse()

        userName = f"\n> Username: {member.name}" if member.display_name != member.name else ""
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
                f"\n**Created:** {created} (MM/DD/YYYY)"
                f"\n**Joined:** {joined} (MM/DD/YYYY)"
                f"\n**Color:** `{usr.accent_color}`"
                f"\n**Roles:** `{len(member.roles)}`"

                "\n\n**Account Accessories**"
                f"\n**Roles**: {roles}"
            )
        )
        
        try:
            embed.set_thumbnail(url=member.avatar.url)
        except AttributeError:
            pic = "https://media.discordapp.net/attachments/915018131376857138/962350664338522143/noLogo.png"
            embed.set_thumbnail(url=pic)
        
        await ctx.respond(embed=embed)

    @commands.slash_command(name="avatars", description="View yours or a members avatar")
    @discord.option("member", description="The member to view", required=False)
    @discord.option("type", description="The type of avatar to view", required=False, choices=["global", "server"])
    async def avatars(self, ctx, member: discord.Member=None, type: str="global"):
        member = ctx.author if not member else member

        if type == "global":
            title, name, img = "Global", member.name, member.avatar.url
        elif type == "server":
            title, name, img = "Server", member.display_name, member.display_avatar.url
        
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"{name}'s {title} Avatar",
            description=f"**[PNG]({member.avatar.with_format('png').url})** | **[JPG]({member.avatar.with_format('jpg').url})** | **[WEBP]({member.avatar.with_format('webp').url})**"
        )
        embed.set_image(url=img)
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(usercmd(client))