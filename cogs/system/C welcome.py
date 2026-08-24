import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild

class welcomeSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def create_embed(self, embed_data, member):
        color = embed_data.get("color", "")
        embed_title = embed_data.get("title", "")
        embed_desc = embed_data.get("desc", "")
        embed_author = embed_data.get("author", {}).get("name", "")
        embed_footer = embed_data.get("footer", {}).get("text", "")

        embed_color = (
            int(str(color).removeprefix("#"), 16)
            if color
            else v.style(member.guild.id)
        )

        em = discord.Embed(
            color=embed_color,
            title=v.render_placeholders(
                embed_title,
                user=member,
                server=member.guild.name,
                membercount=member.guild.member_count
            ),
            description=v.render_placeholders(
                embed_desc,
                user=member,
                server=member.guild.name,
                membercount=member.guild.member_count
            )
        )

        if embed_author:
            em.set_author(
                name=v.render_placeholders(
                    embed_author,
                    user=member,
                    server=member.guild.name,
                    membercount=member.guild.member_count
                )
            )

        if embed_footer:
            em.set_footer(
                text=v.render_placeholders(
                    embed_footer,
                    user=member,
                    server=member.guild.name,
                    membercount=member.guild.member_count
                )
            )

        return em

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_doc = Guild.get(str(member.guild.id)).run()
        if guild_doc is None:
            return

        wel_data = guild_doc.dashboard.welcome

        # Master toggle for the whole Welcome plugin
        if not wel_data.get('status', False):
            return

        # ── Join message ────────────────────────────────────────────────────
        join_data = wel_data.get('join', {})
        joinStatus = join_data.get('status', False)
        joinChannel = join_data.get('channel')
        joinMessage = join_data.get('message', {})
        joinMessageType = joinMessage.get('type')

        if joinStatus and joinChannel:
            channel = self.client.get_channel(int(joinChannel))
            if channel and joinMessageType == "text":
                await channel.send(v.render_placeholders(
                    joinMessage.get('content'),
                    user=member,
                    server=member.guild.name,
                    membercount=member.guild.member_count
                ))

            if channel and joinMessageType == "embed":
                embed_data = joinMessage.get('embed', {})
                em = await self.create_embed(embed_data, member)
                await channel.send(embed=em)
        ###

        # ── Auto Roles ────────────────────────────────────────────────────
        autoRoles_data = wel_data.get("autoRoles", {})
        autoRolesStatus = autoRoles_data.get("status", False)
        autoRolesRoles = autoRoles_data.get("roles", [])

        if autoRolesStatus and autoRolesRoles:
            roles_to_add = [
                role for roleID in autoRolesRoles
                if (role := member.guild.get_role(int(roleID))) is not None
            ]
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Welcome auto-role")
                except (discord.Forbidden, discord.HTTPException):
                    pass

        # ── DM ────────────────────────────────────────────────────
        welcomeDm_data = wel_data.get('dm', {})
        welcomeDm = welcomeDm_data.get('status', False)
        welcomeDmMsg = welcomeDm_data.get('message', {})
        welcomeDmMsgType = welcomeDmMsg.get('type')

        if welcomeDm and not member.bot:
            try:
                if welcomeDmMsgType == "text":
                    await member.send(v.render_placeholders(
                        welcomeDmMsg.get('content', ''),
                        user=member,
                        server=member.guild.name,
                        membercount=member.guild.member_count
                    ))

                elif welcomeDmMsgType == "embed":
                    embed_data = welcomeDmMsg.get('embed', {})
                    em = await self.create_embed(embed_data, member)
                    await member.send(embed=em)
            except (discord.Forbidden, discord.HTTPException):
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        guild_doc = Guild.get(str(member.guild.id)).run()
        if guild_doc is None:
            return

        wel_data = guild_doc.dashboard.welcome

        # Master toggle for the whole Welcome plugin
        if not wel_data.get("status", False):
            return

        # ── Leave message ──────────────────────────────────────
        leave_data = wel_data.get("leave", {})
        leaveStatus = leave_data.get("status", False)
        leaveChan = leave_data.get("channel")
        leaveMessage = leave_data.get("message", {})
        leaveMessageType = leaveMessage.get("type")

        if not (leaveStatus and leaveChan):
            return

        channel = self.client.get_channel(int(leaveChan))
        if not channel:
            return

        if leaveMessageType == "text":
            await channel.send(
                v.render_placeholders(
                    leaveMessage.get("content", ""),
                    user=member,
                    server=member.guild.name,
                    membercount=member.guild.member_count,
                )
            )

        elif leaveMessageType == "embed":
            embed_data = leaveMessage.get("embed", {})
            em = await self.create_embed(embed_data, member)
            await channel.send(embed=em)
        
def setup(client):
    client.add_cog(welcomeSystem(client))