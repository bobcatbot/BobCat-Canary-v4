import logging
import discord
from bson import ObjectId
from bson.errors import InvalidId
from quart import Blueprint, render_template, redirect, url_for, flash, jsonify, request

from modules import bot as v
from modules.models import Guild, Ticket, TicketPanelConfig
from ...utils import bearer_client, login_required, plugin_guard, is_premium, plugin_item_cap, unflatten_keys, deep_merge
from ...plugins import PLUGIN_LIST

ticketing_bp = Blueprint('ticketing', __name__)
logger = logging.getLogger(__name__)

def _panel_message_embed(panel: TicketPanelConfig) -> discord.Embed:
    """Build the live Discord embed for a panel's publish message.

    An unset title/description/color falls back to a display-only default
    here - the panel's own saved config stays blank so the dashboard editor
    still shows an empty field rather than the placeholder text.
    """
    return panel.panel_message.embed.to_embed()

def _panel_button_view(panel: TicketPanelConfig) -> discord.ui.View:
    btn = panel.panel_button
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        emoji=btn.emoji or None,
        label=btn.label or 'Open Ticket',
        style=getattr(discord.ButtonStyle, btn.style or 'blurple', discord.ButtonStyle.blurple),
        custom_id='create_ticket'
    ))
    return view

# ── Public transcript pages ──────────────────────────────────────────────
@ticketing_bp.route("/t/<int:guild_id>/<ticket_id>")
@login_required
async def ticketing_transcript(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return redirect(url_for('web.index'))

    # Use Beanie to get the ticket
    ticket = await Ticket.find_one(
        Ticket.guild_id == str(guild.id),
        Ticket.id == ticket_id
    )
    if ticket is None:
        # Older ticket docs were stored with a BSON ObjectId `_id`; the
        # string-typed query above can't match those, so fall back to a
        # raw ObjectId lookup.
        try:
            oid = ObjectId(ticket_id)
        except InvalidId:
            oid = None
        if oid is not None:
            ticket = await Ticket.find_one(
                Ticket.guild_id == str(guild.id),
                {"_id": oid}
            )

    if ticket is None:
        await flash('Ticket not found', 'error')
        return redirect(url_for('web.index'))

    closed_by_user = None
    if ticket.closed and ticket.closed.get('user'):
        closed_by_user = v.client.get_user(int(ticket.closed['user']))

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_transcript.html",
        guild=guild,
        data=ticket,
        closed_by=closed_by_user,
    )


# ── Dashboard management ────────────────────────────────────────────────
@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing")
@plugin_guard('ticketing')
async def ticketing(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.ticketing

    guild_premium = await is_premium(guild)

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_index.html",
        user=current_user,
        guild=guild,
        data=config,
        is_premium=guild_premium,
        item_cap=plugin_item_cap('ticketing', guild_premium),
        item_cap_premium=PLUGIN_LIST.get('ticketing', {}).get('max_premium', 15),
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/creation", methods=['GET', 'POST'])
@plugin_guard('ticketing')
async def ticketing_create(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == "POST":
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # The form posts dotted paths (panel_button.emoji, intro_message.embed.title);
        # the model and edit template expect the nested shape.
        data = unflatten_keys(data)

        # Validate required fields
        if not data.get('channel_id'):
            return jsonify({'status': 'error', 'message': 'Channel ID is required'}), 400

        channel = guild.get_channel(int(data['channel_id']))
        if channel is None:
            return jsonify({'status': 'error', 'message': 'Selected channel was not found.'}), 400

        # Enforce the free / premium panel cap
        existing = (await Guild.get(str(guild.id))).dashboard.ticketing.panels
        guild_premium = await is_premium(guild)
        cap = plugin_item_cap('ticketing', guild_premium)
        if len(existing) >= cap:
            msg = f"You've reached your limit of {cap} ticket panels."
            if not guild_premium:
                msg += f" Upgrade to premium for up to {PLUGIN_LIST.get('ticketing', {}).get('max_premium', 15)}."
            return jsonify({'status': 'error', 'message': msg, 'code': 'item_cap'}), 409

        data['id'] = v.uuid(12, strCase="upper/lower/nums")
        # Validate through the model (not a raw dict) so the embed color
        # validator and every field default actually run.
        panel = TicketPanelConfig(**data)

        embed = _panel_message_embed(panel)
        view = _panel_button_view(panel)

        try:
            msg = await channel.send(embed=embed, view=view)
        except discord.HTTPException as e:
            logger.error("Failed to send ticket panel message for guild %s: %s", guild_id, e)
            return jsonify({'status': 'error', 'message': f'Failed to post the panel message: {e}'}), 502
        panel.panel_message_id = str(msg.id)

        config = await Guild.get(str(guild.id))
        if config is None:
            return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

        panels = config.dashboard.ticketing.panels
        panels.append(panel)
        config.dashboard.ticketing.panels = panels
        config.updated_at = discord.utils.utcnow()
        await config.save()

        await flash(f"Successfully created ticket panel {panel.id}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully created ticket'})

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_form.html",
        user=current_user,
        guild=guild,
        data=TicketPanelConfig(),
        is_edit=False,
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/edition", methods=['GET', 'POST'])
@plugin_guard('ticketing')
async def ticketing_edit(guild_id, ticket_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document
    config = await Guild.get(str(guild.id))
    if config is None:
        await flash('Guild config not found', 'error')
        return redirect(url_for('ticketing.ticketing', guild_id=guild_id))

    panels = config.dashboard.ticketing.panels
    tk_data = next((t for t in panels if t.id == ticket_id), None)
    
    if tk_data is None:
        await flash('Ticket panel not found', 'error')
        return redirect(url_for('ticketing.ticketing', guild_id=guild_id))

    ticket_idx = panels.index(tk_data)

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Expand dotted paths (intro_message.embed.title) to the nested shape.
        data = unflatten_keys(data)

        # Re-fetch to apply the edit against the latest saved state.
        config = await Guild.get(str(guild.id))
        if config is None:
            return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

        panels = config.dashboard.ticketing.panels
        # Merge the update in first so a partial edit (e.g. just the intro
        # embed title) doesn't clobber sibling keys. deep_merge recurses into
        # the panel's own DictModel sub-fields and setattr's each leaf, so
        # the embed color validator still runs on assignment.
        panel = deep_merge(panels[ticket_idx], data)

        panel_msg_id = panel.panel_message_id
        channel_id = panel.channel_id

        if panel_msg_id and channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel is None:
                return jsonify({'status': 'error', 'message': 'Panel channel was not found.'}), 400

            embed = _panel_message_embed(panel)
            view = _panel_button_view(panel)

            try:
                msg = await channel.fetch_message(int(panel_msg_id))
                await msg.edit(embed=embed, view=view)
            except discord.NotFound:
                return jsonify({'status': 'error', 'message': 'Panel message was not found; it may have been deleted on Discord.'}), 404
            except discord.HTTPException as e:
                logger.error("Failed to update ticket panel message for guild %s: %s", guild_id, e)
                return jsonify({'status': 'error', 'message': f'Failed to update the panel message: {e}'}), 502

        config.dashboard.ticketing.panels = panels
        config.updated_at = discord.utils.utcnow()
        await config.save()

        await flash(f"Successfully updated ticket panel {ticket_id}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully updated ticket'})

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_form.html",
        user=current_user,
        guild=guild,
        data=tk_data,
        is_edit=True,
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/delete", methods=['DELETE'])
@plugin_guard('ticketing')
async def ticketing_delete(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    panels = config.dashboard.ticketing.panels
    data = next((t for t in panels if t.id == ticket_id), None)
    if data is None:
        return jsonify({'status': 'error', 'message': 'Ticket panel not found'}), 404

    panel_msg_id = data.panel_message_id
    channel_id = data.channel_id

    if panel_msg_id and channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel:
            try:
                msg = await channel.fetch_message(int(panel_msg_id))
                await msg.delete()
            except discord.NotFound:
                pass  # Message already gone on Discord's side; still remove the panel below.
            except discord.HTTPException as e:
                logger.error("Failed to delete ticket panel message for guild %s: %s", guild_id, e)
                return jsonify({'status': 'error', 'message': f'Failed to delete the panel message: {e}'}), 502

    panels.pop(panels.index(data))
    config.dashboard.ticketing.panels = panels
    config.updated_at = discord.utils.utcnow()
    await config.save()

    await flash(f"Successfully deleted ticket panel {ticket_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted ticket panel'})
