import discord
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from modules import bot as v
from modules.models import Guild, Ticket
from ...db import get_guild
from ...utils import bearer_client, login_required, premium_module

ticketing_bp = Blueprint('ticketing', __name__)

# ── Public transcript pages ──────────────────────────────────────────────
@ticketing_bp.route("/t/<int:guild_id>/<ticket_id>")
@login_required
def ticketing_transcript(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return redirect(url_for('web.index'))

    # Use Bunnet to get the ticket
    ticket = Ticket.find_one(
        Ticket.guild_id == str(guild.id),
        Ticket.id == ticket_id
    ).run()

    if ticket is None:
        flash('Ticket not found', 'error')
        return redirect(url_for('web.index'))

    closed_by_user = None
    if ticket.closed and ticket.closed.get('user'):
        closed_by_user = v.client.get_user(int(ticket.closed['user']))

    return render_template(
        "dashboard/plugins/ticketing/ticketing_transcript.html",
        guild=guild,
        data=ticket,
        closed_by=closed_by_user,
    )

# ── Dashboard management ────────────────────────────────────────────────
@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing")
@login_required
def ticketing(guild_id):
    premium_module(guild_id, 'ticketing')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    # Get the guild document using Bunnet
    config = Guild.get(str(guild.id)).run().dashboard.ticketing
    
    return render_template(
        "dashboard/plugins/ticketing/ticketing_index.html",
        user=current_user,
        guild=guild,
        data=config
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/creation", methods=['GET', 'POST'])
@login_required
def ticketing_create(guild_id):
    premium_module(guild_id, 'ticketing')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        data['id'] = v.uuid(12, strCase="upper/lower/nums")

        async def run():
            # Get the guild document
            config = Guild.get(str(guild.id)).run()
            if config is None:
                return

            # Ensure ticketing exists
            if not hasattr(config.dashboard, 'ticketing'):
                config.dashboard.ticketing = {}
            
            panels = config.dashboard.ticketing.get('panels', [])

            # Create the Discord message
            embed = discord.Embed(
                title=data.get('panel_message', {}).get('embed', {}).get('title', 'Support Tickets'),
                description=data.get('panel_message', {}).get('embed', {}).get('description', 'Click below to create a ticket.'),
                color=int(data.get('panel_message', {}).get('embed', {}).get('color', '#5865f2').replace('#', ''), 16)
            )
            
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                emoji=data.get('panel_button', {}).get('emoji', '🎫'),
                label=data.get('panel_button', {}).get('label', 'Create Ticket'),
                style=getattr(discord.ButtonStyle, data.get('panel_button', {}).get('style', 'blurple')),
                custom_id='create_ticket'
            ))
            
            channel = guild.get_channel(int(data.get('channel_id')))
            if channel:
                msg = await channel.send(embed=embed, view=view)
                data['panel_message_id'] = str(msg.id)

            # Save to dashboard
            panels.append(data)
            config.dashboard.ticketing['panels'] = panels
            config.updated_at = discord.utils.utcnow()
            config.save()

        v.client.loop.create_task(run())
        flash(f"Successfully created ticket panel {data['id']}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully created ticket'})

    return render_template(
        "dashboard/plugins/ticketing/ticketing_create.html",
        user=current_user,
        guild=guild
    )

@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/edition", methods=['GET', 'POST'])
@login_required
def ticketing_edit(guild_id, ticket_id):
    premium_module(guild_id, 'ticketing')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    # Get the guild document
    config = Guild.get(str(guild.id)).run()
    if config is None:
        flash('Guild config not found', 'error')
        return redirect(url_for('ticketing.ticketing', guild_id=guild_id))

    panels = config.dashboard.ticketing.get('panels', [])
    tk_data = next((t for t in panels if t.get('id') == ticket_id), None)
    
    if tk_data is None:
        flash('Ticket panel not found', 'error')
        return redirect(url_for('ticketing.ticketing', guild_id=guild_id))

    ticket_idx = panels.index(tk_data)

    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        async def run():
            # Get fresh config
            config = Guild.get(str(guild.id)).run()
            if config is None:
                return

            panels = config.dashboard.ticketing.get('panels', [])
            
            # Update the panel message if it exists
            panel_msg_id = panels[ticket_idx].get('panel_message_id')
            channel_id = panels[ticket_idx].get('channel_id')
            
            if panel_msg_id and channel_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        msg = await channel.fetch_message(int(panel_msg_id))
                        
                        embed = discord.Embed(
                            title=data.get('panel_message', {}).get('embed', {}).get('title', tk_data.get('panel_message', {}).get('embed', {}).get('title', 'Support Tickets')),
                            description=data.get('panel_message', {}).get('embed', {}).get('description', tk_data.get('panel_message', {}).get('embed', {}).get('description', 'Click below to create a ticket.')),
                            color=int(data.get('panel_message', {}).get('embed', {}).get('color', '#5865f2').replace('#', ''), 16)
                        )
                        
                        view = discord.ui.View()
                        view.add_item(discord.ui.Button(
                            emoji=data.get('panel_button', {}).get('emoji', tk_data.get('panel_button', {}).get('emoji', '🎫')),
                            label=data.get('panel_button', {}).get('label', tk_data.get('panel_button', {}).get('label', 'Create Ticket')),
                            style=getattr(discord.ButtonStyle, data.get('panel_button', {}).get('style', tk_data.get('panel_button', {}).get('style', 'blurple'))),
                            custom_id='create_ticket'
                        ))
                        
                        await msg.edit(embed=embed, view=view)
                    except discord.NotFound:
                        pass  # Message was deleted, just update config

            # Update the config
            for key, value in data.items():
                panels[ticket_idx][key] = value

            config.dashboard.ticketing['panels'] = panels
            config.updated_at = discord.utils.utcnow()
            config.save()

        v.client.loop.create_task(run())
        flash(f"Successfully updated ticket panel {ticket_id}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully updated ticket'})

    return render_template(
        "dashboard/plugins/ticketing/ticketing_edit.html",
        user=current_user,
        guild=guild,
        data=tk_data
    )

@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/delete", methods=['DELETE'])
def ticketing_delete(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    panels = config.dashboard.ticketing.get('panels', [])
    data = next((t for t in panels if t.get('id') == ticket_id), None)
    
    if data is None:
        return jsonify({'status': 'error', 'message': 'Ticket panel not found'}), 404

    async def run():
        # Get fresh config
        config = Guild.get(str(guild.id)).run()
        if config is None:
            return

        panels = config.dashboard.ticketing.get('panels', [])
        data = next((t for t in panels if t.get('id') == ticket_id), None)
        
        if data is None:
            return

        # Delete the Discord message
        panel_msg_id = data.get('panel_message_id')
        channel_id = data.get('channel_id')
        
        if panel_msg_id and channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                try:
                    msg = await channel.fetch_message(int(panel_msg_id))
                    await msg.delete()
                except discord.NotFound:
                    pass

        # Remove from config
        ticket_idx = panels.index(data)
        panels.pop(ticket_idx)
        config.dashboard.ticketing['panels'] = panels
        config.updated_at = discord.utils.utcnow()
        config.save()

    v.client.loop.create_task(run())
    flash(f"Successfully deleted ticket panel {ticket_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted ticket panel'})