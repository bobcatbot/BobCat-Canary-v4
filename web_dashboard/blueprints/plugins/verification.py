import discord
from flask import Blueprint, jsonify, render_template, request

from modules import bot as v
from modules.models import Guild
from ...db import get_guild
from ...utils import bearer_client, login_required, premium_module

verification_bp = Blueprint('verification', __name__)

@verification_bp.route("/dashboard/<int:guild_id>/verification", methods=['GET'])
@login_required
def verify(guild_id):
    premium_module(guild_id, 'verification')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    # Get the guild document using Bunnet
    config = Guild.get(str(guild.id)).run().dashboard.verification

    return render_template(
        "dashboard/plugins/verification.html",
        user=current_user,
        guild=guild,
        data=config
    )


@verification_bp.route("/dashboard/<int:guild_id>/verification/publish", methods=['POST'])
def verify_publish(guild_id):
    """Publish or update the verification message."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Get the guild document
    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    verification_config = config.dashboard.verification

    async def publish():
        embed = discord.Embed.from_dict(data.get('embed', {}))
        btn_data = data.get('btn', {})
        
        style_map = {
            'secondary': discord.ButtonStyle.gray,
            'blurple': discord.ButtonStyle.blurple,
            'danger': discord.ButtonStyle.red,
            'success': discord.ButtonStyle.green,
        }
        style = style_map.get(btn_data.get('color', 'blurple'), discord.ButtonStyle.blurple)

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            emoji=btn_data.get('emoji') or None,
            label=btn_data.get('title', 'Verify'),
            style=style,
            custom_id='Verification'
        ))

        # Check if already published
        if verification_config.get('message_published', False):
            channel_id = verification_config.get('channel')
            message_id = verification_config.get('message_id')
            if channel_id and message_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        msg = await channel.fetch_message(int(message_id))
                        await msg.edit(embed=embed, view=view)
                        return
                    except discord.NotFound:
                        # Message was deleted, fall through to republish
                        pass

        # Get or create verification role
        role_id = verification_config.get('role')
        role = guild.get_role(int(role_id)) if role_id else None
        if role is None:
            role = await guild.create_role(
                name='Verified',
                reason='Enabled verification system'
            )
            # Save the role ID back to dashboard
            config.dashboard.verification['role'] = str(role.id)
            config.save()

        # Get or create verification channel
        channel_id = verification_config.get('channel')
        channel = guild.get_channel(int(channel_id)) if channel_id else None
        if channel is None:
            channel = await guild.create_text_channel(
                'verification',
                reason='Enabled verification system',
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=False,
                        read_message_history=True
                    ),
                    role: discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=False,
                        read_message_history=True
                    ),
                }
            )
            # Save the channel ID back to dashboard
            config.dashboard.verification['channel'] = str(channel.id)
            config.save()

        # Set permissions
        await channel.set_permissions(
            guild.default_role,
            overwrite=discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False
            )
        )
        await channel.set_permissions(
            role,
            overwrite=discord.PermissionOverwrite(
                read_messages=False,
                send_messages=False
            )
        )
        
        try:
            await guild.default_role.edit(
                reason="Verification system enabled",
                permissions=discord.Permissions(read_messages=False)
            )
        except discord.Forbidden:
            pass

        if role.id == int(verification_config.get('role', 0)):
            try:
                await role.edit(
                    reason="Verification system enabled",
                    permissions=discord.Permissions(read_messages=True)
                )
            except discord.Forbidden:
                pass

        # Send the verification message
        msg = await channel.send(embed=embed, view=view)
        
        # Save message ID and published status
        config.dashboard.verification['message_id'] = str(msg.id)
        config.dashboard.verification['message_published'] = True
        config.updated_at = discord.utils.utcnow()
        config.save()

    v.client.loop.create_task(publish())
    return jsonify({'status': 'success', 'message': 'Successfully published verification message'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/unpublish", methods=['POST'])
def verify_unpublish(guild_id):
    """Delete the verification message."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    verification_config = config.dashboard.verification

    async def unpublish():
        channel_id = verification_config.get('channel')
        message_id = verification_config.get('message_id')
        
        if channel_id and message_id:
            channel = guild.get_channel(int(channel_id))
            if channel:
                try:
                    msg = await channel.fetch_message(int(message_id))
                    await msg.delete()
                except discord.NotFound:
                    pass  # Message already deleted

        # Update dashboard
        config.dashboard.verification['message_published'] = False
        config.dashboard.verification['message_id'] = None
        config.updated_at = discord.utils.utcnow()
        config.save()

    v.client.loop.create_task(unpublish())
    return jsonify({'status': 'success', 'message': 'Successfully deleted verification message'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/update", methods=['POST'])
def verify_update(guild_id):
    """Update a specific verification setting."""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    key = data.get('key')
    value = data.get('value')

    if not key:
        return jsonify({'status': 'error', 'message': 'No key provided'}), 400

    # Handle nested keys like "message.embed.title"
    parts = key.split('.')
    current = config.dashboard.verification
    
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            current = getattr(current, part, {})
    
    final = parts[-1]
    if isinstance(current, dict):
        current[final] = value
    else:
        setattr(current, final, value)
    
    config.updated_at = discord.utils.utcnow()
    config.save()

    return jsonify({'status': 'success', 'message': 'Successfully updated verification settings'})