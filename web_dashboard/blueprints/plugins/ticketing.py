import discord
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request

from modules import bot as v
from ...db import get_server_config, get_dash_config, update_config
from ...utils import bearer_client, login_required, premium_module

ticketing_bp = Blueprint('ticketing', __name__)

# ── Public transcript pages ──────────────────────────────────────────────
@ticketing_bp.route("/t/<int:guild_id>/<ticket_id>")
@login_required
def ticketing_transcript(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    
    tickets = get_server_config(guild_id)['tickets']
    ticket = next((t for t in tickets if t['id'] == ticket_id), None)

    if ticket is None:
        return redirect(url_for('web.index'))
    
    closed_by_user = None
    if ticket['closed']['user']:
        closed_by_user = v.client.get_user(int(ticket['closed']['user']))

    return render_template(
        "dashboard/plugins/ticketing/ticketing_transcript.html",
        guild=guild,
        data=ticket,
        ticket_idx=tickets.index(ticket),
        closed_by=closed_by_user,
    )

# ── Dashboard management ────────────────────────────────────────────────
@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing")
@login_required
def ticketing(guild_id):
    premium_module(guild_id, 'ticketing')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    data = get_dash_config(guild.id).get('ticketing')
    
    return render_template(
        "dashboard/plugins/ticketing/ticketing_index.html",
        user=current_user, 
        guild=guild, 
        data=data
    )

@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/creation", methods=['GET', 'POST'])
@login_required
def ticketing_create(guild_id):
    premium_module(guild_id, 'ticketing')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    if request.method == "POST":
        data = request.get_json()
        data['id'] = v.uuid(12, strCase="upper/lower/nums")

        async def run():
            panels = get_dash_config(guild.id).get('ticketing')['panels']
            for key, val in data.items():
                update_config(guild.id, f'Dash.ticketing.panels.{len(panels)}.{key}', val)

            embed = discord.Embed(
                title=data['panel_message.embed.title'],
                description=data['panel_message.embed.description'],
                color=data['panel_message.embed.color']
            )
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                emoji=data['panel_button.emoji'],
                label=data['panel_button.label'],
                style=getattr(discord.ButtonStyle, data['panel_button.style']),
                custom_id='create_ticket'
            ))
            channel = guild.get_channel(int(data['channel_id']))
            msg = await channel.send(embed=embed, view=view)
            update_config(guild.id, f'Dash.ticketing.panels.{len(panels)}.panel_message_id', str(msg.id))

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

    panels = get_dash_config(guild.id).get('ticketing')['panels']
    tk_data = next((t for t in panels if t['id'] == ticket_id), None)
    ticket_idx = panels.index(tk_data)

    if request.method == 'POST':
        data = request.get_json()

        async def run():
            panel_msg = guild.get_channel(int(tk_data['channel_id'])).get_partial_message(
                int(tk_data['panel_message_id'])
            )
            embed = discord.Embed(
                title=data.get('panel_message.embed.title', tk_data['panel_message']['embed']['title']),
                description=data.get('panel_message.embed.description', tk_data['panel_message']['embed']['description']),
                color=data.get('panel_message.embed.color', tk_data['panel_message']['embed']['color'])
            )
            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                emoji=data.get('panel_button.emoji', tk_data['panel_button']['emoji']),
                label=data.get('panel_button.label', tk_data['panel_button']['label']),
                style=getattr(discord.ButtonStyle, data.get('panel_button.style', tk_data['panel_button']['style'])),
                custom_id='create_ticket'
            ))
            await panel_msg.edit(embed=embed, view=view)
            for key, val in data.items():
                update_config(guild.id, f'Dash.ticketing.panels.{ticket_idx}.{key}', val)

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
    panels = get_dash_config(guild.id).get('ticketing')['panels']
    data = next((t for t in panels if t['id'] == ticket_id), None)

    async def run():
        msg = guild.get_channel(int(data['channel_id'])).get_partial_message(int(data['panel_message_id']))
        await msg.delete()
        panels.pop(panels.index(data))
        update_config(guild.id, 'Dash.ticketing.panels', panels)

    v.client.loop.create_task(run())
    flash(f"Successfully deleted ticket panel {ticket_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted ticket panel'})