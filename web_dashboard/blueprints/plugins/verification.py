import discord
import asyncio
import logging
from quart import Blueprint, jsonify, render_template, request

from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, login_required, premium_module

verification_bp = Blueprint('verification', __name__)
logger = logging.getLogger(__name__)

@verification_bp.route("/dashboard/<int:guild_id>/verification", methods=['GET'])
@login_required
async def verify(guild_id):
    premium_module(guild_id, 'verification')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = Guild.get(str(guild.id)).run().dashboard.verification

    return await render_template(
        "dashboard/plugins/verification.html",
        user=current_user,
        guild=guild,
        data=config
    )


@verification_bp.route("/dashboard/<int:guild_id>/verification/publish", methods=['POST'])
async def verify_publish(guild_id):
    """Publish or update the verification message."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    data = await request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required data
    if not data.get('embed'):
        return jsonify({'status': 'error', 'message': 'Embed data is required'}), 400

    # Get the guild document
    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    verification_config = config.dashboard.verification

    async def publish():
        try:
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
                            logger.info(f"Updated verification message for guild {guild_id}")
                            return
                        except discord.NotFound:
                            logger.warning(f"Verification message not found for guild {guild_id}, recreating...")
                        except discord.Forbidden:
                            logger.error(f"No permissions to edit message in guild {guild_id}")
                            return
                        except Exception as e:
                            logger.error(f"Error editing verification message: {e}")
                            return

            # Get or create verification role
            role_id = verification_config.get('role')
            role = guild.get_role(int(role_id)) if role_id else None
            if role is None:
                try:
                    role = await guild.create_role(
                        name='Verified',
                        reason='Enabled verification system'
                    )
                    config.dashboard.verification['role'] = str(role.id)
                    config.save()
                    logger.info(f"Created Verified role for guild {guild_id}")
                except discord.Forbidden:
                    logger.error(f"No permissions to create role in guild {guild_id}")
                    return
                except Exception as e:
                    logger.error(f"Error creating role: {e}")
                    return

            # Get or create verification channel
            channel_id = verification_config.get('channel')
            channel = guild.get_channel(int(channel_id)) if channel_id else None
            if channel is None:
                try:
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
                    config.dashboard.verification['channel'] = str(channel.id)
                    config.save()
                    logger.info(f"Created verification channel for guild {guild_id}")
                except discord.Forbidden:
                    logger.error(f"No permissions to create channel in guild {guild_id}")
                    return
                except Exception as e:
                    logger.error(f"Error creating channel: {e}")
                    return

            # Set permissions
            try:
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
            except discord.Forbidden:
                logger.warning(f"Could not set permissions in guild {guild_id}")
            except Exception as e:
                logger.error(f"Error setting permissions: {e}")
            
            try:
                await guild.default_role.edit(
                    reason="Verification system enabled",
                    permissions=discord.Permissions(read_messages=False)
                )
            except discord.Forbidden:
                logger.warning(f"Could not edit default role in guild {guild_id}")
            except Exception as e:
                logger.error(f"Error editing default role: {e}")

            if role.id == int(verification_config.get('role', 0)):
                try:
                    await role.edit(
                        reason="Verification system enabled",
                        permissions=discord.Permissions(read_messages=True)
                    )
                except discord.Forbidden:
                    logger.warning(f"Could not edit Verified role in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error editing Verified role: {e}")

            # Send the verification message
            try:
                msg = await channel.send(embed=embed, view=view)
                
                # Save message ID and published status
                config.dashboard.verification['message_id'] = str(msg.id)
                config.dashboard.verification['message_published'] = True
                config.updated_at = discord.utils.utcnow()
                config.save()
                logger.info(f"Published verification message for guild {guild_id}")
            except discord.Forbidden:
                logger.error(f"No permissions to send message in guild {guild_id}")
            except Exception as e:
                logger.error(f"Error sending verification message: {e}")

        except Exception as e:
            logger.error(f"Error in publish task for guild {guild_id}: {e}", exc_info=True)

    asyncio.run_coroutine_threadsafe(publish(), v.client.loop)
    return jsonify({'status': 'success', 'message': 'Publishing verification message in background...'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/unpublish", methods=['POST'])
async def verify_unpublish(guild_id):
    """Delete the verification message."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    verification_config = config.dashboard.verification

    async def unpublish():
        try:
            channel_id = verification_config.get('channel')
            message_id = verification_config.get('message_id')
            
            if channel_id and message_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        msg = await channel.fetch_message(int(message_id))
                        await msg.delete()
                        logger.info(f"Deleted verification message for guild {guild_id}")
                    except discord.NotFound:
                        logger.warning(f"Verification message not found for guild {guild_id}")
                    except discord.Forbidden:
                        logger.error(f"No permissions to delete message in guild {guild_id}")
                    except Exception as e:
                        logger.error(f"Error deleting verification message: {e}")

            # Update dashboard
            config.dashboard.verification['message_published'] = False
            config.dashboard.verification['message_id'] = None
            config.updated_at = discord.utils.utcnow()
            config.save()
            logger.info(f"Unpublished verification for guild {guild_id}")
        
        except Exception as e:
            logger.error(f"Error in unpublish task for guild {guild_id}: {e}", exc_info=True)

    asyncio.run_coroutine_threadsafe(unpublish(), v.client.loop)
    return jsonify({'status': 'success', 'message': 'Unpublishing verification message in background...'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/update", methods=['POST'])
async def verify_update(guild_id):
    """Update a specific verification setting."""
    data = await request.get_json()
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

    logger.info(f"Updated verification setting {key} for guild {guild_id}")
    return jsonify({'status': 'success', 'message': 'Successfully updated verification settings'})