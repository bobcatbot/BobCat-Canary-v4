import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild

class welcomeSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def create_embed(self, embed_data, member):
        color = embed_data.get("color")
        if not color:
            embed_data["color"] = v.style(member.guild.id)
        else:
            try:
                embed_data["color"] = int(str(color).removeprefix("#"), 16)
            except ValueError:
                embed_data["color"] = v.style(member.guild.id)

        def render(value):
            if isinstance(value, str):
                return v.render_placeholders(
                    value,
                    user=member,
                    server=member.guild
                )

            if isinstance(value, dict):
                return {key: render(val) for key, val in value.items()}

            if isinstance(value, list):
                return [render(item) for item in value]

            return value

        return discord.Embed.from_dict(render(embed_data))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_doc = await Guild.get(str(member.guild.id))
        if guild_doc is None:
            return

        wel_data = guild_doc.dashboard.welcome

        # Master toggle for the whole Welcome plugin
        if not wel_data.status:
            return

        # ── Join message ────────────────────────────────────────────────────
        join = wel_data.join

        if join.status and join.channel:
            channel = self.client.get_channel(int(join.channel))
            if channel and join.message.type == "text":
                await channel.send(v.render_placeholders(
                    join.message.content,
                    user=member,
                    server=member.guild
                ))

            if channel and join.message.type == "embed":
                em = await self.create_embed(join.message.embed, member)
                await channel.send(embed=em)
        ###

        # ── Auto Roles ────────────────────────────────────────────────────
        autoRoles = wel_data.autoRoles

        if autoRoles.status and autoRoles.roles:
            roles_to_add = [
                role for roleID in autoRoles.roles
                if (role := member.guild.get_role(int(roleID))) is not None
            ]
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Welcome auto-role")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        # ── DM ────────────────────────────────────────────────────
        dm = wel_data.dm

        if dm.status and not member.bot:
            try:
                if dm.message.type == "text":
                    await member.send(v.render_placeholders(
                        dm.message.content or '',
                        user=member,
                        server=member.guild
                    ))

                elif dm.message.type == "embed":
                    em = await self.create_embed(dm.message.embed, member)
                    await member.send(embed=em)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild_doc = await Guild.get(str(member.guild.id))
        if guild_doc is None:
            return

        wel_data = guild_doc.dashboard.welcome

        # Master toggle for the whole Welcome plugin
        if not wel_data.status:
            return

        # ── Leave message ──────────────────────────────────────
        leave = wel_data.leave

        if not (leave.status and leave.channel):
            return

        channel = self.client.get_channel(int(leave.channel))
        if not channel:
            return

        if leave.message.type == "text":
            await channel.send(
                v.render_placeholders(
                    leave.message.content or "",
                    user=member,
                    server=member.guild
                )
            )

        elif leave.message.type == "embed":
            em = await self.create_embed(leave.message.embed, member)
            await channel.send(embed=em)
        
def setup(client):
    client.add_cog(welcomeSystem(client))