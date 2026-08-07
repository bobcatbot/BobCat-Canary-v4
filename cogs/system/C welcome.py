from discord.ext import commands
from modules import bot as v
from modules.models import Guild

class welcomeSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
        wel_data = Guild.get(str(member.guild.id)).run().dashboard.welcome

        # Master toggle for the whole Welcome plugin
        if not wel_data['status']:
            return

        # ── Join message (independent toggle) ──────────────────────────
        join_data = wel_data['join']
        joinStaus = join_data['status']
        joinChannel = join_data['channel']
        joinMessageType = join_data['message']['type']
        joinMessageContent = join_data['message']['content']
        
        if joinStaus and joinChannel:      
            channel = self.client.get_channel(int(joinChannel))
            if channel and joinMessageType == "text":
                await channel.send(v.render_placeholders(
                    joinMessageContent, 
                    user=member, 
                    server=member.guild.name, 
                    membercount=member.guild.member_count
                ))
        
            # if welcomeMessageType == "embed":
        
        # ── Auto Roles (independent toggle) ─────────────────────────────
        autoRoles_data = wel_data["autoRoles"]
        autoRolesStatus = autoRoles_data["status"]
        autoRolesRoles = autoRoles_data["roles"]
        if autoRolesStatus:
            for roleID in autoRolesRoles:
                role = member.guild.get_role(int(roleID))
                if role:
                    await member.add_roles(role)
        
        # ── DM (independent toggle) ──────────────────────────────────────
        welcomeDm_data = wel_data['dm']
        welcomeDm = welcomeDm_data['status']
        welcomeDmMsg = welcomeDm_data['message']['content']
        if welcomeDm and not member.bot:
            await member.send(v.render_placeholders(
                welcomeDmMsg,
                server=member.guild.name
            ))
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        wel_data = Guild.get(str(member.guild.id)).run().dashboard.welcome

        # Master toggle for the whole Welcome plugin
        if not wel_data['status']:
            return

        leaveStaus = wel_data['leave']['status']
        leaveChan = wel_data['leave']['channel']
        leaveMessage = wel_data['leave']['message']['content']
                
        if not leaveStaus:
            return
        if not leaveChan:
            return
        
        channel = self.client.get_channel(int(leaveChan))
        await channel.send(v.render_placeholders(
            leaveMessage,
            user=member,
            server=member.guild.name,
            membercount=member.guild.member_count,
        ))
        
def setup(client):
    client.add_cog(welcomeSystem(client))