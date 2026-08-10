import discord
import asyncio
import io
from datetime import datetime, timedelta
from discord.ext import commands, tasks
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
        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)

        if interaction.user.id == int(ticket.creator_id):
            return await interaction.response.send_message("> **Warning:** You cannot claim your own ticket.", ephemeral=True)

        if ticket.claimed['status'] == True:
            return await interaction.response.send_message(f"> **Warning:** This ticket is already claimed by <@{ticket.claimed['user']}>.", ephemeral=True)

        panelCategoryClaimed = panel.get('category_claimed', '')
        move_to = '.'
        if panelCategoryClaimed:
            claimed_category = discord.utils.get(interaction.guild.categories, id=int(panelCategoryClaimed))
            if claimed_category:
                await interaction.channel.edit(category=claimed_category)
                move_to = f' and it has been moved to **{claimed_category.name}** category'

        ticket.claimed = {
            "status": True,
            "user": interaction.user.id,
            "updated_at": f"{datetime.now()}"
        }
        ticket.claimed_by = str(interaction.user.id)
        ticket.save()

        embed = discord.Embed(color=0x5865f2, description=f"{interaction.user.mention}, you claimed the ticket{move_to}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.channel.send(f"{interaction.user.mention} claimed the ticket.")

        button.disabled = True
        button.label = "Claimed"
        msg = await interaction.channel.fetch_message(int(ticket.message_id))
        await msg.edit(view=self)

    @discord.ui.button(emoji="🔒", label="Close", style=discord.ButtonStyle.gray, custom_id="close_ticket")
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = get_ticketing(interaction.guild)['panels']
        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)
        panelCategoryClose = panel.get('category_closed', '')
        
        ctbtns = self
        
        class MyModal(discord.ui.Modal):
            def __init__(self, *args, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                self.add_item(discord.ui.InputText(label="Reason", style=discord.InputTextStyle.long))

            async def callback(self, interaction: discord.Interaction):
                move_to = '.'
                if panelCategoryClose:
                    closed_category = discord.utils.get(interaction.guild.categories, id=int(panelCategoryClose))
                    if closed_category:
                        await interaction.channel.edit(category=closed_category)
                        move_to = f' and it has been moved to **{closed_category.name}** category'

                close_em = discord.Embed(color=0x5865f2, description=f"{interaction.user.mention}, this ticket has been closed{move_to}")
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
        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)
        panelCategoryOpen = panel.get('category_open', '')

        if ticket.closed['status'] == False:
            return await interaction.response.send_message(embed=discord.Embed(description="This ticket is not closed yet.", color=0x5865f2), ephemeral=True)

        move_to = '.'
        if panelCategoryOpen:
            categoryopen = discord.utils.get(interaction.guild.categories, id=int(panelCategoryOpen))
            if categoryopen:
                await interaction.channel.edit(category=categoryopen)
                move_to = f' and it has been moved to **{categoryopen.name}** category'

        ticket.closed["status"] = False
        ticket.closed["user"] = ""
        ticket.reopened = {
            "status": True,
            "user": interaction.user.id,
            "updated_at": f"{datetime.now()}"
        }
        ticket.status = "open"
        ticket.save()

        reopen_em = discord.Embed(color=0x5865f2, description=f"{interaction.user.mention}, you reopened this ticket{move_to}")
        await interaction.response.send_message(embed=reopen_em, ephemeral=True)

        embed = discord.Embed(title="Ticket reopened.")
        embed.add_field(name="Reopened by", value=f"<@{interaction.user.id}>")
        await interaction.channel.send(embed=embed)

        for child in self.children:
            if child.custom_id == "close_ticket":
                child.disabled = False
            if child.custom_id == "reopen_ticket":
                child.disabled = True

        msg = await interaction.channel.fetch_message(int(ticket.message_id))
        await msg.edit(view=self)

    @discord.ui.button(emoji="🗑️", label="Delete", style=discord.ButtonStyle.red, custom_id="delete_ticket")
    async def delete_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        panels = get_ticketing(interaction.guild)['panels']
        ticket = get_channel_ticket(interaction.guild, interaction.channel.id)
        panel = next((p for p in panels if p['id'] == ticket.panel_id), None)

        if ticket.closed['status'] == True and ticket.closed['user'] == interaction.user.id:
            return await interaction.response.send_message("> **Warning:** You cannot delete your own ticket. Please close it first.", ephemeral=True)

        delete_confirm_em = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, are you sure you want to delete this ticket? The channel will be deleted and a transcript will be generated."
        )
        
        class DeleteTicketConfirm(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
                
            @discord.ui.button(emoji="🗑️", label="Confirm", style=discord.ButtonStyle.red, custom_id="confirm_delete")
            async def confirm_delete(self, button: discord.ui.Button, interaction: discord.Interaction):
                await interaction.response.defer(invisible=False, ephemeral=True)

                creator: discord.Member = await interaction.guild.fetch_member(int(ticket.creator_id))

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

                await interaction.channel.send(f"{interaction.user.mention} deleted the ticket.")
                
                # FIX: Generate transcript data and file in threads
                transcript_data = await self._generate_transcript(ticket, interaction.guild, creator, panel)
                
                # Send transcript to log channel
                if panel.get('transcript_channel'):
                    log_channel = interaction.guild.get_channel(int(panel['transcript_channel']))
                    if log_channel:
                        # FIX: Correct asyncio.to_thread usage
                        file = await asyncio.to_thread(
                            self._create_transcript_file, 
                            transcript_data['text'], 
                            ticket.id[:8]
                        )
                        await log_channel.send(file=file, embed=transcript_data['embed'])
                
                if panel.get('transcript_dm'):
                    try:
                        file = await asyncio.to_thread(
                            self._create_transcript_file, 
                            transcript_data['text'], 
                            ticket.id[:8]
                        )
                        await creator.send(file=file, embed=transcript_data['embed'])
                    except:
                        pass

                await interaction.channel.delete(reason="Ticket deleted by user.")

            async def _generate_transcript(self, ticket, guild, creator, panel):
                """Generate transcript data (CPU-bound work)."""
                user_message_count = {}
                for msg in ticket.transcript:
                    user_id = msg['user']['id']
                    if msg['user']['bot']:
                        continue
                    user_message_count[user_id] = user_message_count.get(user_id, 0) + 1
                
                participants = [f"{count} messages by <@{user_id}>" for user_id, count in user_message_count.items()]

                def format_time(time):
                    time = datetime.fromisoformat(time)
                    return f'<t:{int(time.timestamp())}:R>'

                transcript_em = discord.Embed(
                    color=0x5865f2,
                    title=f"Ticket #{ticket.id[:8]} in {guild.name}",
                    timestamp=datetime.now()
                )
                transcript_em.set_author(name=creator.name, icon_url=creator.avatar.url if creator.avatar else None)
                transcript_em.add_field(name="Type", value=f"{panel['panel_button']['emoji']} `{panel['panel_button']['label']}`", inline=False)
                transcript_em.add_field(name="Created by", value=f"<@{ticket.creator_id}> {format_time(ticket.created_at.isoformat())}", inline=False)
                
                if ticket.claimed['status']:
                    transcript_em.add_field(name="Claimed by", value=f"<@{ticket.claimed['user']}> {format_time(ticket.claimed['updated_at'])}", inline=False)
                if ticket.closed['status']:
                    transcript_em.add_field(name="Closed by", value=f"<@{ticket.closed['user']}> {format_time(ticket.closed['updated_at'])}", inline=False)
                if ticket.reopened['status']:
                    transcript_em.add_field(name="Reopened by", value=f"<@{ticket.reopened['user']}> {format_time(ticket.reopened['updated_at'])}", inline=False)
                if ticket.deleted['status']:
                    transcript_em.add_field(name="Deleted by", value=f"<@{ticket.deleted['user']}> {format_time(ticket.deleted['updated_at'])}", inline=False)
                
                transcript_em.add_field(name="Participants", value="\n".join(participants) or "No participants", inline=False)
                
                # Build text transcript
                transcript_text = f"Ticket #{ticket.id[:8]} - {guild.name}\n"
                transcript_text += "=" * 50 + "\n\n"
                for msg in ticket.transcript:
                    timestamp = msg['timestamp']['formatted']
                    author = msg['user']['name']
                    content = msg['content']
                    transcript_text += f"[{timestamp}] {author}: {content}\n"
                    if msg.get('attachments'):
                        for att in msg['attachments']:
                            transcript_text += f"  📎 {att}\n"
                
                return {"embed": transcript_em, "text": transcript_text}

            def _create_transcript_file(self, text: str, ticket_id: str) -> discord.File:
                """Create transcript file (runs in thread pool)."""
                text_file = io.BytesIO()
                text_file.write(text.encode('utf-8'))
                text_file.seek(0)
                return discord.File(text_file, filename=f"ticket_{ticket_id}.txt")

        await interaction.response.send_message(embed=delete_confirm_em, view=DeleteTicketConfirm(), ephemeral=True)

class Ticketing(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False
        self.ticket_timeouts = {}  # {channel_id: expiry_time}
        self.auto_close_timeout = 86400  # 24 hours
        self.auto_close_check.start()

    @tasks.loop(minutes=30)
    async def auto_close_check(self):
        """Auto-close tickets after 24 hours of inactivity."""
        now = datetime.now()
        for channel_id, expiry in list(self.ticket_timeouts.items()):
            if now > expiry:
                channel = self.client.get_channel(channel_id)
                if channel:
                    ticket = get_channel_ticket(channel.guild, channel.id)
                    if ticket and ticket.status == "open":
                        ticket.closed = {
                            "status": True,
                            "reason": "Auto-closed due to 24 hours of inactivity",
                            "user": 0,
                            "updated_at": f"{datetime.now()}"
                        }
                        ticket.status = "closed"
                        ticket.save()
                        
                        try:
                            await channel.send("🔒 This ticket has been auto-closed due to 24 hours of inactivity.")
                            msg = await channel.fetch_message(int(ticket.message_id))
                            view = TicketControls(self.client)
                            for child in view.children:
                                if child.custom_id == "close_ticket":
                                    child.disabled = True
                                if child.custom_id == "reopen_ticket":
                                    child.disabled = False
                            await msg.edit(view=view)
                        except:
                            pass
                        
                        self.ticket_timeouts.pop(channel_id, None)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            self.client.add_view(TicketControls(self.client))
            self.persistent_views_added = True
            
        if not self.auto_close_check.is_running():
            self.auto_close_check.start()

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
                    return await interaction.response.send_message("> **Warning:** You already have an open ticket", ephemeral=True)
                
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

            self.ticket_timeouts[channel.id] = datetime.now() + timedelta(seconds=self.auto_close_timeout)

            move_to = '.'
            if panel['category_open']:
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

            if ticket.status == "open":
                self.ticket_timeouts[message.channel.id] = datetime.now() + timedelta(seconds=self.auto_close_timeout)

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
                    "catagory": message.channel.category.name if message.channel.category else None
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