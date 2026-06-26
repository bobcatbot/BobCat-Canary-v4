import random
import string

import discord
from datetime import datetime
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from modules import bot as v
from ...db import get_dash_config, get_server_config, update_config
from ...utils import GuildModels, bearer_client, login_required, premium_module

forms_bp = Blueprint('forms', __name__)

# ── Public form submission pages ──────────────────────────────────────────────
@forms_bp.route("/form/<int:guild_id>/<form_id>", methods=['GET', 'POST'])
@login_required
def form(guild_id, form_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    forms_list = get_server_config(guild).get('forms')
    form_data = next((f for f in forms_list if f['id'] == form_id), None)

    if request.method == 'POST':
        data = request.get_json()
        form_idx = forms_list.index(form_data)

        form_data['responses'].append(data)
        update_config(guild, f'Bot.forms.{form_idx}.responses', form_data['responses'])

        channel = guild.get_channel(int(form_data['settings']['submission_channel']))

        async def send_submission():
            submitted_at = datetime.fromisoformat(data['submitted_at'])
            embed = discord.Embed(
                title=f"{form_data['name']} (#{len(form_data['responses'])})",
                color=0x5865F2,
                timestamp=submitted_at,
            )
            for index, question in enumerate(form_data['questions']):
                embed.add_field(name=question['title'], value=data['answers'][index], inline=False)
            embed.set_footer(text=f"User ID: {data['user']['id']}")
            msg = await channel.send(embed=embed)

            if form_data['settings']['options']['thread']:
                await msg.create_thread(name=f"{form_data['name']} ({form_data['id']})")

            reactions = form_data['settings']['options']['reactions']
            if reactions['status'] and reactions['emojis']:
                for emoji in reactions['emojis']:
                    await msg.add_reaction(emoji)

        v.client.loop.create_task(send_submission())
        return jsonify({'status': 200})

    return render_template("dashboard/plugins/forms/form.html", user=current_user, guild=guild, data=form_data)

@forms_bp.route("/form/<int:guild_id>/<form_id>/submissions", methods=['GET', 'DELETE'])
@login_required
def form_submissions(guild_id, form_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    user = guild.get_member(current_user.id)

    forms_list = get_server_config(guild).get('forms')
    form_data = next((f for f in forms_list if f['id'] == form_id), None)

    if request.method == 'DELETE':
        res = request.get_json()
        form_idx = forms_list.index(form_data)
        form_data['responses'] = [r for r in form_data['responses'] if r['id'] != res['id']]
        update_config(guild, f'Bot.forms.{form_idx}.responses', form_data['responses'])
        return jsonify({'status': 200})

    submission_viewers = form_data['settings'].get('submission_viewers', [])
    submission_managers = form_data['settings'].get('submission_managers', [])
    allowed_roles = set(submission_viewers) | set(submission_managers)
    user_role_ids = {str(role.id) for role in user.roles}

    if allowed_roles and not user_role_ids & allowed_roles:
        flash('You are not allowed to view the submissions', 'error')
        return redirect(url_for('web.index'))

    can_manage = any(str(role.id) in submission_managers for role in user.roles)
    return render_template("dashboard/plugins/forms/form_subs.html", user=current_user, guild=guild, form=form_data, can_manage=can_manage)


# ── Dashboard forms management ────────────────────────────────────────────────
@forms_bp.route("/dashboard/<int:guild_id>/forms")
@login_required
def forms(guild_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    
    data = get_server_config(guild).get('forms')
    plugin = get_dash_config(guild).get('forms')
    
    return render_template(
        "dashboard/plugins/forms/form_index.html", 
        user=current_user, 
        guild=guild, 
        data=data, 
        plugin=plugin
    )

@forms_bp.route("/dashboard/<int:guild_id>/forms/creation", methods=['GET', 'POST'])
@login_required
def forms_create(guild_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    if request.method == 'POST':
        data = request.get_json()

        data['id'] = v.uuid(12, strCase="upper/lower/nums")
        
        forms_list = get_server_config(guild).get('forms')
        
        for key, val in data.items():
            update_config(guild.id, f'Bot.forms.{len(forms_list)}.{key}', val)
        
        flash(f"Successfully created form {data['id']}", 'success')
        return jsonify({'status': 'success', 'message': f"Successfully created form {data['id']}"})

    return render_template(
        "dashboard/plugins/forms/form_create.html", 
        user=current_user, 
        guild=guild
    )

@forms_bp.route("/dashboard/<int:guild_id>/forms/<form_id>/edit", methods=['GET', 'POST', 'DELETE'])
@login_required
def forms_edit(guild_id, form_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    forms_list = get_server_config(guild).get('forms')
    form_data = next((f for f in forms_list if f['id'] == form_id), None)
    form_idx = forms_list.index(form_data)

    if request.method == 'POST':
        for key, val in request.get_json().items():
            update_config(guild.id, f'Bot.forms.{form_idx}.{key}', val)
        return jsonify({'status': 'success', 'message': 'Successfully updated form'})

    if request.method == 'DELETE':
        forms_list.pop(form_idx)
        update_config(guild.id, 'Bot.forms', forms_list)
        return jsonify({'status': 'success', 'message': 'Successfully deleted form'})

    return render_template(
        "dashboard/plugins/forms/form_edit.html",
        user=current_user, 
        guild=guild, 
        data=form_data, 
        emojis=GuildModels(guild).emojis
    )