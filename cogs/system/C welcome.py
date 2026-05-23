import discord
from discord.ext import commands
from modules import bot as v

class welcomeSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
        wel_data = v.db.get_dash(member.guild)['welcome']

        welcomeStaus = wel_data['join']['status']
        welcomeChannel = wel_data['join']['channel']
        welcomeMessageType = wel_data['join']['message']['type']
        
        if not welcomeStaus:
            return
        if not welcomeChannel:
            return
                
        channel = self.client.get_channel(int(welcomeChannel))
        
        if welcomeMessageType == "text":
            msg = wel_data['join']['message']['content']
            await channel.send(f"{msg}".format(
                user=member,
                server=member.guild.name,
                membercount=member.guild.member_count,
            ))
        
        # if welcomeMessageType == "embed":
        
        # Auto Roles
        autoRoles = wel_data['autoRoles']
        if not autoRoles['status']:
            return
        for roleID in autoRoles['roles']:
            role = member.guild.get_role(int(roleID))
            await member.add_roles(role)
        
        # DM
        welcomeDm = wel_data['dm']['status']
        if welcomeDm and not member.bot:
            welcomeDmMsg = wel_data['dm']['message']['content']
            return await member.send(f"{welcomeDmMsg}".format(server=member.guild.name))
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        wel_data = v.db.get_dash(member.guild)['welcome']

        leaveStaus = wel_data['leave']['status']
        leaveChan = wel_data['leave']['channel']
        leaveMessage = wel_data['leave']['message']['content']
                
        if not leaveStaus:
            return
        if not leaveChan:
            return
        
        channel = self.client.get_channel(int(leaveChan))
        await channel.send(f"{leaveMessage}".format(
            user=member,
            server=member.guild.name,
            membercount=member.guild.member_count,
        ))
        
def setup(client):
    client.add_cog(welcomeSystem(client))