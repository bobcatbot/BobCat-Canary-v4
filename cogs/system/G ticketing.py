import discord
import asyncio
from datetime import datetime
from discord.ext import commands
from modules import bot as v

class TicketControls(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client

    @discord.ui.button(emoji="🎟️", label="Claim", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = v.db.get_dash(interaction.guild)['ticketing']['pannels']
        tickets = v.db.get_server_config(interaction.guild)['tickets']

        panel_dict = {panel['id']: panel for panel in panels}
        for _ticket in tickets:
            panel = panel_dict.get(_ticket['pannelid'])
            
            if _ticket['channelid'] == str(interaction.channel.id):
                ticket = _ticket

        # Prevnt users from claiming their own ticket
        if interaction.user.id == int(ticket['creator']['id']):
            return await interaction.response.send_message(
                f"> **Warning:** You cannot claim your own ticket.", ephemeral=True
            )

        if ticket['claimed']['status'] == True:
            return await interaction.response.send_message(
                f"> **Warning:** This ticket is already claimed by <@{ticket['claimed']['user']}>.", ephemeral=True
            )

        claimed_category = discord.utils.get(interaction.guild.categories, id=int(panel['category_claimed']))

        await interaction.channel.edit(category=claimed_category)

        move_to = '.'
        if panel['category_claimed'] != '':
            move_to = f' and it has been moved to **<#{panel["category_claimed"]}>** category' 
        
        ticket_idx = tickets.index(ticket)
        v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.claimed', value={
            "status": True,
            "user": f"{interaction.user.id}",
            "updated_at": f"{datetime.now()}"
        })

        embed = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, you claimed the ticket{move_to}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.channel.send(f"{interaction.user.mention} claimed the ticket.")

        button.disabled = True
        button.label = "Claimed"
        msg = await interaction.channel.fetch_message(int(ticket['messageid']))
        await msg.edit(view=self)

    @discord.ui.button(emoji="🔒", label="Close", style=discord.ButtonStyle.gray, custom_id="close_ticket", disabled=False)
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = v.db.get_dash(interaction.guild)['ticketing']['pannels']
        tickets = v.db.get_server_config(interaction.guild)['tickets']

        panel_dict = {panel['id']: panel for panel in panels}
        for _ticket in tickets:
            panel = panel_dict.get(_ticket['pannelid'])

            if _ticket['channelid'] == str(interaction.channel.id):
                ticket = _ticket
        
        ctbtns = self
        class MyModal(discord.ui.Modal):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.add_item(discord.ui.InputText(label="Reason", style=discord.InputTextStyle.long))

            async def callback(self, interaction: discord.Interaction):
                closed_category = discord.utils.get(interaction.guild.categories, id=int(panel['category_closed']))

                await interaction.channel.edit(category=closed_category)

                move_to = '.'
                if panel['category_closed'] != '':
                    move_to = f' and it has been moved to **<#{panel["category_closed"]}>** category' 
                
                close_em = discord.Embed(
                    color=0x5865f2,
                    description=f"{interaction.user.mention}, this ticket has been closed{move_to}"
                )
                await interaction.response.send_message(embed=close_em, ephemeral=True)

                ticket_idx = tickets.index(ticket)
                v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.closed', value={
                    "status": True,
                    "reason": self.children[0].value,
                    "user": f"{interaction.user.id}",
                    "updated_at": f"{datetime.now()}"
                })

                embed = discord.Embed(title="Close ticket with reason")
                embed.add_field(name="Reason", value=self.children[0].value)
                await interaction.channel.send(embed=embed)

                for child in ctbtns.children:
                    if child.custom_id == "close_ticket":
                        child.disabled = True
                    if child.custom_id == "reopen_ticket":
                        child.disabled = False

                msg = await interaction.channel.fetch_message(int(ticket['messageid']))
                await msg.edit(view=ctbtns)
                return
        await interaction.response.send_modal(MyModal(title="Close Ticket Reason"))

    @discord.ui.button(emoji="🔓", label="Reopen", style=discord.ButtonStyle.green, custom_id="reopen_ticket", disabled=True)
    async def reopen_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = v.db.get_dash(interaction.guild)['ticketing']['pannels']
        tickets = v.db.get_server_config(interaction.guild)['tickets']

        panel_dict = {panel['id']: panel for panel in panels}
        for _ticket in tickets:
            panel = panel_dict.get(_ticket['pannelid'])
            
            if _ticket['channelid'] == str(interaction.channel.id):
                ticket = _ticket

                ticket_idx = tickets.index(ticket)

        if ticket['closed']['status'] == False:
            return await interaction.response.send_message(embed=discord.Embed(description="This ticket is not closed yet.", color=0x5865f2), ephemeral=True)

        category_openn = discord.utils.get(interaction.guild.categories, id=int(panel['category_open']))

        await interaction.channel.edit(category=category_openn)

        move_to = '.'
        if panel['category_open'] != '':
            move_to = f' and it has been moved to **<#{panel["category_open"]}>** category'

        if ticket['closed']['status'] == True:
            ticket_idx = tickets.index(ticket)
            v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.closed.status', value=False)
            v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.closed.user', value='')

            v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.reopened.status', value=True)
            v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.reopened', value={
                "status": True,
                "user": f"{interaction.user.id}",
                "updated_at": f"{datetime.now()}"
            })

        reopen_em = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, you reopened htis ticket{move_to}"
        )

        await interaction.response.send_message(embed=reopen_em, ephemeral=True)

        embed = discord.Embed(title="Ticket reopened.")
        embed.add_field(name="Reopened by", value=f"<@{interaction.user.id}>")
        await interaction.channel.send(embed=embed)

        for child in self.children:
            if child.custom_id == "close_ticket":
                child.disabled = False
            if child.custom_id == "reopen_ticket":
                child.disabled = True
        
        msg = await interaction.channel.fetch_message(int(interaction.message.id))
        await msg.edit(view=self)

    @discord.ui.button(emoji="🗑️", label="Delete", style=discord.ButtonStyle.red, custom_id="delete_ticket")
    async def delete_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = v.db.get_dash(interaction.guild)['ticketing']['pannels']
        tickets = v.db.get_server_config(interaction.guild)['tickets']

        panel_dict = {panel['id']: panel for panel in panels}
        for _ticket in tickets:
            panel = panel_dict.get(_ticket['pannelid'])
            
            if _ticket['channelid'] == str(interaction.channel.id):
                ticket = _ticket
                ticket_idx = tickets.index(ticket)

        # Prevnt users from deleting their own ticket
        if ticket['closed']['status'] == True and ticket['closed']['user'] == interaction.user.id:
            return await interaction.response.send_message(
                f"> **Warning:** You cannot delete your own ticket. Please close it first.", ephemeral=True
            )

        delete_confirm_em = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, are you sure you want to delete this ticket? \nThe channel will be deleted and a transcript will be generated (soon)."
        )
        class DeleteTicketConfirm(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(emoji="🗑️", label="Confirm", style=discord.ButtonStyle.red, custom_id="open_ticket")
            async def open_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.defer(invisible=False, ephemeral=True)

                creator: discord.Member = await interaction.guild.fetch_member(ticket['creator']['id'])

                # if ticket is not closed then close and delete
                if ticket['closed']['status'] == False: 
                    v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.closed.status', value=True)
                    v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.closed.user', value=interaction.user.id)
                    v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.closed.updated_at', value=f"{datetime.now()}")
                
                v.db.update_server_config(interaction.guild, key=f'tickets.{ticket_idx}.deleted', value={
                    'status': True,
                    'user': interaction.user.id,
                    'updated_at': f"{datetime.now()}"
                })

                user_message_count = {}

                # Count messages for each user
                for msg in ticket['transcript']:
                    user_id = msg['user']['id']
                    
                    if msg['user']['bot']:
                        continue
                    if user_id in user_message_count:
                        user_message_count[user_id] += 1
                    else:
                        user_message_count[user_id] = 1
                participants = [
                    f"{count} messages by `{user_id}` <@{user_id}>"
                    for user_id, count in user_message_count.items()
                ]

                def format_time(time):
                    time = datetime.fromisoformat(time)
                    epoch_end = int(time.timestamp())
                    return f'<t:{epoch_end}:R>'
                
                panel_channel = await interaction.guild.fetch_channel(int(panel['channel_id']))

                transcript_em = discord.Embed(
                    color=0x5865f2,
                    title=f"Ticket #{len(tickets)} in {interaction.guild.name}",
                )
                transcript_em.set_author(name=creator.name, icon_url=creator.avatar.url)
                transcript_em.add_field(name="Type", value=f"{panel['pannel_button']['emoji']} `{panel['pannel_button']['label']}` from Panel in {panel_channel.mention}", inline=False)
                transcript_em.add_field(name="Created by", value=f"<@{ticket['creator']['id']}> {format_time(ticket['created_at'])}", inline=False)
                
                if ticket['claimed']['status'] == True:
                    transcript_em.add_field(name="Claimed by", value=f"<@{ticket['claimed']['user']}> {format_time(ticket['claimed']['updated_at'])}", inline=False)
                if ticket['closed']['status'] == True:
                    transcript_em.add_field(name="Closed by", value=f"<@{ticket['closed']['user']}> {format_time(ticket['closed']['updated_at'])}", inline=False)
                if ticket['reopened']['status'] == True:
                    transcript_em.add_field(name="Reopened by", value=f"<@{ticket['reopened']['user']}> {format_time(ticket['reopened']['updated_at'])}", inline=False)
                if ticket['deleted']['status'] == True:
                    transcript_em.add_field(name="Deleted by", value=f"<@{ticket['deleted']['user']}> {format_time(ticket['deleted']['updated_at'])}", inline=False)
                
                transcript_em.add_field(name="Participants", value="\n".join(participants), inline=False)
                
                await interaction.channel.send(f"{interaction.user.mention} closed the ticket.") # Send a message to the channel
                await interaction.channel.delete(reason="Ticket deleted by user.") # Delete the channel

                # Send to the transcript channel
                if panel['transcript_channel'] != '':
                    await interaction.guild.get_channel(int(panel['transcript_channel'])).send(embed=transcript_em)

                if panel['transcript_dm']:
                    await interaction.guild.get_member(int(ticket['creator']['id'])).send(embed=transcript_em)
        ##
        await interaction.response.send_message(embed=delete_confirm_em, view=DeleteTicketConfirm(), ephemeral=True)

class Ticketing(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.client.add_view(TicketControls(self.client))
            self.persistent_views_added = True

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") == "create_ticket":
            panels = v.db.get_dash(interaction.guild)['ticketing']['pannels']
            tickets = v.db.get_server_config(interaction.guild)['tickets']
            
            panel_dict = {panel['channel_id']: panel for panel in panels}
            panel = panel_dict.get(str(interaction.channel.id))
            
            category = discord.utils.get(interaction.guild.categories, id=int(panel['category_open']))

            for channel in category.channels:
                if channel.name == f"{len([t for t in tickets if not t['closed']['status']])+1}-{interaction.user.name}".lower():
                    return await interaction.response.send_message(
                        "> **Warning:** You already have an open ticket", ephemeral=True
                    )
                
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
                **{
                    interaction.guild.get_role(int(role_str)): discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
                    for role_str in panel['manager_roles']
                }
            }
            
            channel = await interaction.guild.create_text_channel(
                f"{len(tickets)+1}-{interaction.user.name}".lower(), 
                category=category, 
                overwrites=overwrites,
                topic=(
                    f"- Type: {panel['pannel_button']['emoji']} {panel['pannel_button']['label']}"
                    f"\n- Created by: {interaction.user.mention}"
                ),
            )

            move_to = '.'
            if panel['category_open'] != '':
                move_to = f' and it has been moved to **<#{panel["category_open"]}>** category' 

            create_em = discord.Embed(
                color=0x5865f2,
                title="Ticket created",
                description=f"{interaction.user.mention}, your ticket has been created{move_to}"
            )
            create_em.add_field(name=f"Ticket #{len(tickets)+1}", value=f"{channel.mention}", inline=False)
            await interaction.response.send_message(embed=create_em, ephemeral=True)

            embed = discord.Embed.from_dict(panel['intro_message']['embed'])
            msg: discord.Message = await channel.send(embed=embed, view=TicketControls(self.client))
            await msg.pin()

            data = {
                "id": v.uuid(12, strCase="upper/lower/nums"),
                "channelid": f"{channel.id}",
                "messageid": f"{msg.id}",
                "pannelid": f"{panel['id']}",
                "created_at": f"{datetime.now()}",
                "creator": {
                    "id": f"{interaction.user.id}",
                    "name": f"{interaction.user.name}",
                    "avatar": f"{interaction.user.avatar.url}",
                },
                "claimed": { "status": False, "user": "", "updated_at": "" },
                "closed": { "status": False, "user": "", "updated_at": "" },
                "reopened": { "status": False, "user": "", "updated_at": "" },
                "deleted": { "status": False, "user": "", "updated_at": "" },
                "transcript": []
            }

            v.db.update_server_config(interaction.guild, key=f'tickets.{len(tickets)}', value=data)
        ##
    ##

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore non-default message types
        if message.type != discord.MessageType.default:
            return

        # Delay processing to prevent race conditions
        await asyncio.sleep(0.5)

        try:
            # Retrieve ticketing data
            pannels = v.db.get_dash(message.guild).get('ticketing', {}).get('pannels', [])
            tickets = v.db.get_server_config(message.guild).get('tickets', [])

            if not tickets or not pannels:
                return

            # Find the ticket associated with the current channel
            ticket = next((ticket for ticket in tickets if ticket['channelid'] == str(message.channel.id)), None)
            if not ticket:
                return  # Ignore messages from non-ticket channels

            # Initialize transcript
            transcript = []

            # Fetch the channel history
            history = message.channel.history(limit=None, oldest_first=True)
            async for msg in history:
                msg_content = msg.content

                # Handle system messages (e.g., pins)
                if msg.type == discord.MessageType.pins_add:
                    msg_content = f"{msg.author.nick} pinned a message to this channel. See all pinned messages."

                # Replace mentions with readable formats
                for user in msg.mentions:
                    msg_content = msg_content.replace(f"<@{user.id}>", f"@{user.name}")
                for role in msg.role_mentions:
                    msg_content = msg_content.replace(f"<@&{role.id}>", f"@{role.name}")

                # Append message details to the transcript
                transcript.append({
                    "user": {
                        "id": msg.author.id,
                        "name": msg.author.display_name,
                        "avatar": msg.author.avatar.url if msg.author.avatar else msg.author.default_avatar.url,
                        "color": next((role.color.value for role in msg.author.roles if role.hoist), ''),
                        "bot": msg.author.bot
                    },
                    "id": msg.id,
                    "content": msg_content,
                    "embeds": [embed.to_dict() for embed in msg.embeds] if msg.embeds else '',
                    "attachments": [attachment.url for attachment in msg.attachments] if msg.attachments else '',
                    "timestamp": {
                        "created": f"{msg.created_at}",
                        "formatted": msg.created_at.strftime("%d/%m/%Y %H:%M:%S"),
                    },
                })

            # Update the database with the transcript
            ticket_idx = tickets.index(ticket)
            v.db.update_server_config(message.guild, key=f'tickets.{ticket_idx}.transcript', value=transcript)

        except AttributeError:
            # Handle cases where attributes are missing (e.g., invalid guild or message data)
            return
        except discord.errors.NotFound:
            # Handle cases where the channel or message is not found
            return
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        # Ignore non-default message types
        if message.type != discord.MessageType.default:
            return

        try:
            # Retrieve ticketing and transcript data
            tickets = v.db.get_server_config(message.guild).get('tickets', [])

            if not tickets:
                return

            # Locate the ticket associated with the current channel
            ticket = next((ticket for ticket in tickets if ticket['channelid'] == str(message.channel.id)), None)
            if not ticket:
                return  # Ignore messages from non-ticket channels

            # Remove the deleted message from the transcript
            transcript = ticket.get('transcript', [])
            updated_transcript = [msg for msg in transcript if msg['id'] != str(message.id)]

            # Update the database if a message was removed
            if len(updated_transcript) != len(transcript):
                ticket_idx = tickets.index(ticket)
                v.db.update_server_config(message.guild, key=f'tickets.{ticket_idx}.transcript', value=updated_transcript)

        except AttributeError:
            # Handle cases where attributes are missing (e.g., invalid guild or message data)
            return
    

    # Commands
    @commands.slash_command(name="ticket-add", description="Adds a user to a ticket")
    @discord.option(name="user", type=discord.User, description="The user to add to the ticket", required=True)
    async def ticket_add(self, ctx: discord.ApplicationContext, user: discord.User):
        overwrites = discord.PermissionOverwrite()
        overwrites.read_messages = True
        overwrites.send_messages = True
        overwrites.read_message_history = True
        await ctx.interaction.channel.set_permissions(user, overwrite=overwrites)

        await ctx.respond(f"> **{user.mention}** was added to the ticket.")

    @commands.slash_command(name="ticket-remove", description="Removes a user from a ticket")
    @discord.option(name="user", type=discord.User, description="The user to remove from the ticket", required=True)
    async def ticket_remove(self, ctx: discord.ApplicationContext, user: discord.User):
        overwrites = discord.PermissionOverwrite()
        overwrites.read_messages = False
        overwrites.send_messages = False
        overwrites.read_message_history = False
        await ctx.interaction.channel.set_permissions(user, overwrite=overwrites)

        await ctx.respond(f"> **{user.mention}** was removed from the ticket.")

def setup(client):
    client.add_cog(Ticketing(client))