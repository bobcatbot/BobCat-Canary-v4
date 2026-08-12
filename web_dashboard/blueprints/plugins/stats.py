import discord
from flask import Blueprint, render_template, jsonify, request
from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, login_required

stats_bp = Blueprint('stats', __name__)

@stats_bp.route("/dashboard/<int:guild_id>/stats")
@login_required
def stats(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404
    
    config = Guild.get(str(guild.id)).run()
    stats_config = config.dashboard.stats if config else {}
    
    return render_template(
        "dashboard/plugins/stats.html",
        user=current_user,
        guild=guild,
        data=stats_config
    )

@stats_bp.route("/dashboard/<int:guild_id>/stats/setup", methods=["POST"])
@login_required
def stats_setup(guild_id):
    """Auto-create default stats channels."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({"status": "error", "message": "Guild not found"}), 404
    
    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({"status": "error", "message": "Guild config not found"}), 404
    
    # Check if already set up
    counters = config.dashboard.stats.get('counters', [])
    if any(c.get('channel_id') for c in counters):
        return jsonify({"status": "error", "message": "Stats already configured"}), 400
    
    # Create default counters
    default_counters = [
        {"target": "totalMembers", "text": "👥 Members: {count}", "channel_id": "", "count": 0},
        {"target": "onlineCount", "text": "🟢 Online: {count}", "channel_id": "", "count": 0},
        {"target": "totalChannels", "text": "📋 Channels: {count}", "channel_id": "", "count": 0},
        {"target": "botCount", "text": "🤖 Bots: {count}", "channel_id": "", "count": 0},
    ]
    
    async def create_channels():
        for counter in default_counters:
            try:
                channel = await guild.create_voice_channel(
                    name=counter["text"].format(count=0),
                    reason="Stats auto-setup"
                )
                counter["channel_id"] = str(channel.id)
            except Exception as e:
                print(f"Failed to create stats channel: {e}")
                return False
        return True
    
    # Run the async function
    import asyncio
    success = asyncio.run_coroutine_threadsafe(
        create_channels(), 
        v.client.loop
    ).result(timeout=30)
    
    if not success:
        return jsonify({"status": "error", "message": "Failed to create channels"}), 500
    
    # Save config
    config.dashboard.stats["counters"] = default_counters
    config.dashboard.stats["status"] = True
    config.updated_at = discord.utils.utcnow()
    config.save()
    
    return jsonify({"status": "success", "message": "Stats channels created"})

@stats_bp.route("/dashboard/<int:guild_id>/stats/reset", methods=["POST"])
@login_required
def stats_reset(guild_id):
    """Delete all stats channels and clear config."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({"status": "error", "message": "Guild not found"}), 404
    
    config = Guild.get(str(guild.id)).run()
    if config is None:
        return jsonify({"status": "error", "message": "Guild config not found"}), 404
    
    counters = config.dashboard.stats.get('counters', [])
    
    async def delete_channels():
        for counter in counters:
            channel_id = counter.get('channel_id')
            if channel_id:
                channel = guild.get_channel(int(channel_id))
                if channel and isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                    try:
                        await channel.delete(reason="Stats reset")
                    except:
                        pass
    
    # Run the async function
    import asyncio
    asyncio.run_coroutine_threadsafe(
        delete_channels(), 
        v.client.loop
    ).result(timeout=30)
    
    # Clear config
    config.dashboard.stats["counters"] = []
    config.dashboard.stats["status"] = False
    config.updated_at = discord.utils.utcnow()
    config.save()
    
    return jsonify({"status": "success", "message": "Stats channels deleted"})