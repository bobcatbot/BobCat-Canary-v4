import discord
from discord.ext import commands
from modules import bot as v

class UserCmd(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        description=v.t.msg(None, "user.cmd.description"),
        name_localizations=v.t.localizations("user.cmd.name"),
        description_localizations=v.t.localizations("user.cmd.description"),
    )
    @discord.option(
        "member",
        description=v.t.msg(None, "user.cmd.options.member.description"),
        name_localizations=v.t.localizations("user.cmd.options.member.name"),
        description_localizations=v.t.localizations("user.cmd.options.member.description"),
        required=False,
    )
    async def user(self, ctx, member: discord.Member=None):
        member = ctx.author if not member else member
        usr = await self.client.fetch_user(member.id)

        user_roles = [ role.mention for role in member.roles ]
        user_roles.reverse()

        userName = v.t.msg(ctx.guild, "user.embed.username_line", username=member.name) if member.display_name != member.name else ""
        accent_color = usr.accent_color
        roles = ", ".join(user_roles)

        joined = f"{member.joined_at.timestamp()}".split(".")[0]
        created = f"{member.created_at.timestamp()}".split(".")[0]

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=v.t.msg(ctx.guild, "user.embed.title", name=member.name),
            description=v.t.msg(
                ctx.guild, "user.embed.description",
                display_name=member.display_name, username_line=userName,
                tag=member, id=member.id, created=created, joined=joined,
                color=accent_color, role_count=len(member.roles), roles=roles,
            )
        )
        embed.set_thumbnail(url=member.avatar.url)
        await ctx.respond(embed=embed, view=None)

def setup(client):
    client.add_cog(UserCmd(client))