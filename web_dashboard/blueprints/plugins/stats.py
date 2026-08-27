import asyncio
import discord
import logging
from quart import Blueprint, request, render_template, jsonify

from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, login_required, premium_module

stats_bp = Blueprint('stats', __name__)
logger = logging.getLogger(__name__)

async def run_on_bot_loop(coro):
    """Schedule coroutine on bot's event loop and await result."""
    future = asyncio.run_coroutine_threadsafe(coro, v.client.loop)
    try:
        return await asyncio.wrap_future(future)
    except asyncio.CancelledError:
        future.cancel()
        raise


@stats_bp.route("/dashboard/<int:guild_id>/stats")
@login_required
async def stats(guild_id):
    await premium_module(guild_id, 'stats')

    current_user = bearer_client().get_current_user()

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = await Guild.get(str(guild.id))
    stats_config = config.dashboard.stats if config else {}

    return await render_template(
        "dashboard/plugins/stats.html",
        user=current_user,
        guild=guild,
        data=stats_config
    )


@stats_bp.route("/dashboard/<int:guild_id>/stats/setup", methods=['POST'])
@login_required
async def stats_setup(guild_id):
    """Auto-create default stats channels."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    # Check if already set up
    counters = config.dashboard.stats.get('counters', [])
    if any(c.get('channel_id') for c in counters):
        return jsonify({'status': 'error', 'message': 'Stats already configured'}), 400

    # Default counters
    default_counters = [
        {"target": "humanCount", "text": "Humans: {count}", "channel_id": "", "count": 0, "position": 0,},
        {"target": "botsCount", "text": "Bots: {count}", "channel_id": "", "count": 0, "position": 1,},
    ]

    created_count = 0
    for counter in default_counters:
        try:
            channel = await run_on_bot_loop(guild.create_voice_channel(
                name=counter["text"].format(count=0),
                reason="Stats auto-setup",
                user_limit=0,
            ))
            counter["channel_id"] = str(channel.id)
            counter["count"] = 0
            created_count += 1
            logger.info(f"Created stats channel {channel.name} for guild {guild_id}")
        except discord.Forbidden:
            return jsonify({'status': 'error', 'message': 'No permissions to create voice channels'}), 403
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Save config
    config.dashboard.stats["counters"] = default_counters
    config.updated_at = discord.utils.utcnow()
    await config.save()
    logger.info(f"Setup stats channels for guild {guild_id}")

    return jsonify({
        'status': 'success',
        'message': f'Successfully created {created_count} stats channels',
        'created': created_count
    })


@stats_bp.route("/dashboard/<int:guild_id>/stats/refresh", methods=['POST'])
@login_required
async def stats_refresh(guild_id):
    """Force refresh stats channels."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    cog = v.client.get_cog("Stats")
    if cog is None:
        return jsonify({'status': 'error', 'message': 'Stats cog not loaded'}), 404

    await run_on_bot_loop(cog.update_guild_stats(guild, force=True))
    logger.info(f"Refreshed stats for guild {guild_id}")

    return jsonify({'status': 'success', 'message': 'Stats refreshed'})


@stats_bp.route("/dashboard/<int:guild_id>/stats/create-counter", methods=['POST'])
@login_required
async def stats_create_counter(guild_id):
    """Create a new voice channel and add it as a counter."""
    data = await request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    target = data.get('target')
    template = data.get('template', f"{target}: {{count}}")
    formated_target = data.get('formated_target', target)

    if not target:
        return jsonify({'status': 'error', 'message': 'Target is required'}), 400

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    # Create the voice channel on the bot's loop
    channel = await run_on_bot_loop(guild.create_voice_channel(
        name=template.format(kind=formated_target, count=0),
        reason=f"Stats counter for {target}",
        user_limit=0,
    ))
    logger.info(f"Created stats counter channel {channel.name} for guild {guild_id}")

    # Add the counter to config
    counters = config.dashboard.stats.get('counters', [])
    new_counter = {
        "target": target,
        "text": template.format(kind=formated_target, count='{count}'),
        "channel_id": str(channel.id),
        "count": 0,
        "position": 0,
    }
    counters.append(new_counter)
    counter_index = len(counters) - 1

    # Save config
    config.dashboard.stats["counters"] = counters
    config.updated_at = discord.utils.utcnow()
    await config.save()
    logger.info(f"Saved counter {target} for guild {guild_id}")

    # Force an immediate update
    cog = v.client.get_cog("Stats")
    if cog:
        await run_on_bot_loop(
            cog.update_guild_stats(guild, force=True)
        )

    return jsonify({
        'status': 'success',
        'message': f"Successfully created counter for {target}",
        'channel_id': channel.id,
        'channel_name': channel.name,
        'counter': new_counter,
        'index': counter_index
    }), 200


@stats_bp.route("/dashboard/<int:guild_id>/stats/counter/<int:counter_idx>/delete", methods=['DELETE'])
@login_required
async def stats_delete_counter(guild_id, counter_idx):
    """Delete a specific counter and its associated channel."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    counters = config.dashboard.stats.get('counters', [])
    if counter_idx >= len(counters):
        return jsonify({'status': 'error', 'message': 'Counter not found'}), 404

    counter = counters[counter_idx]

    # Delete Discord channel
    channel_id = counter.get('channel_id')
    if channel_id:
        channel = guild.get_channel(int(channel_id))
        if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            try:
                await run_on_bot_loop(channel.delete(
                    reason="Stats counter deleted"
                ))
                logger.info(f"Deleted stats counter channel for guild {guild_id}")
            except discord.Forbidden:
                logger.error(f"No permissions to delete channel in guild {guild_id}")
                return jsonify({'status': 'error', 'message': 'No permissions to delete channel'}), 403

    # Remove from config
    counters.pop(counter_idx)
    config.dashboard.stats["counters"] = counters
    config.updated_at = discord.utils.utcnow()
    await config.save()
    logger.info(f"Deleted counter {counter_idx} for guild {guild_id}")

    return jsonify({'status': 'success', 'message': 'Successfully deleted counter'})


@stats_bp.route("/dashboard/<int:guild_id>/stats/reset", methods=['POST'])
@login_required
async def stats_reset(guild_id):
    """Delete all stats channels and clear config."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    counters = config.dashboard.stats.get('counters', [])

    for counter in counters:
        channel_id = counter.get('channel_id')
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                try:
                    await run_on_bot_loop(channel.delete(
                        reason="Stats reset"
                    ))
                    logger.info(f"Deleted stats channel for guild {guild_id}")
                except discord.Forbidden:
                    logger.warning(f"No permissions to delete channel in guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error deleting channel: {e}")

    # Clear config
    config.dashboard.stats["counters"] = []
    config.updated_at = discord.utils.utcnow()
    await config.save()
    logger.info(f"Reset all stats for guild {guild_id}")

    return jsonify({'status': 'success', 'message': 'Successfully deleted all stats channels'})

@stats_bp.route("/dashboard/<int:guild_id>/stats/reorder", methods=['POST'])
@login_required
async def stats_reorder(guild_id):
    """Apply new order to stats channels."""
    data = await request.get_json()
    if not data or 'order' not in data:
        return jsonify({'status': 'error', 'message': 'Order data required'}), 400

    new_order = data['order']
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Config not found'}), 404

    counters = config.dashboard.stats.get('counters', [])
    counter_map = {c['target']: c for c in counters}

    # Reorder counters
    ordered_counters = []
    for target in new_order:
        if target in counter_map:
            ordered_counters.append(counter_map[target])

    # Add any missing counters at the end
    existing_targets = set(c['target'] for c in ordered_counters)
    for counter in counters:
        if counter['target'] not in existing_targets:
            ordered_counters.append(counter)

    # Save to database
    config.dashboard.stats["counters"] = ordered_counters
    config.updated_at = discord.utils.utcnow()
    await config.save()

    # Reorder Discord channels
    stats_channels = []
    for counter in ordered_counters:
        channel_id = counter.get('channel_id')
        if channel_id:
            channel = guild.get_channel(int(channel_id))
            if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                stats_channels.append(channel)

    if stats_channels:
        category = stats_channels[0].category if stats_channels[0].category else None
        for idx, channel in enumerate(reversed(stats_channels)):
            try:
                new_position = len(stats_channels) - 1 - idx
                if category:
                    await run_on_bot_loop(channel.edit(
                        position=new_position,
                        category=category
                    ))
                else:
                    await run_on_bot_loop(channel.edit(position=new_position))
            except discord.HTTPException as e:
                logger.warning(f"Failed to reorder channel {channel.name}: {e}")
            await asyncio.sleep(0.3)

    logger.info(f"Reordered stats channels for guild {guild_id}")

    return jsonify({
        'status': 'success',
        'message': f'Successfully reordered {len(ordered_counters)} stats channels'
    })