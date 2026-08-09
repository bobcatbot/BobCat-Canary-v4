import discord
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from modules import bot as v
from modules.models import Guild, Form, FormResponse
from ...utils import bearer_client, login_required, premium_module

forms_bp = Blueprint('forms', __name__)

# ── Public form submission pages ──────────────────────────────────────────────
@forms_bp.route("/form/<int:guild_id>/<form_id>", methods=['GET', 'POST'])
@login_required
def form(guild_id, form_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        flash('Guild not found', 'error')
        return redirect(url_for('web.index'))

    # Get the form using Bunnet
    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        flash('Form not found', 'error')
        return redirect(url_for('web.index'))

    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Create a form response
        response = FormResponse(
            guild_id=str(guild.id),
            form_id=form_id,
            user_id=str(current_user.id),
            answers=data.get('answers', [])
        )
        response.insert()

        # Send to channel if configured
        channel_id = form_data.settings.get('submission_channel')
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                async def send_submission():
                    embed = discord.Embed(
                        title=f"{form_data.name} (#{response.id})",
                        color=0x5865F2,
                        timestamp=response.submitted_at,
                    )
                    for idx, question in enumerate(form_data.questions):
                        answer = response.answers[idx] if idx < len(response.answers) else 'N/A'
                        embed.add_field(
                            name=question.get('label', f'Question {idx+1}'),
                            value=answer,
                            inline=False
                        )
                    embed.set_footer(text=f"User ID: {current_user.id}")
                    await channel.send(embed=embed)

                v.client.loop.create_task(send_submission())

        return jsonify({'status': 200})

    return render_template(
        "dashboard/plugins/forms/form.html",
        user=current_user,
        guild=guild,
        data=form_data
    )


@forms_bp.route("/dashboard/<int:guild_id>/forms")
@login_required
def forms(guild_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    # Get guild document for plugin status
    config = Guild.get(str(guild.id)).run()
    
    # Get all forms for this guild using Bunnet
    forms_list = Form.find(Form.guild_id == str(guild.id)).run()
    plugin_status = config.dashboard.forms.get('status', False)

    return render_template(
        "dashboard/plugins/forms/form_index.html",
        user=current_user,
        guild=guild,
        data=forms_list,
        plugin=plugin_status
    )


@forms_bp.route("/dashboard/<int:guild_id>/forms/creation", methods=['GET', 'POST'])
@login_required
def forms_create(guild_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Create form using Bunnet
        form = Form(
            guild_id=str(guild.id),
            name=data.get('name', 'Untitled Form'),
            description=data.get('description', ''),
            questions=data.get('questions', []),
            settings=data.get('settings', {}),
            status=True
        )
        form.insert()

        flash(f"Successfully created form {form.id}", 'success')
        return jsonify({'status': 'success', 'message': f"Successfully created form {form.id}"})

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
    if guild is None:
        return render_template("error/404.html"), 404

    # Get the form using Bunnet
    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        flash('Form not found', 'error')
        return redirect(url_for('forms.forms', guild_id=guild_id))

    if request.method == 'POST':
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        for key, value in data.items():
            setattr(form_data, key, value)
        form_data.save()
        return jsonify({'status': 'success', 'message': 'Successfully updated form'})

    if request.method == 'DELETE':
        form_data.delete()
        return jsonify({'status': 'success', 'message': 'Successfully deleted form'})

    return render_template(
        "dashboard/plugins/forms/form_edit.html",
        user=current_user,
        guild=guild,
        data=form_data
    )