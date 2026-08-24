import discord
import asyncio
import logging
from quart import Blueprint, request, render_template, redirect, url_for, jsonify, flash

from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, login_required, premium_module

temporary_channels_bp = Blueprint('temporary_channels', __name__)
logger = logging.getLogger(__name__)


@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels")
@login_required
async def temporary_channels(guild_id):
    premium_module(guild_id, 'temporary_channels')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Bunnet
    config = Guild.get(str(guild.id)).run().dashboard.temporary_channels
    
    return await render_template(
        "dashboard/plugins/temporary_channels/tc_index.html",
        user=current_user,
        guild=guild,
        data=config
    )


@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels/creation", methods=['GET', 'POST'])
@login_required
async def temporary_channels_create(guild_id):
    premium_module(guild_id, 'temporary_channels')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Validate required fields
        if not data.get('hub_name'):
            return jsonify({'status': 'error', 'message': 'Hub name is required'}), 400

        # Generate a unique ID for the hub
        data['id'] = v.uuid(length=12, strCase='upper/lower/nums')

        async def create_hub():
            try:
                # Get the guild document
                config = Guild.get(str(guild.id)).run()
                if config is None:
                    logger.error(f"Guild config not found for {guild_id}")
                    return

                # Ensure temporary_channels exists
                if not hasattr(config.dashboard, 'temporary_channels'):
                    config.dashboard.temporary_channels = {}
                
                hubs = config.dashboard.temporary_channels.get('hubs', [])

                # Create the Discord channel
                category = None
                if data.get('sync_hub_category'):
                    category_id = data.get('category_id')
                    if category_id:
                        category = guild.get_channel(int(category_id))
                        if category is None:
                            logger.error(f"Category {category_id} not found for guild {guild_id}")
                            return
                    else:
                        try:
                            category = await guild.create_category_channel(
                                data.get('hub_name', 'Temporary Channels'),
                                reason=f"Temp category for hub {data['id']}"
                            )
                            data['category_id'] = str(category.id)
                            logger.info(f"Created category for hub {data['id']} in guild {guild_id}")
                        except discord.Forbidden:
                            logger.error(f"No permissions to create category in guild {guild_id}")
                            return
                        except Exception as e:
                            logger.error(f"Error creating category: {e}")
                            return
                else:
                    category = guild

                # Create the voice channel
                try:
                    vc = await category.create_voice_channel(
                        data.get('hub_name', 'Hub - Join to create'),
                        user_limit=int(data.get('user_limit', 4)),
                        bitrate=int(data.get('bitrate', 64000)),
                        reason=f"Temp voice channel for hub {data['id']}"
                    )
                    data['channel_id'] = str(vc.id)
                    logger.info(f"Created voice channel for hub {data['id']} in guild {guild_id}")
                except discord.Forbidden:
                    logger.error(f"No permissions to create voice channel in guild {guild_id}")
                    return
                except Exception as e:
                    logger.error(f"Error creating voice channel: {e}")
                    return

                # Save to dashboard
                hubs.append(data)
                config.dashboard.temporary_channels['hubs'] = hubs
                config.updated_at = discord.utils.utcnow()
                config.save()
                logger.info(f"Saved hub {data['id']} for guild {guild_id}")
            
            except Exception as e:
                logger.error(f"Error creating hub for guild {guild_id}: {e}", exc_info=True)

        # Fire and forget
        asyncio.create_task(create_hub())
        
        await flash(f"Successfully created hub {data['id']}", 'success')
        return jsonify({'status': 'success', 'message': f"Successfully created hub {data['id']}"})

    return await render_template(
        "dashboard/plugins/temporary_channels/tc_create.html",
        user=current_user,
        guild=guild
    )


@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/edition", methods=['GET', 'POST'])
@login_required
async def temporary_channels_edit(guild_id, hub_id):
    premium_module(guild_id, 'temporary_channels')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document
    config = Guild.get(str(guild.id)).run()
    if config is None:
        await flash('Guild config not found', 'error')
        return redirect(url_for('temporary_channels.temporary_channels', guild_id=guild_id))

    hubs = config.dashboard.temporary_channels.get('hubs', [])
    hub = next((h for h in hubs if h.get('id') == hub_id), None)
    
    if hub is None:
        await flash('Hub not found', 'error')
        return redirect(url_for('temporary_channels.temporary_channels', guild_id=guild_id))

    hub_idx = hubs.index(hub)

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        async def edit_hub():
            try:
                # Get fresh config
                config = Guild.get(str(guild.id)).run()
                if config is None:
                    return

                hubs = config.dashboard.temporary_channels.get('hubs', [])
                
                # Update the hub data
                for key, value in data.items():
                    hubs[hub_idx][key] = value

                # Update Discord channel if it exists
                channel_id = hubs[hub_idx].get('channel_id')
                if channel_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        try:
                            category = None
                            if data.get('sync_hub_category') and data.get('category_id'):
                                category = guild.get_channel(int(data['category_id']))
                            
                            await channel.edit(
                                name=data.get('hub_name', channel.name),
                                category=category,
                                user_limit=int(data.get('user_limit', channel.user_limit or 0)),
                                bitrate=int(data.get('bitrate', channel.bitrate or 64000))
                            )
                            logger.info(f"Updated Discord channel for hub {hub_id} in guild {guild_id}")
                        except discord.Forbidden:
                            logger.error(f"No permissions to edit channel in guild {guild_id}")
                        except Exception as e:
                            logger.error(f"Error editing channel: {e}")

                config.dashboard.temporary_channels['hubs'] = hubs
                config.updated_at = discord.utils.utcnow()
                config.save()
                logger.info(f"Updated hub {hub_id} for guild {guild_id}")
            
            except Exception as e:
                logger.error(f"Error editing hub for guild {guild_id}: {e}", exc_info=True)

        # Fire and forget
        asyncio.create_task(edit_hub())
        
        await flash(f"Successfully updated hub {hub['id']}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully updated hub'})

    return await render_template(
        "dashboard/plugins/temporary_channels/tc_edit.html",
        user=current_user,
        guild=guild,
        data=hub
    )


@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/delete", methods=['DELETE'])
@login_required
async def temporary_channels_delete(guild_id, hub_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    hubs = config.dashboard.temporary_channels.get('hubs', [])
    hub = next((h for h in hubs if h.get('id') == hub_id), None)
    
    if hub is None:
        return jsonify({'status': 'error', 'message': 'Hub not found'}), 404

    async def delete_hub():
        try:
            # Get fresh config
            config = Guild.get(str(guild.id)).run()
            if config is None:
                return

            hubs = config.dashboard.temporary_channels.get('hubs', [])
            hub = next((h for h in hubs if h.get('id') == hub_id), None)
            
            if hub is None:
                return

            # Delete Discord channel
            channel_id = hub.get('channel_id')
            if channel_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        await channel.delete(reason=f"Hub {hub_id} deleted")
                        logger.info(f"Deleted voice channel for hub {hub_id} in guild {guild_id}")
                    except discord.Forbidden:
                        logger.error(f"No permissions to delete channel in guild {guild_id}")
                    except Exception as e:
                        logger.error(f"Error deleting channel: {e}")

            # Delete category if it was synced
            if hub.get('sync_hub_category') and hub.get('category_id'):
                category = guild.get_channel(int(hub['category_id']))
                if category:
                    try:
                        await category.delete(reason=f"Hub {hub_id} deleted")
                        logger.info(f"Deleted category for hub {hub_id} in guild {guild_id}")
                    except discord.Forbidden:
                        logger.error(f"No permissions to delete category in guild {guild_id}")
                    except Exception as e:
                        logger.error(f"Error deleting category: {e}")

            # Remove from config
            hub_idx = hubs.index(hub)
            hubs.pop(hub_idx)
            config.dashboard.temporary_channels['hubs'] = hubs
            config.updated_at = discord.utils.utcnow()
            config.save()
            logger.info(f"Deleted hub {hub_id} for guild {guild_id}")
        
        except Exception as e:
            logger.error(f"Error deleting hub for guild {guild_id}: {e}", exc_info=True)

    # Fire and forget
    asyncio.create_task(delete_hub())
    
    await flash(f"Successfully deleted hub {hub_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted hub'})