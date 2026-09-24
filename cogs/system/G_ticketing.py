import discord
import asyncio
import io
from datetime import datetime, timedelta, timezone
from discord.ext import commands, tasks
from pymongo.errors import DuplicateKeyError
from modules import bot as v
from modules.models import Guild, Ticket, TicketingConfig, TicketMessage, TicketPanelConfig

AUTO_CLOSE_TIMEOUT = 86400  # 24 hours

# ── Data access ──────────────────────────────────────────────────────────

async def get_ticketing(guild: discord.Guild) -> TicketingConfig:
    return (await Guild.get(str(guild.id))).dashboard.ticketing

async def get_guild_tickets(guild: discord.Guild) -> list[Ticket]:
    return await Ticket.find(Ticket.guild_id == str(guild.id)).to_list()

async def get_channel_ticket(guild: discord.Guild, channel_id: int) -> Ticket | None:
    return await Ticket.find_one(
        Ticket.guild_id == str(guild.id),
        Ticket.channel_id == str(channel_id),
    )

async def get_ticket_and_panel(guild: discord.Guild, channel_id: int) -> tuple[Ticket | None, TicketPanelConfig | None]:
    """Fetch a channel's ticket along with the panel it was created from."""
    panels = (await get_ticketing(guild)).panels
    ticket = await get_channel_ticket(guild, channel_id)
    if ticket is None:
        return None, None
    panel = next((p for p in panels if p.id == ticket.panel_id), None)
    return ticket, panel

async def get_ticket_transcript(ticket: Ticket) -> list[dict]:
    """Return a ticket's transcript as normalized dicts.

    Reads the per-message `TicketMessage` collection when present, falling
    back to the legacy embedded `Ticket.transcript` list for tickets created
    before that collection existed.
    """
    records = await TicketMessage.find(TicketMessage.ticket_id == str(ticket.id)).sort("+created_at").to_list()
    if records:
        tz = v.datetimes(ticket.guild_id)
        # Mongo hands datetimes back naive; they were stored as UTC.
        local = lambda dt: dt.replace(tzinfo=timezone.utc).astimezone(tz)
        fmt = lambda dt: local(dt).strftime("%d/%m/%Y %H:%M:%S") if dt else None
        return [{
            "id": m.id,
            "user": m.user,
            "content": m.content,
            "embeds": m.embeds,
            "attachments": m.attachments,
            "pin": m.pin,
            "deleted": m.deleted,
            "edited": m.edited,
            "timestamp": {
                "created": m.created_at.isoformat(),
                "formatted": fmt(m.created_at),
                "edited": fmt(m.edited_at),
                "deleted": fmt(m.deleted_at),
            },
            "channel": {"id": m.channel_id},
        } for m in records]
    return ticket.transcript

# ── Shared state-transition helpers ─────────────────────────────────────

def _status_entry(client, user_id, reason: str | None = None) -> dict:
    user = client.get_user(int(user_id))
    entry = {
        "status": True,
        "user": {
            "id": str(user_id),
            "name": user.display_name if user else str(user_id),
            "avatar": user.display_avatar.url if user else None,
        },
        "updated_at": f"{datetime.now()}",
    }
    if reason is not None:
        entry["reason"] = reason
    return entry

async def _move_to_category(channel, category_id: str | None, guild: discord.Guild) -> str:
    """Move a channel-based ticket to `category_id` (no-op for threads). Returns a note for the response embed."""
    category = discord.utils.get(guild.categories, id=int(category_id)) if category_id else None
    if await _set_ticket_channel_state(channel, category=category):
        return f' and it has been moved to **{category.name}** category'
    return '.'

async def _set_ticket_channel_state(channel, *, category=None, archived=None, locked=None) -> bool:
    """Apply a ticket-state transition to its channel.

    Thread-mode tickets are archived/locked (per `archived`/`locked`); regular
    tickets are moved to `category` instead. Both HTTPException from the
    thread edit are swallowed, matching prior per-call-site behavior.
    Returns True if a category move happened (for building "moved to X" text).
    """
    if isinstance(channel, discord.Thread):
        kwargs = {k: v for k, v in {"archived": archived, "locked": locked}.items() if v is not None}
        if kwargs:
            try:
                await channel.edit(**kwargs)
            except discord.HTTPException:
                pass
        return False
    elif category is not None:
        await channel.edit(category=category)
        return True
    return False

def _set_button_state(view: discord.ui.View, **states: bool):
    """Set `disabled` on view buttons by custom_id, e.g. _set_button_state(view, close_ticket=True)."""
    for child in view.children:
        if child.custom_id in states:
            child.disabled = states[child.custom_id]

async def _refresh_ticket_message(channel, ticket: Ticket, view: discord.ui.View):
    msg = await channel.fetch_message(int(ticket.message_id))
    await msg.edit(view=view)

# ── Transcript generation ───────────────────────────────────────────────

async def generate_transcript_data(ticket: Ticket, messages: list[dict], guild: discord.Guild, creator: discord.Member, panel: TicketPanelConfig) -> dict:
    """Generate transcript data (CPU-bound work)."""
    ticket_id = str(ticket.id)
    short_id = ticket_id[:8]
    user_message_count = {}
    for msg in messages:
        user_id = msg['user']['id']
        if msg['user']['bot']:
            continue
        user_message_count[user_id] = user_message_count.get(user_id, 0) + 1

    participants = [f"{count} messages by <@{user_id}>" for user_id, count in user_message_count.items()]

    def format_time(time_str):
        try:
            time = datetime.fromisoformat(time_str)
            return f'<t:{int(time.timestamp())}:R>'
        except (ValueError, TypeError):
            return time_str

    transcript_em = discord.Embed(
        color=0x5865f2,
        title=f"Ticket #{short_id} in {guild.name}",
        timestamp=datetime.now()
    )
    transcript_em.set_author(name=creator.name, icon_url=creator.avatar.url if creator.avatar else None)
    transcript_em.add_field(name="Type", value=f"{panel.panel_button.emoji} `{panel.panel_button.label}`", inline=False)
    transcript_em.add_field(name="Created by", value=f"<@{ticket.creator_id}> {format_time(ticket.created_at.isoformat())}", inline=False)

    for field_name, entry in (
        ("Claimed by", ticket.claimed),
        ("Closed by", ticket.closed),
        ("Reopened by", ticket.reopened),
        ("Deleted by", ticket.deleted),
    ):
        if entry and entry.get('status'):
            transcript_em.add_field(
                name=field_name,
                value=f"<@{entry.get('user', {}).get('id', '')}> {format_time(entry.get('updated_at', ''))}",
                inline=False
            )

    transcript_em.add_field(name="Participants", value="\n".join(participants) or "No participants", inline=False)

    transcript_url = f"{v.web_url}/t/{guild.id}/{ticket_id}"

    # Build text transcript
    transcript_text = f"Ticket #{short_id} - {guild.name}\n"
    transcript_text += "=" * 50 + "\n\n"
    for msg in messages:
        timestamp = msg.get('timestamp', {}).get('formatted', 'Unknown')
        author = msg.get('user', {}).get('name', 'Unknown')
        content = msg.get('content', '')
        transcript_text += f"[{timestamp}] {author}: {content}\n"
        # Bot notices (close reason, reopen notice, etc.) are almost always
        # embed-only - content is empty and the actual info lives in the
        # embed, which this loop otherwise never looks at, silently dropping
        # it from the exported .txt even though it's saved fine in the DB.
        for embed in msg.get('embeds') or []:
            if embed.get('title'):
                transcript_text += f"  [embed] {embed['title']}\n"
            if embed.get('description'):
                transcript_text += f"  {embed['description']}\n"
            for field in embed.get('fields') or []:
                name = field.get('name', '')
                value = field.get('value', '')
                transcript_text += f"  {name}: {value}\n"
        if msg.get('attachments'):
            for att in msg['attachments']:
                transcript_text += f"  📎 {att}\n"

    return {"embed": transcript_em, "text": transcript_text, "url": transcript_url}

def create_transcript_file(text: str, ticket_id: str) -> discord.File:
    """Create transcript file (runs in thread pool)."""
    text_file = io.BytesIO()
    text_file.write(text.encode('utf-8'))
    text_file.seek(0)
    return discord.File(text_file, filename=f"ticket_{ticket_id}.txt")

async def send_transcript(ticket: Ticket, guild: discord.Guild, panel: TicketPanelConfig, channel: discord.abc.Messageable):
    """Build the transcript and deliver it to the panel's log channel / creator's DMs, per panel settings."""
    creator: discord.Member = await guild.fetch_member(int(ticket.creator_id))
    messages = await get_ticket_transcript(ticket)
    transcript_data = await generate_transcript_data(ticket, messages, guild, creator, panel)

    transcript_view = discord.ui.View()
    transcript_view.add_item(discord.ui.Button(label="Transcript", url=transcript_data['url'], style=discord.ButtonStyle.url))

    if panel.transcript_channel:
        log_channel = guild.get_channel(int(panel.transcript_channel))
        if log_channel:
            file = await asyncio.to_thread(create_transcript_file, transcript_data['text'], str(ticket.id))
            await log_channel.send(file=file, embed=transcript_data['embed'], view=transcript_view)

    if panel.transcript_dm:
        try:
            file = await asyncio.to_thread(create_transcript_file, transcript_data['text'], str(ticket.id))
            await creator.send(file=file, embed=transcript_data['embed'], view=transcript_view)
        except discord.HTTPException:
            pass

# ── UI ───────────────────────────────────────────────────────────────────

class CloseTicketModal(discord.ui.Modal):
    def __init__(self, ticket: Ticket, panel: TicketPanelConfig, controls: "TicketControls"):
        super().__init__(title="Close Ticket Reason")
        self.ticket = ticket
        self.panel = panel
        self.controls = controls
        self.add_item(discord.ui.InputText(label="Reason", style=discord.InputTextStyle.long))

    async def callback(self, interaction: discord.Interaction):
        is_thread = isinstance(interaction.channel, discord.Thread)
        move_to = await _move_to_category(interaction.channel, self.panel.category_closed, interaction.guild)

        close_em = discord.Embed(color=0x5865f2, description=f"{interaction.user.mention}, this ticket has been closed{move_to}")
        await interaction.response.send_message(embed=close_em, ephemeral=True)

        reason = self.children[0].value
        self.ticket.closed = _status_entry(interaction.client, int(interaction.user.id), reason=reason)
        self.ticket.status = "closed"
        await self.ticket.save()

        embed = discord.Embed(title="Close ticket with reason")
        embed.add_field(name="Reason", value=reason)
        await interaction.channel.send(embed=embed)

        _set_button_state(self.controls, close_ticket=True, reopen_ticket=False)
        await _refresh_ticket_message(interaction.channel, self.ticket, self.controls)

        if is_thread:
            await _set_ticket_channel_state(interaction.channel, archived=True, locked=True)

class DeleteTicketConfirm(discord.ui.View):
    def __init__(self, ticket: Ticket, panel: TicketPanelConfig):
        super().__init__(timeout=None)
        self.ticket = ticket
        self.panel = panel

    @discord.ui.button(emoji="🗑️", label="Confirm", style=discord.ButtonStyle.red, custom_id="confirm_delete")
    async def confirm_delete(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.defer(invisible=False, ephemeral=True)

        if not self.ticket.closed.get('status'):
            self.ticket.closed = _status_entry(interaction.client, int(interaction.user.id), reason="Ticket deleted")
        self.ticket.deleted = _status_entry(interaction.client, int(interaction.user.id))
        self.ticket.status = "deleted"
        await self.ticket.save()

        await interaction.channel.send(f"{interaction.user.mention} deleted the ticket.")

        await send_transcript(self.ticket, interaction.guild, self.panel, interaction.channel)
        await interaction.channel.delete()

class TicketControls(discord.ui.View):
    def __init__(self, client):
        super().__init__(timeout=None)
        self.client = client

    @discord.ui.button(emoji="🎟️", label="Claim", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        ticket, panel = await get_ticket_and_panel(interaction.guild, interaction.channel.id)
        if ticket is None or panel is None:
            return await interaction.response.send_message("> **Warning:** This ticket's panel could not be found.", ephemeral=True)

        if interaction.user.id == int(ticket.creator_id):
            return await interaction.response.send_message("> **Warning:** You cannot claim your own ticket.", ephemeral=True)

        if ticket.claimed['status'] == True:
            return await interaction.response.send_message(f"> **Warning:** This ticket is already claimed by <@{ticket.claimed['user']['id']}>.", ephemeral=True)

        move_to = await _move_to_category(interaction.channel, panel.category_claimed, interaction.guild)

        ticket.claimed = _status_entry(interaction.client, interaction.user.id)
        await ticket.save()

        embed = discord.Embed(color=0x5865f2, description=f"{interaction.user.mention}, you claimed the ticket{move_to}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await interaction.channel.send(f"{interaction.user.mention} claimed the ticket.")

        button.disabled = True
        button.label = "Claimed"
        await _refresh_ticket_message(interaction.channel, ticket, self)

    @discord.ui.button(emoji="🔒", label="Close", style=discord.ButtonStyle.gray, custom_id="close_ticket")
    async def close_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        ticket, panel = await get_ticket_and_panel(interaction.guild, interaction.channel.id)
        if ticket is None or panel is None:
            return await interaction.response.send_message("> **Warning:** This ticket's panel could not be found.", ephemeral=True)

        await interaction.response.send_modal(CloseTicketModal(ticket, panel, self))

    @discord.ui.button(emoji="🔓", label="Reopen", style=discord.ButtonStyle.green, custom_id="reopen_ticket", disabled=True)
    async def reopen_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        ticket, panel = await get_ticket_and_panel(interaction.guild, interaction.channel.id)
        if ticket is None or panel is None:
            return await interaction.response.send_message("> **Warning:** This ticket's panel could not be found.", ephemeral=True)

        if ticket.closed['status'] == False:
            return await interaction.response.send_message(embed=discord.Embed(description="This ticket is not closed yet.", color=0x5865f2), ephemeral=True)

        category = discord.utils.get(interaction.guild.categories, id=int(panel.category_open)) if panel.category_open else None
        move_to = '.'
        if await _set_ticket_channel_state(interaction.channel, category=category, archived=False, locked=False):
            move_to = f' and it has been moved to **{category.name}** category'

        ticket.closed["status"] = False
        ticket.closed["user"] = ""
        ticket.reopened = _status_entry(interaction.client, interaction.user.id)
        ticket.status = "open"
        await ticket.save()

        reopen_em = discord.Embed(color=0x5865f2, description=f"{interaction.user.mention}, you reopened this ticket{move_to}")
        await interaction.response.send_message(embed=reopen_em, ephemeral=True)

        embed = discord.Embed(title="Ticket reopened.")
        embed.add_field(name="Reopened by", value=f"<@{interaction.user.id}>")
        await interaction.channel.send(embed=embed)

        _set_button_state(self, close_ticket=False, reopen_ticket=True)
        await _refresh_ticket_message(interaction.channel, ticket, self)

    @discord.ui.button(emoji="🗑️", label="Delete", style=discord.ButtonStyle.red, custom_id="delete_ticket")
    async def delete_ticket(self, button: discord.ui.Button, interaction: discord.Interaction):
        ticket, panel = await get_ticket_and_panel(interaction.guild, interaction.channel.id)
        if ticket is None or panel is None:
            return await interaction.response.send_message("> **Warning:** This ticket's panel could not be found.", ephemeral=True)

        # Ticket creators can't unilaterally delete their own ticket while it's
        # still open (staff needs a chance to review it first).
        if not ticket.closed.get('status') and interaction.user.id == int(ticket.creator_id):
            return await interaction.response.send_message("> **Warning:** You cannot delete your own ticket. Please close it first.", ephemeral=True)

        delete_confirm_em = discord.Embed(
            color=0x5865f2,
            description=f"{interaction.user.mention}, are you sure you want to delete this ticket? The channel will be deleted and a transcript will be generated."
        )
        await interaction.response.send_message(embed=delete_confirm_em, view=DeleteTicketConfirm(ticket, panel), ephemeral=True)

class Ticketing(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False
        self.ticket_timeouts = {}  # {channel_id: expiry_time}
        self.auto_close_check.start()

    @tasks.loop(minutes=30)
    async def auto_close_check(self):
        """Auto-close tickets after 24 hours of inactivity."""
        now = datetime.now()
        for channel_id, expiry in list(self.ticket_timeouts.items()):
            if now <= expiry:
                continue

            channel = self.client.get_channel(channel_id)
            if not channel:
                continue

            ticket = await get_channel_ticket(channel.guild, channel.id)
            if not ticket or ticket.status != "open":
                self.ticket_timeouts.pop(channel_id, None)
                continue

            ticket.closed = _status_entry(self.client, 0, reason="Auto-closed due to 24 hours of inactivity")
            ticket.status = "closed"
            await ticket.save()

            try:
                await channel.send("🔒 This ticket has been auto-closed due to 24 hours of inactivity.")
                view = TicketControls(self.client)
                _set_button_state(view, close_ticket=True, reopen_ticket=False)
                await _refresh_ticket_message(channel, ticket, view)
                await _set_ticket_channel_state(channel, archived=True, locked=True)
            except discord.HTTPException:
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
        if interaction.data.get("custom_id") != "create_ticket":
            return

        ticketing_data = await get_ticketing(interaction.guild)

        # Master toggle for the whole Ticketing plugin - a panel message
        # stays live on Discord even while disabled, so this has to be
        # checked here, not just enforced on the dashboard's write routes.
        if not ticketing_data.status:
            return await interaction.response.send_message(
                "❌ The ticketing service has been disabled. Please contact your server owner.",
                ephemeral=True
            )

        panels = ticketing_data.panels
        tickets = await get_guild_tickets(interaction.guild)

        panel = next((p for p in panels if p.channel_id == str(interaction.channel.id)), None)
        if panel is None:
            return

        threading_mode = bool(panel.threading_mode)

        # Enforce "max open tickets per user" for this panel. An explicit 0
        # means unlimited; an unset value keeps the legacy default of 1.
        # An open ticket is one that isn't closed and isn't deleted.
        max_open = panel.max_open_tickets if panel.max_open_tickets is not None else 1
        user_open = [
            t for t in tickets
            if t.creator_id == str(interaction.user.id)
            and t.panel_id == str(panel.id)
            and not t.closed.get('status')
            and not t.deleted.get('status')
        ]
        if max_open > 0 and len(user_open) >= max_open:
            noun = "an open ticket" if max_open == 1 else f"**{len(user_open)}** open tickets (limit is **{max_open}**)"
            return await interaction.response.send_message(
                f"> **Warning:** You already have {noun} on this panel.", ephemeral=True
            )

        ticket_number = len(tickets) + 1
        ticket_name = f"{ticket_number}-{interaction.user.name}".lower()
        manager_roles = [
            r for r in (interaction.guild.get_role(int(rs)) for rs in panel.manager_roles)
            if r is not None
        ]

        if threading_mode:
            channel, location_note = await self._create_thread_ticket(interaction, panel, ticket_name, manager_roles)
        else:
            channel, location_note = await self._create_channel_ticket(interaction, panel, ticket_name, manager_roles)

        self.ticket_timeouts[channel.id] = datetime.now() + timedelta(seconds=AUTO_CLOSE_TIMEOUT)

        create_em = discord.Embed(
            color=0x5865f2,
            title="Ticket created",
            description=f"{interaction.user.mention}, your ticket has been created{location_note}"
        )
        create_em.add_field(name=f"Ticket #{ticket_number}", value=f"{channel.mention}", inline=False)
        await interaction.response.send_message(embed=create_em, ephemeral=True)

        # Insert the Ticket doc BEFORE sending the intro message below - the
        # on_message transcript listener looks the ticket up by channel, and
        # if that gateway event is processed before this insert lands, the
        # lookup finds nothing and silently drops the bot's own intro
        # message from the transcript. message_id is filled in once we have
        # it, right after the send.
        ticket = Ticket(
            id=v.uuid(12, strCase="upper/lower/nums"),
            guild_id=str(interaction.guild.id),
            channel_id=str(channel.id),
            message_id="",
            creator_id=str(interaction.user.id),
            creator={
                "name": interaction.user.name,
                "avatar": interaction.user.display_avatar.url,
            },
            panel_id=str(panel.id),
            claimed={"status": False, "user": "", "updated_at": ""},
            closed={"status": False, "reason": "", "user": "", "updated_at": ""},
            reopened={"status": False, "user": "", "updated_at": ""},
            deleted={"status": False, "user": "", "updated_at": ""},
        )
        await ticket.insert()

        embed = panel.intro_message.embed.to_embed()
        # Ping the creator (and, in a thread, the manager roles so they get pulled in).
        content = interaction.user.mention
        if threading_mode and manager_roles:
            content += " " + " ".join(r.mention for r in manager_roles)
        msg: discord.Message = await channel.send(content=content, embed=embed, view=TicketControls(self.client))
        # No point pinning in a thread - the intro is already the first
        # message, and pinning just adds a "Message pinned" system notice.
        if panel.pin_intro and not threading_mode:
            await msg.pin()

        ticket.message_id = str(msg.id)
        await ticket.save()

    async def _create_thread_ticket(self, interaction: discord.Interaction, panel: TicketPanelConfig, ticket_name: str, manager_roles: list[discord.Role]):
        # Private threads are available to every guild and, unlike public
        # threads, don't post a "started a thread" notice in the parent
        # channel. Fall back to a public thread only if creation fails.
        try:
            channel = await interaction.channel.create_thread(
                name=ticket_name,
                type=discord.ChannelType.private_thread,
                invitable=False,
            )
        except discord.HTTPException:
            channel = await interaction.channel.create_thread(
                name=ticket_name,
                type=discord.ChannelType.public_thread,
            )
        await channel.add_user(interaction.user)
        return channel, f' as a thread in {interaction.channel.mention}.'

    async def _create_channel_ticket(self, interaction: discord.Interaction, panel: TicketPanelConfig, ticket_name: str, manager_roles: list[discord.Role]):
        category = discord.utils.get(interaction.guild.categories, id=int(panel.category_open)) if panel.category_open else None
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
            **{
                role: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)
                for role in manager_roles
            }
        }
        channel = await interaction.guild.create_text_channel(
            ticket_name,
            category=category,
            overwrites=overwrites,
            topic=(
                f"- Type: {panel.panel_button.emoji} {panel.panel_button.label}"
                f"\n- Created by: {interaction.user.mention}"
            ),
        )
        location_note = (
            f' and it has been moved to **<#{panel.category_open}>** category'
            if panel.category_open else '.'
        )
        return channel, location_note

    # ── Ticketing Transcript Listeners ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # pins_add must stay allowed through here - the pins_add-specific
        # content below (the "X pinned a message" notice) is otherwise dead
        # code, since every such message would already have been filtered
        # out above.
        if message.type not in (discord.MessageType.default, discord.MessageType.pins_add):
            return
        if message.guild is None:
            return

        try:
            panels = (await get_ticketing(message.guild)).panels
            tickets = await get_guild_tickets(message.guild)

            if not tickets or not panels:
                return

            ticket = await get_channel_ticket(message.guild, message.channel.id)
            if not ticket:
                return

            if ticket.status == "open":
                self.ticket_timeouts[message.channel.id] = datetime.now() + timedelta(seconds=AUTO_CLOSE_TIMEOUT)

            msg_content = message.content

            if message.type == discord.MessageType.pins_add:
                msg_content = f"{message.author.nick} pinned a message to this channel. See all pinned messages."

            for user in message.mentions:
                msg_content = msg_content.replace(f"<@{user.id}>", f"@{user.name}")
            for role in message.role_mentions:
                msg_content = msg_content.replace(f"<@&{role.id}>", f"@{role.name}")

            try:
                await TicketMessage(
                    id=str(message.id),
                    ticket_id=str(ticket.id),
                    guild_id=str(message.guild.id),
                    channel_id=str(message.channel.id),
                    user={
                        "id": str(message.author.id),
                        "name": message.author.display_name,
                        "avatar": message.author.avatar.url if message.author.avatar else message.author.default_avatar.url,
                        "color": int(message.author.color),
                        "bot": message.author.bot
                    },
                    content=msg_content,
                    embeds=[embed.to_dict() for embed in message.embeds] if message.embeds else [],
                    attachments=[a.url for a in message.attachments] if message.attachments else [],
                    pin=message.type == discord.MessageType.pins_add,
                    created_at=message.created_at,
                ).insert()
            except DuplicateKeyError:
                pass

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
            tickets = await get_guild_tickets(message.guild)
            if not tickets:
                return

            ticket = await get_channel_ticket(message.guild, message.channel.id)
            if not ticket:
                return

            # Mark the message deleted rather than dropping it, so the
            # transcript keeps a full record instead of silently losing
            # history when a message is removed from the channel.
            entry = await TicketMessage.get(str(message.id))
            if entry and entry.ticket_id == str(ticket.id):
                entry.deleted = True
                entry.deleted_at = datetime.now(timezone.utc)
                await entry.save()
        except AttributeError:
            return

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.type != discord.MessageType.default:
            return
        if after.guild is None:
            return
        if before.content == after.content:
            # Discord also fires this for embed-only updates (e.g. link
            # unfurls), which aren't a real content edit.
            return

        try:
            panels = (await get_ticketing(after.guild)).panels
            tickets = await get_guild_tickets(after.guild)
            if not tickets or not panels:
                return

            ticket = await get_channel_ticket(after.guild, after.channel.id)
            if not ticket:
                return

            msg_content = after.content
            for user in after.mentions:
                msg_content = msg_content.replace(f"<@{user.id}>", f"@{user.name}")
            for role in after.role_mentions:
                msg_content = msg_content.replace(f"<@&{role.id}>", f"@{role.name}")

            entry = await TicketMessage.get(str(after.id))
            if entry and entry.ticket_id == str(ticket.id):
                entry.content = msg_content
                entry.embeds = [embed.to_dict() for embed in after.embeds] if after.embeds else []
                entry.edited = True
                entry.edited_at = datetime.now(timezone.utc)
                await entry.save()
        except AttributeError:
            return
        except discord.errors.NotFound:
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
