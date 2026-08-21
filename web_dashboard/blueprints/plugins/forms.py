import discord
import asyncio
import logging
from bson import ObjectId
from quart import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from modules import bot as v
from modules.models import Guild, Form, FormResponse
from ...utils import bearer_client, login_required, premium_module

forms_bp = Blueprint('forms', __name__)
logger = logging.getLogger(__name__)


# ── Public form submission pages ──────────────────────────────────────────────
@forms_bp.route("/form/<int:guild_id>/<form_id>", methods=['GET', 'POST'])
@login_required
async def form(guild_id, form_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        await flash('Guild not found', 'error')
        return redirect(url_for('web.index'))

    # Get the form using Bunnet
    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        await flash('Form not found', 'error')
        return redirect(url_for('web.index'))

    if request.method == 'POST':
        data = await request.get_json()
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
        logger.info(f"Form response submitted for form {form_id} by user {current_user.id}")

        # Send to channel if configured
        channel_id = form_data.settings.get('submission_channel')
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                async def send_submission():
                    try:
                        # Build mentions string
                        mentions = []
                        mention_roles = form_data.settings.get('options', {}).get('mentions', [])
                        if mention_roles:
                            for role_id in mention_roles:
                                role = guild.get_role(int(role_id))
                                if role:
                                    mentions.append(role.mention)
                        
                        mention_text = ' '.join(mentions) if mentions else ''

                        embed = discord.Embed(
                            title=f"{form_data.name} (#{response.id})",
                            color=0x5865F2,
                            timestamp=response.submitted_at,
                        )
                        
                        # Use question title as field name, not label
                        for idx, question in enumerate(form_data.questions):
                            answer = response.answers[idx] if idx < len(response.answers) else 'N/A'
                            embed.add_field(
                                name=question.get('title', f'Question {idx+1}'),
                                value=answer if answer else 'No response',
                                inline=False
                            )
                        
                        embed.set_footer(text=f"User ID: {current_user.id}")
                        
                        # Send the message
                        msg = await channel.send(content=mention_text if mention_text else None, embed=embed)
                        logger.info(f"Form submission sent to channel {channel_id} for form {form_id}")

                        # Add reactions
                        reactions_config = form_data.settings.get('options', {}).get('reactions', {})
                        if reactions_config.get('status', False):
                            for reaction in reactions_config.get('emojis', []):
                                try:
                                    await msg.add_reaction(reaction)
                                except Exception as e:
                                    logger.error(f"Failed to add reaction {reaction}: {e}")
                            logger.info(f"Added reactions to form submission message for form {form_id}")

                        # Start a thread
                        if form_data.settings.get('options', {}).get('thread', False):
                            try:
                                await msg.create_thread(name=f"Form response #{response.id}")
                                logger.info(f"Created thread for form submission message for form {form_id}")
                            except Exception as e:
                                logger.error(f"Failed to create thread: {e}")
                    
                    except discord.Forbidden:
                        logger.error(f"No permissions to send message in channel {channel_id}")
                    except Exception as e:
                        logger.error(f"Error sending form submission: {e}")

                # Fire and forget using asyncio.create_task
                asyncio.run_coroutine_threadsafe(send_submission(), v.client.loop)

        return jsonify({'status': 'success', 'message': 'Form submitted successfully'})

    return await render_template(
        "dashboard/plugins/forms/form.html",
        user=current_user,
        guild=guild,
        data=form_data
    )


# ── Form submission detail page ───────────────────────────────────────────────
@forms_bp.route("/form/<int:guild_id>/<form_id>/submissions", methods=['GET'])
@login_required
async def form_submissions(guild_id, form_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        await flash('Guild not found', 'error')
        return redirect(url_for('web.index'))

    # Get the form
    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        await flash('Form not found', 'error')
        return redirect(url_for('web.index'))

    # Check if user has permission to view submissions
    # Check if user is guild owner, admin, or has manage_guild permission
    member = guild.get_member(current_user.id)
    is_admin = (
        guild.owner_id == current_user.id or
        member.guild_permissions.administrator or
        member.guild_permissions.manage_guild
    )
    
    # Check if user has manager role
    is_manager = False
    manager_roles = form_data.settings.get('submission_managers', [])
    if manager_roles and member:
        for role_id in manager_roles:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                is_manager = True
                break
    
    # Check if user has viewer role
    is_viewer = False
    viewer_roles = form_data.settings.get('submission_viewers', [])
    if viewer_roles and member:
        for role_id in viewer_roles:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                is_viewer = True
                break
    
    can_view = is_admin or is_manager or is_viewer
    
    if not can_view:
        await flash('You do not have permission to view submissions', 'error')
        return redirect(url_for('web.index'))

    # Get all submissions for this form
    submissions = FormResponse.find(
        FormResponse.guild_id == str(guild.id),
        FormResponse.form_id == form_id
    ).sort(
        [(FormResponse.submitted_at, -1)]  # Newest first
    ).run()

    logger.info(f"Loaded {len(submissions)} submissions for form {form_id} in guild {guild_id}")

    return await render_template(
        "dashboard/plugins/forms/form_subs.html",
        user=current_user,
        guild=guild,
        form=form_data,
        submissions=submissions,
        can_manage=is_admin or is_manager
    )

@forms_bp.route("/form/<int:guild_id>/<form_id>/submissions/<submission_id>", methods=['GET'])
@login_required
async def form_submission_detail(guild_id, form_id, submission_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        return jsonify({'status': 'error', 'message': 'Form not found'}), 404

    # Check permissions
    member = guild.get_member(current_user.id)
    is_admin = (
        guild.owner_id == current_user.id or
        member.guild_permissions.administrator or
        member.guild_permissions.manage_guild
    )
    
    is_manager = False
    manager_roles = form_data.settings.get('submission_managers', [])
    if manager_roles and member:
        for role_id in manager_roles:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                is_manager = True
                break
    
    if not (is_admin or is_manager):
        return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

    # Get the submission - query using both formats
    submission = None
    
    # Try as ObjectId first
    try:
        obj_id = ObjectId(submission_id)
        submission = FormResponse.find_one(
            FormResponse.guild_id == str(guild.id),
            FormResponse.form_id == form_id,
            FormResponse.id == obj_id
        ).run()
    except:
        pass
    
    # If not found, try as string
    if submission is None:
        submission = FormResponse.find_one(
            FormResponse.guild_id == str(guild.id),
            FormResponse.form_id == form_id,
            FormResponse.id == submission_id
        ).run()
    
    if submission is None:
        return jsonify({'status': 'error', 'message': 'Submission not found'}), 404

    # Format answers with questions
    formatted_answers = []
    for idx, question in enumerate(form_data.questions):
        answer = submission.answers[idx] if idx < len(submission.answers) else 'No response'
        formatted_answers.append({
            'question': question.get('title', f'Question {idx+1}'),
            'answer': answer if answer else 'No response'
        })

    return jsonify({
        'status': 'success',
        'data': {
            'id': str(submission.id),
            'user_id': submission.user_id,
            'submitted_at': submission.submitted_at.isoformat(),
            'answers': formatted_answers
        }
    })

@forms_bp.route("/form/<int:guild_id>/<form_id>/submissions/<submission_id>", methods=['DELETE'])
@login_required
async def form_submission_delete(guild_id, form_id, submission_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    # Get the form
    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        return jsonify({'status': 'error', 'message': 'Form not found'}), 404

    # Check permissions
    member = guild.get_member(current_user.id)
    is_admin = (
        guild.owner_id == current_user.id or
        member.guild_permissions.administrator or
        member.guild_permissions.manage_guild
    )
    
    is_manager = False
    manager_roles = form_data.settings.get('submission_managers', [])
    if manager_roles and member:
        for role_id in manager_roles:
            role = guild.get_role(int(role_id))
            if role and role in member.roles:
                is_manager = True
                break
    
    if not (is_admin or is_manager):
        return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

    # Get the submission
    from bson import ObjectId
    submission = None
    
    # Try as ObjectId first
    try:
        obj_id = ObjectId(submission_id)
        submission = FormResponse.find_one(
            FormResponse.guild_id == str(guild.id),
            FormResponse.form_id == form_id,
            FormResponse._id == obj_id  # Use _id directly
        ).run()
    except:
        pass
    
    # If not found, try as string
    if submission is None:
        submission = FormResponse.find_one(
            FormResponse.guild_id == str(guild.id),
            FormResponse.form_id == form_id,
            FormResponse._id == submission_id  # Use _id directly
        ).run()
    
    if submission is None:
        return jsonify({'status': 'error', 'message': 'Submission not found'}), 404

    submission.delete()
    logger.info(f"Deleted submission {submission_id} for form {form_id} by user {current_user.id}")

    return jsonify({'status': 'success', 'message': 'Submission deleted successfully'})


# ── Dashboard pages ──────────────────────────────────────────────
@forms_bp.route("/dashboard/<int:guild_id>/forms")
@login_required
async def forms(guild_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get guild document for plugin status
    config = Guild.get(str(guild.id)).run()
    
    # Get all forms for this guild using Bunnet
    forms_list = Form.find(Form.guild_id == str(guild.id)).run()

    logger.info(f"Loaded {len(forms_list)} forms for guild {guild_id}")
    
    return await render_template(
        "dashboard/plugins/forms/form_index.html",
        user=current_user,
        guild=guild,
        data=forms_list,
    )

@forms_bp.route("/dashboard/<int:guild_id>/forms/creation", methods=['GET', 'POST'])
@login_required
async def forms_create(guild_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Validate required fields
        if not data.get('name'):
            return jsonify({'status': 'error', 'message': 'Form name is required'}), 400

        # Create form using Bunnet
        form = Form(
            id=v.uuid(length=12, strCase='upper/lower/nums'),
            guild_id=str(guild.id),
            name=data.get('name', 'Untitled Form'),
            description=data.get('description', ''),
            questions=data.get('questions', []),
            settings=data.get('settings', {}),
            status=True
        )
        form.insert()
        logger.info(f"Created form {form.id} for guild {guild_id}")

        await flash(f"Successfully created form {form.id}", 'success')
        return jsonify({'status': 'success', 'message': f"Successfully created form {form.id}"})

    return await render_template(
        "dashboard/plugins/forms/form_create.html",
        user=current_user,
        guild=guild
    )

@forms_bp.route("/dashboard/<int:guild_id>/forms/<form_id>/edit", methods=['GET', 'POST', 'DELETE'])
@login_required
async def forms_edit(guild_id, form_id):
    premium_module(guild_id, 'forms')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the form using Bunnet
    form_data = Form.find_one(
        Form.guild_id == str(guild.id),
        Form.id == form_id
    ).run()
    
    if form_data is None:
        await flash('Form not found', 'error')
        return redirect(url_for('forms.forms', guild_id=guild_id))

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Handle each field explicitly
        if 'name' in data:
            form_data.name = data['name']
        if 'description' in data:
            form_data.description = data['description']
        if 'questions' in data:
            form_data.questions = data['questions']
        if 'status' in data:
            form_data.status = data['status']
        
        # Handle settings separately
        if 'settings' in data:
            settings = data['settings']
            
            # Top-level settings
            if 'submission_channel' in settings:
                form_data.settings['submission_channel'] = settings['submission_channel']
            if 'submission_viewers' in settings:
                form_data.settings['submission_viewers'] = settings['submission_viewers']
            if 'submission_managers' in settings:
                form_data.settings['submission_managers'] = settings['submission_managers']
            
            # Handle options
            if 'options' in settings:
                if 'thread' in settings['options']:
                    form_data.settings['options']['thread'] = settings['options']['thread']
                if 'mentions' in settings['options']:
                    form_data.settings['options']['mentions'] = settings['options']['mentions']
                if 'reactions' in settings['options']:
                    if 'status' in settings['options']['reactions']:
                        form_data.settings['options']['reactions']['status'] = settings['options']['reactions']['status']
                    if 'emojis' in settings['options']['reactions']:
                        form_data.settings['options']['reactions']['emojis'] = settings['options']['reactions']['emojis']
        
        form_data.save()
        logger.info(f"Updated form {form_id} for guild {guild_id}")
        return jsonify({'status': 'success', 'message': 'Successfully updated form'})

    if request.method == 'DELETE':
        form_data.delete()
        logger.info(f"Deleted form {form_id} for guild {guild_id}")
        return jsonify({'status': 'success', 'message': 'Successfully deleted form'})

    return await render_template(
        "dashboard/plugins/forms/form_edit.html",
        user=current_user,
        guild=guild,
        data=form_data
    )