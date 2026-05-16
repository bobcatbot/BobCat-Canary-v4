import discord
from discord.ext import commands
from modules import bot as v

class UserCmd(commands.Cog):
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
        await ctx.respond(embed=embed, view=UserButtons(self.client, ctx, member))

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
    client.add_cog(UserCmd(client))

class UserButtons(discord.ui.View):
    def __init__(self, client, ctx, member: discord.Member):
        super().__init__(timeout=None)
        self.client = client
        self.ctx = ctx
        self.member = member
    
    @discord.ui.button(label='General', style=discord.ButtonStyle.gray)
    async def info(self, button: discord.ui.Button, interaction: discord.Interaction):
        member = self.member

        usr = await self.client.fetch_user(member.id)
        colour = usr.accent_color
        if colour == None: colour = "Default"
        
        joined = member.joined_at.strftime('%m/%d/%Y')
        created = member.created_at.strftime('%m/%d/%Y')
        
        embed = discord.Embed(title=f"{member.name}'s Infomation", color=v.style(interaction))
        try:
            embed.set_thumbnail(url=member.avatar.url)
        except AttributeError:
            pass
        embed.add_field(name="Username", value=f"```{member}```", inline=True)
        embed.add_field(name="Nickname", value=f"```{member.display_name}```", inline=True)
        embed.add_field(name="User ID", value=f"```{member.id}```", inline=True)
        embed.add_field(name="Bot", value=f"```{member.bot}```", inline=True)
        embed.add_field(name="Activity", value=f"```{str(member.activity).title()}```", inline=True)
        embed.add_field(name="Status", value=f"```{str(member.status).title()}```", inline=True)
        embed.add_field(name="Profile Colour", value=f"```{colour}```", inline=True)
        embed.add_field(name="Roles", value=f"```{len(member.roles)}```", inline=True)
        embed.add_field(name="** **", value="** **", inline=False)
        embed.add_field(name="Joined at (MM/DD/YYYY)", value=f"```{joined}```", inline=True)
        embed.add_field(name="Created at (MM/DD/YYYY)", value=f"```{created}```", inline=True)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label='Profile', style=discord.ButtonStyle.gray)
    async def profile(self, button: discord.ui.Button, interaction: discord.Interaction):
        member = self.member

        economy = v.db.get_dash(interaction.guild.id)["economy"]
        
        economy_user = v.db.get_server_config(interaction.guild.id)["economy"].get(str(member.id))
        level_user = v.db.get_server_config(interaction.guild.id)["leveling"].get(str(member.id))
        
        if economy_user is None:
            wallet = 0
            bank = 0
            bag = []
        else:
            wallet = economy_user["wallet"]
            bank = economy_user["bank"]
            bag = economy_user["bag"]

        if level_user is None:
            xp = 0
            level = 0
        else:
            xp = level_user["exp"]
            level = level_user["lvl"]

        embed = discord.Embed(
            color=interaction.user.accent_color,
            title=f"{member}"
        )
        embed.add_field(name="Levels", value=f"> Level: {level} \n> Xp: {xp}", inline=False)
        embed.add_field(name="Balance", value=f"> Wallet: {wallet} {economy['icon']} \n> Bank: {bank} {economy['icon']}", inline=False)
        
        embed.set_thumbnail(url=member.avatar.url)
        await interaction.response.edit_message(embed=embed)