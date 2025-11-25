import discord
from discord.ext import commands
from modules import bot as v

class mod_roles(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

# role [member] [role]
    @commands.group(invoke_without_command=True)
    async def role(self, ctx, member: discord.Member, role: discord.Role):
        if not ctx.author.guild_permissions.manage_roles:
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
            
        if not role in member.roles:
            status = "Added"
            await member.add_roles(role)
        else:
            status = "Removed"
            await member.remove_roles(role)
        
        await ctx.send(f"{status} **{role.name}** to **{member}**")
    @role.error
    async def role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/role",
                description="b!role [member] [role] \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`role`: Mention | ID | name",
            )
            return await ctx.send(embed=error)

    @role.command(aliases=["add"])
    @commands.has_permissions(manage_roles=True)
    async def role_add(self, ctx, member: discord.Member, role: discord.Role):
        await member.add_roles(role)
        await ctx.send(f"Added **{role.name}** to **{member}**")
    @role_add.error
    async def role_add_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/role",
                description="b!role add [member] [role] \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`role`: Mention | ID | name",
            )
            return await ctx.send(embed=error)
    
    @role.command(aliases=["remove"])
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, member: discord.Member, role: discord.Role):
        await member.remove_roles(role)
        await ctx.send(f"Removed **{role.name}** to **{member}**")
    @role_remove.error
    async def role_remove_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/role",
                description="b!role remove [member] [role] \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`role`: Mention | ID | name",
            )
            return await ctx.send(embed=error)

    @role.command(aliases=["removeall", "purge", "clear"])
    @commands.has_permissions(manage_roles=True)
    async def role_removeall(self, ctx, member: discord.Member):
        for item in member.roles:
            if item.name != "@everyone":
                await member.remove_roles(item)

        await ctx.send(f"Removed all roles from **{member}**")
    @role_removeall.error
    async def role_removeall_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/role",
                description="b!role removeall [member] [role] \n\n**Arguments**\n`member`: Mention | ID | Username | Username#tag \n`role`: Mention | ID | name",
            )
            return await ctx.send(embed=error)

    @role.command(aliases=["create"])
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, name, color="", mentionable=False, hoist=False):
        style = discord.Color.default()
        role = await ctx.guild.create_role(name=name, color=style)        

        em = discord.Embed(
            color=style,
            title="Success!",
            description=(
                f"The role **{role.name}** has been created."
                f"\n **Color:** {role.color}"
                f"\n **Mentionable:** {role.mentionable}"
                f"\n **Display separately:** {role.hoist}"
            )
        )
        await ctx.send(embed=em)
    @role_create.error
    async def role_create_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/role",
                description="b!role create [name] \n\n**Arguments**\n`name`: the name you want the role to be called",
            )
            return await ctx.send(embed=error)

    @role.command(aliases=["info"])
    @commands.has_permissions(manage_roles=True)
    async def role_info(self, ctx, role: discord.Role):
        em = discord.Embed(
            color=v.style(ctx.guild.id),
            title="Role infomation",
            description=(
                f"**Name:** {role.name}"
                f"\n **ID:** {role.id}"
                f"\n **Color:** {role.color}"
                f"\n **Mentionable:** {role.mentionable}"
                f"\n **Display separately:** {role.hoist}"
                f"\n **Members**: {len(role.members)}"
                f"\n **Created**: {role.created_at}"
            )
        )
        await ctx.send(embed=em)
    @role_info.error
    async def role_info_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://www.docs.bobcatbot.xyz/moderation/role",
                description="b!role info [role] \n\n**Arguments**\n`role`: Mention | ID | name",
            )
            return await ctx.send(embed=error)

    @role.command(aliases=["allroles"])
    @commands.has_permissions(manage_roles=True)
    async def role_allroles(self, ctx):
        embed = discord.Embed(description="", color=v.style(ctx.guild.id))

        for role in ctx.guild.roles:
            embed.description += f"{role.mention} - ID: {role.id}" + "\n"
        await ctx.send(embed=embed)
    @role_allroles.error
    async def role_allroles_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)

    
    @role.command(aliases=["all"])
    @commands.has_permissions(manage_roles=True)
    async def role_all(self, ctx, role: discord.Role):
        counter = 0
        for member in ctx.guild.members:
            if not role in member.roles:
                counter += 1
                await member.add_roles(role)            
        await ctx.send(f"Added **{role.name}** to **{counter}** members")
    @role_all.error
    async def role_all_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)

    @role.command(aliases=["bots"])
    @commands.has_permissions(manage_roles=True)
    async def role_bots(self, ctx, role: discord.Role):
        counter = 0
        for member in ctx.guild.members:
            if member.bot:
                counter += 1
                await member.add_roles(role)            
        await ctx.send(f"Added **{role.name}** to **{counter}** bots")
    @role_bots.error
    async def role_bots_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
    
    @role.command(aliases=["humans"])
    @commands.has_permissions(manage_roles=True)
    async def role_humans(self, ctx, role: discord.Role):
        counter = 0
        for member in ctx.guild.members:
            if not member.bot:
                if not role in member.roles:
                    counter += 1
                    await member.add_roles(role)
        await ctx.send(f"Added **{role.name}** to **{counter}** members")
    @role_humans.error
    async def role_humans_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)

    @role.command(aliases=["rall", "rmall"])
    @commands.has_permissions(manage_roles=True)
    async def role_rmall(self, ctx, role: discord.Role):
        counter = 0
        for member in ctx.guild.members:
            counter += 1
            await member.remove_roles(role)            
        await ctx.send(f"Removed **{role.name}** to **{counter}** members")
    @role_rmall.error
    async def role_rmall_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)

    @role.command(aliases=["rmbots"])
    @commands.has_permissions(manage_roles=True)
    async def role_rmbots(self, ctx, role: discord.Role):
        counter = 0
        for member in ctx.guild.members:
            if member.bot:
                counter += 1
                await member.remove_roles(role)            
        await ctx.send(f"Removed **{role.name}** to **{counter}** bots")
    @role_rmbots.error
    async def role_rmbots_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)
    
    @role.command(aliases=["rhumans", "rmhumans"])
    @commands.has_permissions(manage_roles=True)
    async def role_rmhumans(self, ctx, role: discord.Role):
        counter = 0
        for member in ctx.guild.members:
            if not member.bot:
                counter += 1
                await member.remove_roles(role)
        await ctx.send(f"Removed **{role.name}** to **{counter}** members")
    @role_rmhumans.error
    async def role_rmhumans_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Roles` permission", color=v.error)
            return await ctx.send(embed=error)

def setup(client):
    client.add_cog(mod_roles(client))