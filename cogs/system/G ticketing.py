import discord
from datetime import datetime
from discord.ext import commands
from modules import bot as v
from modules.models import Guild, Ticket

def get_ticketing(guild: discord.Guild) -> dict:
    return Guild.get(str(guild.id)).run().dashboard.ticketing

def get_guild_tickets(guild: discord.Guild) -> list[Ticket]:
    return Ticket.find(Ticket.guild_id == str(guild.id)).run()

def get_channel_ticket(guild: discord.Guild, channel_id: int) -> Ticket | None:
    return Ticket.find_one(
        Ticket.guild_id == str(guild.id),
        Ticket.channel_id == str(channel_id),
    ).run()

class TicketControls(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client

    @discord.ui.button(emoji="🎟️", label="Claim", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = get_ticketing(interaction.guild)['panels']
        tickets = get_guild_tickets(interaction.guild)

        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)

        panelCategoryClaimed = panel['category_claimed']

        # Prevnt users from claiming their own ticket
        if interaction.user.id == int(ticket.creator_id):
            return await interaction.response.send_message(
                f"> **Warning:** You cannot claim your own ticket.", ephemeral=True
            )

        if ticket.claimed['status'] == True:
            return await interaction.response.send_message(
                f"> **Warning:** This ticket is already claimed by <@{ticket.claimed['user']}>.", ephemeral=True
            )


        move_to = '.'
        if panelCategoryClaimed != '':
            claimed_category = discord.utils.get(interaction.guild.categories, id=int(panelCategoryClaimed))
            await interaction.channel.edit(category=claimed_category)
            
            move_to = f' and it has been moved to **<#{panelCategoryClaimed}>** category' 
        
        ticket.claimed = {
            "status": True,
            "user": interaction.user.id,
            "updated_at": f"{datetime.now()}"
        }
        ticket.claimed_by = str(interaction.user.id)
        ticket.save()

        embed = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, you claimed the ticket{move_to}"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.channel.send(f"{interaction.user.mention} claimed the ticket.")

        button.disabled = True
        button.label = "Claimed"
        msg = await interaction.channel.fetch_message(int(ticket.message_id))
        await msg.edit(view=self)

    @discord.ui.button(emoji="🔒", label="Close", style=discord.ButtonStyle.gray, custom_id="close_ticket", disabled=False)
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = get_ticketing(interaction.guild)['panels']
        tickets = get_guild_tickets(interaction.guild)

        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)

        panelCategoryClose = panel['category_closed']
        
        ctbtns = self
        class MyModal(discord.ui.Modal):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.add_item(discord.ui.InputText(label="Reason", style=discord.InputTextStyle.long))

            async def callback(self, interaction: discord.Interaction):
                move_to = '.'
                if panelCategoryClose != '':
                    closed_category = discord.utils.get(interaction.guild.categories, id=int(panelCategoryClose))
                    await interaction.channel.edit(category=closed_category)
                    
                    move_to = f' and it has been moved to **<#{panelCategoryClose}>** category' 
                
                close_em = discord.Embed(
                    color=0x5865f2,
                    description=f"{interaction.user.mention}, this ticket has been closed{move_to}"
                )
                await interaction.response.send_message(embed=close_em, ephemeral=True)

                ticket.closed = {
                    "status": True,
                    "reason": self.children[0].value,
                    "user": int(interaction.user.id),
                    "updated_at": f"{datetime.now()}"
                }
                ticket.status = "closed"
                ticket.save()

                embed = discord.Embed(title="Close ticket with reason")
                embed.add_field(name="Reason", value=self.children[0].value)
                await interaction.channel.send(embed=embed)

                for child in ctbtns.children:
                    if child.custom_id == "close_ticket":
                        child.disabled = True
                    if child.custom_id == "reopen_ticket":
                        child.disabled = False

                msg = await interaction.channel.fetch_message(int(ticket.message_id))
                await msg.edit(view=ctbtns)
        await interaction.response.send_modal(MyModal(title="Close Ticket Reason"))

    @discord.ui.button(emoji="🔓", label="Reopen", style=discord.ButtonStyle.green, custom_id="reopen_ticket", disabled=True)
    async def reopen_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = get_ticketing(interaction.guild)['panels']
        tickets = get_guild_tickets(interaction.guild)

        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)

        panelCategoryOpen = panel['category_open']

        if ticket.closed['status'] == False:
            return await interaction.response.send_message(embed=discord.Embed(description="This ticket is not closed yet.", color=0x5865f2), ephemeral=True)

        move_to = '.'
        if panelCategoryOpen != '':
            categoryopen = discord.utils.get(interaction.guild.categories, id=int(panelCategoryOpen))
            await interaction.channel.edit(category=categoryopen)
            
            move_to = f' and it has been moved to **<#{panelCategoryOpen}>** category'

        if ticket.closed['status'] == True: # If the ticket is closed, we need to update the database to reflect that it has been reopened
            ticket.closed["status"] = False
            ticket.closed["user"] = ""
            ticket.reopened = {
                "status": True,
                "user": interaction.user.id,
                "updated_at": f"{datetime.now()}"
            }
            ticket.status = "open"
            ticket.save()

        reopen_em = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, you reopened this ticket{move_to}"
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
        panels = get_ticketing(interaction.guild)['panels']
        tickets = get_guild_tickets(interaction.guild)

        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)

        # Prevnt users from deleting their own ticket
        if ticket.closed['status'] == True and ticket.closed['user'] == interaction.user.id:
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

                creator: discord.Member = await interaction.guild.fetch_member(int(ticket.creator_id))

                # if ticket is not closed then close and delete
                if ticket.closed['status'] == False:
                    ticket.closed = {
                        "status": True,
                        "reason": "Ticket deleted",
                        "user": interaction.user.id,
                        "updated_at": f"{datetime.now()}"
                    }

                ticket.deleted = {
                    "status": True,
                    "user": interaction.user.id,
                    "updated_at": f"{datetime.now()}"
                }
                ticket.status = "deleted"
                ticket.save()

                user_message_count = {}

                # Count messages for each user
                for msg in ticket.transcript:
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
                transcript_em.add_field(name="Type", value=f"{panel['panel_button']['emoji']} `{panel['panel_button']['label']}` from Panel in {panel_channel.mention}", inline=False)
                transcript_em.add_field(name="Created by", value=f"<@{ticket.creator_id}> {format_time(ticket.created_at.isoformat())}", inline=False)
                
                if ticket.claimed['status'] == True:
                    transcript_em.add_field(name="Claimed by", value=f"<@{ticket.claimed['user']}> {format_time(ticket.claimed['updated_at'])}", inline=False)
                if ticket.closed['status'] == True:
                    transcript_em.add_field(name="Closed by", value=f"<@{ticket.closed['user']}> {format_time(ticket.closed['updated_at'])}", inline=False)
                if ticket.reopened['status'] == True:
                    transcript_em.add_field(name="Reopened by", value=f"<@{ticket.reopened['user']}> {format_time(ticket.reopened['updated_at'])}", inline=False)
                if ticket.deleted['status'] == True:
                    transcript_em.add_field(name="Deleted by", value=f"<@{ticket.deleted['user']}> {format_time(ticket.deleted['updated_at'])}", inline=False)
                
                transcript_em.add_field(name="Participants", value="\n".join(participants), inline=False)
                
                await interaction.channel.send(f"{interaction.user.mention} closed the ticket.") # Send a message to the channel
                await interaction.channel.delete(reason="Ticket deleted by user.") # Delete the channel

                # Send to the transcript channel
                if panel['transcript_channel'] != '':
                    await interaction.guild.get_channel(int(panel['transcript_channel'])).send(embed=transcript_em)

                if panel['transcript_dm']:
                    await interaction.guild.get_member(int(ticket.creator_id)).send(embed=transcript_em)
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

    # ── Ticket Creation ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") == "create_ticket":
            panels = get_ticketing(interaction.guild)['panels']
            tickets = get_guild_tickets(interaction.guild)
            
            panel = next((p for p in panels if p['channel_id'] == str(interaction.channel.id)), None)
            
            category = discord.utils.get(interaction.guild.categories, id=int(panel['category_open']))

            for channel in category.channels:
                if channel.name == f"{len([t for t in tickets if not t.closed['status']])+1}-{interaction.user.name}".lower():
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
                    f"- Type: {panel['panel_button']['emoji']} {panel['panel_button']['label']}"
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

            Ticket(
                guild_id=str(interaction.guild.id),
                channel_id=str(channel.id),
                message_id=str(msg.id),
                creator_id=str(interaction.user.id),
                creator={
                    "name": interaction.user.name,
                    "avatar": interaction.user.display_avatar.url,
                },
                panel_id=str(panel['id']),
                claimed={"status": False, "user": "", "updated_at": ""},
                closed={"status": False, "reason": "", "user": "", "updated_at": ""},
                reopened={"status": False, "user": "", "updated_at": ""},
                deleted={"status": False, "user": "", "updated_at": ""},
            ).insert()
        ##
    

    # ── Ticketing Transcript Listeners ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.type != discord.MessageType.default:
            return
        if message.guild is None:
            return

        try:
            panels = get_ticketing(message.guild).get('panels', [])
            tickets = get_guild_tickets(message.guild)

            if not tickets or not panels:
                return

            ticket = get_channel_ticket(message.guild, message.channel.id)
            if not ticket:
                return

            msg_content = message.content

            if message.type == discord.MessageType.pins_add:
                msg_content = f"{message.author.nick} pinned a message to this channel. See all pinned messages."

            for user in message.mentions:
                msg_content = msg_content.replace(f"<@{user.id}>", f"@{user.name}")
            for role in message.role_mentions:
                msg_content = msg_content.replace(f"<@&{role.id}>", f"@{role.name}")

            new_entry = {
                "id": str(message.id),
                "user": {
                    "id": str(message.author.id),
                    "name": message.author.display_name,
                    "avatar": message.author.avatar.url if message.author.avatar else message.author.default_avatar.url,
                    "color": int(message.author.color),
                    "bot": message.author.bot
                },
                "content": msg_content,
                "embeds": [embed.to_dict() for embed in message.embeds] if message.embeds else [],
                "attachments": [a.url for a in message.attachments] if message.attachments else [],
                "pin": message.type == discord.MessageType.pins_add,
                "timestamp": {
                    "created": f"{message.created_at}",
                    "formatted": message.created_at.strftime("%d/%m/%Y %H:%M:%S"),
                },
                "channel": {
                    "id": str(message.channel.id),
                    "name": message.channel.name,
                    "catagory": message.channel.category.name
                }
            }

            ticket.transcript.append(new_entry)
            ticket.save()

        except AttributeError:
            return
        except discord.errors.NotFound:
            return

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.type != discord.MessageType.default:
            return
        if message.guild is None:
            return

        try:
            tickets = get_guild_tickets(message.guild)
            if not tickets:
                return

            ticket = get_channel_ticket(message.guild, message.channel.id)
            if not ticket:
                return

            transcript = ticket.transcript
            updated_transcript = [msg for msg in transcript if str(msg['id']) != str(message.id)]

            if len(updated_transcript) != len(transcript):
                ticket.transcript = updated_transcript
                ticket.save()
        except AttributeError:
            return

    # ── Ticket Commands ──────────────────────────────────────────
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