import discord
from typing import Union
from discord.ext import commands
from modules import bot as v

class mod_lockdown(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot = client

    lockdown = discord.SlashCommandGroup(name="lockdown", description="Lockdown a channel/server")
    lock = lockdown.create_subgroup(name="add", description="Lockdown add")
    unlock = lockdown.create_subgroup(name="remove", description="Unlock remove")
    
# Lockdown channel
    #@lock.command(name="channel", description="Lockdown a channel")
    @discord.option("channel", description="Channel to lockdown", required=True)
    @commands.has_permissions(manage_channels=True)
    async def lockdown_channel(self, ctx, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]):
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f'#{channel.name} has been locked'
        )
        await ctx.respond(embed=embed)

        overwrite = discord.PermissionOverwrite()
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f'#{channel.name} has been locked',
            description=f'You will gain access again once the lockdown is lifted.'
        )
        await channel.send(embed=embed)
    #@lockdown_channel.error
    async def lockdown_channel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(
                color=v.error,
                title="Invalid Permission", 
                description="❌ You are missing `Manage Server` permission"
            )
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://docs.bobcatbot.xyz/commands/moderation/lock",
                description="b!lock {reason} \n\n**Arguments**\n`reason`: Reason for locking the channel",
            )
            return await ctx.send(embed=error)
    
    @lock.command(name="server", description="Lockdown the server")
    @discord.option("hidden", bool, description="Hide the channels", required=False, options=["True", "False"])
    @commands.has_permissions(manage_channels=True)
    async def lockdown_server(self, ctx: discord.ApplicationContext, hidden: bool = False):
        await ctx.defer()

        everyone: discord.Role = ctx.guild.default_role
        overwrite = discord.Permissions(send_messages=False, read_messages=hidden, connect=False)
        await everyone.edit(permissions=overwrite, reason="Server lockdown issued by {}".format(ctx.author))

        if not hidden:
            desc = 'You will gain access again once the lockdown is lifted.'
        else:
            desc = 'No one can see the channels besides admins now. A temporary updates channel has been created for the public.'

        if hidden:
            overwrite = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            }
            chan = await ctx.guild.create_text_channel(name="server-locked", overwrites=overwrite, reason="Server lockdown issued by {}".format(ctx.author))

            embed = discord.Embed(
                color=v.red,
                title=f'Server is currently locked',
                description=(
                    'This server has been completely locked down by staff.'
                    '\nYou will not be able to see or talk in channels until this lockdown is lifted.'
                    '\n**Please be patient until everything is sorted out.**'
                )
            )
            await chan.send(embed=embed)
        
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f'Server channels has been locked',
            description=desc
        )
        await ctx.respond(embed=embed)

# unlock

    @unlock.command(name="channel", description="Unlock a channel")
    @discord.option("channel", description="Channel to unlock", required=True)
    @commands.has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx, channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]):
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f'#{channel.name} has been unlocked'
        )
        await ctx.respond(embed=embed)

        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = True
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"#{channel.name} has been unlocked",
            description='Everyone now has access to this channel.'
        )
        await channel.send(embed=embed)
    @unlock_channel.error
    async def unlock_channel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            error = discord.Embed(title="❌ You are missing `Manage Server` permission", color=v.error)
            return await ctx.send(embed=error)
        if isinstance(error, commands.MissingRequiredArgument):
            error = discord.Embed(
                color=v.error,
                title="Invalid Command Usage", url="https://docs.bobcatbot.xyz/commands/moderation/unlock",
                description="b!unlock \n\n**Arguments**\n``",
            )
            return await ctx.send(embed=error)
        
    #@unlock.command(name="server", description="Unlock the server")
    @commands.has_permissions(manage_channels=True)
    async def unlock_server(self, ctx):
        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f'#{ctx.channel.name} has been unlocked'
        )
        await ctx.respond(embed=embed)

        everyone = ctx.guild.default_role
        overwrite = discord.PermissionOverwrite()
        overwrite.read_messages = False
        overwrite.send_messages = False
        overwrite.connect = False
        await everyone.edit(overwrites=overwrite, reason="Server lockdown unlock issued by {}".format(ctx.author))

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f'#{ctx.channel.name} has been unlocked',
            description=f'You will gain access again once the lockdown is lifted.'
        )
        await ctx.channel.send(embed=embed)
    
def setup(client):
    client.add_cog(mod_lockdown(client))