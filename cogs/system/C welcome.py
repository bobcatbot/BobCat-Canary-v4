import discord
from discord.ext import commands
from modules import bot as v

class welcomeSystem(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_member_join(self, member):
        welcomeStaus = v.dashboard(member.guild.id, "welcome.join.status")
        welcomeChannel = v.dashboard(member.guild.id, "welcome.join.channel")
        welcomeMessageType = v.dashboard(member.guild.id, "welcome.join.message.type")
        
        if not welcomeStaus:
            return
        if not welcomeChannel:
            return
                
        channel = self.client.get_channel(int(welcomeChannel))
        
        if welcomeMessageType == "text":
            msg = v.dashboard(member.guild.id, "welcome.join.message.content")
            await channel.send(f"{msg}".format(
                user=member,
                server=member.guild.name,
                membercount=member.guild.member_count,
            ))
        
        if welcomeMessageType == "embed":
            emMessage = v.dashboard(member.guild.id, "WelcomeEmbedMessage")
            msg = emMessage.split("|")
            
            em = discord.Embed(
                color=v.style(member.guild.id),
                title=f"{msg[0]}".format(user=member, server=member.guild.name),
                description=f"{msg[1]}".format(user=member, server=member.guild.name)
            )
            await channel.send(embed=em)
        
        autoRoles = v.dashboard(member.guild.id, "welcome.autoRoles")
        if not autoRoles:
            return
        for roleID in autoRoles['roles']:
            role = member.guild.get_role(int(roleID))
            await member.add_roles(role)
        
        welcomeDm = v.dashboard(member.guild.id, "welcome.dm.status")
        if welcomeDm and not member.bot:
            welcomeDmMsg = v.dashboard(member.guild.id, "welcome.dm.message.content")
            return await member.send(f"{welcomeDmMsg}".format(server=member.guild.name))
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        leaveStaus = v.dashboard(member.guild.id, "welcome.leave.status")
        leaveChan = v.dashboard(member.guild.id, "welcome.leave.channel")
        msg = v.dashboard(member.guild.id, "welcome.leave.message.content")
        
        if not leaveStaus:
            return
        if not leaveChan:
            return
        
        channel = self.client.get_channel(int(leaveChan))
        await channel.send(f"{msg}".format(
            user=member,
            server=member.guild.name,
            membercount=member.guild.member_count,
        ))
        
def setup(client):
    client.add_cog(welcomeSystem(client))