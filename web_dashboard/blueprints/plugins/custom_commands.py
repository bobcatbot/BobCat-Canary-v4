import discord
from pydantic import ValidationError
from quart import Blueprint, render_template, redirect, url_for, flash, jsonify, request

from modules import bot as v
from modules.models import Guild, CustomCommand
from modules.models.custom_commands import role_is_grantable
from ...utils import get_current_user, plugin_guard

custom_commands_bp = Blueprint('custom_commands', __name__)


def _form_context(guild):
    return dict(
        guild=guild,
        roles=[
            {"id": r.id, "name": r.name, "color": r.color.value, "disabled": not role_is_grantable(r, guild.me)}
            for r in reversed(guild.roles)
        ],
    )


def _validate(guild, data, commands, skip_id=None):
    """Returns (command, None) or (None, error message)."""
    try:
        command = CustomCommand(**data)
    except ValidationError:
        return None, 'Invalid command data'

    command.trigger = command.trigger.strip()
    command.reply = command.reply.strip()
    if not command.trigger:
        return None, 'A trigger is required'

    if command.action == 'reply':
        command.role_id = ''
        if not command.reply:
            return None, 'A reply is required'
    else:
        role = guild.get_role(int(command.role_id)) if command.role_id.isdigit() else None
        if role is None:
            return None, 'Pick a role'
        if not role_is_grantable(role, guild.me):
            return None, "That role can't be handed out (it's above the bot, managed, or has powerful permissions)"

    for other in commands:
        if other.id != skip_id and other.trigger.lower() == command.trigger.lower() and other.match == command.match:
            return None, 'A command with that trigger and match type already exists'

    return command, None


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands")
@plugin_guard('custom_commands')
async def custom_commands(guild_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    doc = await Guild.get(str(guild.id))
    config = doc.dashboard.custom_commands

    # Commands saved before ids existed get one here, so every link below has a stable id.
    if any(not c.id for c in config.commands):
        for c in config.commands:
            c.id = c.id or v.uuid()
        await doc.save()

    return await render_template(
        "dashboard/plugins/custom_commands/custom_commands_index.html",
        user=get_current_user(),
        guild=guild,
        data=config,
        role_names={str(r.id): r.name for r in guild.roles},
    )


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands/creation", methods=['GET', 'POST'])
@plugin_guard('custom_commands')
async def custom_commands_create(guild_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == "POST":
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        config = await Guild.get(str(guild.id))
        commands = config.dashboard.custom_commands.commands
        command, error = _validate(guild, data, commands)
        if error:
            return jsonify({'status': 'error', 'message': error}), 400

        command.id = v.uuid()
        commands.append(command)
        config.updated_at = discord.utils.utcnow()
        await config.save()

        await flash("Successfully created command", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully created command'})

    return await render_template(
        "dashboard/plugins/custom_commands/custom_commands_form.html",
        user=get_current_user(),
        data=CustomCommand(trigger=''),
        is_edit=False,
        **_form_context(guild),
    )


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands/<command_id>/edition", methods=['GET', 'POST'])
@plugin_guard('custom_commands')
async def custom_commands_edit(guild_id, command_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = await Guild.get(str(guild.id))
    commands = config.dashboard.custom_commands.commands
    index = next((i for i, c in enumerate(commands) if c.id == command_id), None)
    if index is None:
        await flash('Command not found', 'danger')
        return redirect(url_for('custom_commands.custom_commands', guild_id=guild_id))

    if request.method == "POST":
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        command, error = _validate(guild, data, commands, skip_id=command_id)
        if error:
            return jsonify({'status': 'error', 'message': error}), 400

        command.id = command_id
        command.enabled = commands[index].enabled  # the form doesn't carry the toggle, so keep it
        commands[index] = command
        config.updated_at = discord.utils.utcnow()
        await config.save()

        await flash("Successfully updated command", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully updated command'})

    return await render_template(
        "dashboard/plugins/custom_commands/custom_commands_form.html",
        user=get_current_user(),
        data=commands[index],
        is_edit=True,
        **_form_context(guild),
    )


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands/<command_id>/toggle", methods=['POST'])
@plugin_guard('custom_commands')
async def custom_commands_toggle(guild_id, command_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    data = await request.get_json()
    config = await Guild.get(str(guild.id))
    command = next((c for c in config.dashboard.custom_commands.commands if c.id == command_id), None)
    if command is None or not data or not isinstance(data.get('enabled'), bool):
        return jsonify({'status': 'error', 'message': 'Command not found'}), 404

    command.enabled = data['enabled']
    config.updated_at = discord.utils.utcnow()
    await config.save()
    return jsonify({'status': 'success', 'message': 'Command updated'})


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands/<command_id>/duplicate", methods=['POST'])
@plugin_guard('custom_commands')
async def custom_commands_duplicate(guild_id, command_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    commands = config.dashboard.custom_commands.commands
    index = next((i for i, c in enumerate(commands) if c.id == command_id), None)
    if index is None:
        return jsonify({'status': 'error', 'message': 'Command not found'}), 404

    # Same trigger and match type would never be reachable, so the copy gets a suffixed trigger to edit.
    copy = commands[index].model_copy(update={'id': v.uuid(), 'trigger': commands[index].trigger + '-copy'})
    commands.insert(index + 1, copy)
    config.updated_at = discord.utils.utcnow()
    await config.save()

    await flash("Successfully duplicated command", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully duplicated command'})


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands/<command_id>/delete", methods=['DELETE'])
@plugin_guard('custom_commands')
async def custom_commands_delete(guild_id, command_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    commands = config.dashboard.custom_commands.commands
    index = next((i for i, c in enumerate(commands) if c.id == command_id), None)
    if index is None:
        return jsonify({'status': 'error', 'message': 'Command not found'}), 404

    del commands[index]
    config.updated_at = discord.utils.utcnow()
    await config.save()

    await flash("Successfully deleted command", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted command'})
