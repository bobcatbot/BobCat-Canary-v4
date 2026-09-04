import discord
import asyncio
import logging
from quart import Blueprint, request, flash, jsonify, render_template, redirect, url_for

from modules import bot as v
from modules.models import Guild, Giveaway
from ...utils import bearer_client, plugin_guard

giveaways_bp = Blueprint('giveaways', __name__)
logger = logging.getLogger(__name__)


def _build_giveaway_embed(giveaway):
    """Build the live giveaway embed for a Giveaway document."""
    embed = discord.Embed(
        title=giveaway.embed_title or f"🎉 {giveaway.prize} 🎉",
        description=giveaway.embed_desc,
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="Ends",
        value=f"<t:{int(giveaway.end_epoch)}:R> (<t:{int(giveaway.end_epoch)}:f>)",
        inline=False
    )
    embed.add_field(name="Hosted by", value=f"<@{giveaway.author_id}>", inline=False)
    embed.add_field(name="Winners", value=f"**{giveaway.winner_count}**", inline=False)
    embed.add_field(name="Participants", value=f"**{len(giveaway.participants)}**", inline=False)
    embed.set_footer(text=f"Giveaway ID: {giveaway.id}")
    return embed


def _apply_giveaway_fields(giveaway, data):
    """Apply a dashboard edit payload (flat dotted keys) onto a Giveaway document."""
    for key, value in data.items():
        if key == 'time.epoch':
            giveaway.end_epoch = float(value or 0)
        elif key == 'time.timestamp':
            giveaway.end_timestamp = value
        elif key == 'name':
            giveaway.name = value
        elif key == 'channel_id' and value:
            giveaway.channel_id = str(value)
        elif key == 'prize':
            giveaway.prize = value
        elif key == 'winners':
            giveaway.winner_count = int(value or 1)
        elif key == 'embed.desc':
            giveaway.embed_desc = value
        elif key == 'give_xp.enabled':
            giveaway.give_xp['enabled'] = bool(value)
        elif key == 'give_xp.amount':
            giveaway.give_xp['amount'] = int(value or 0)
        elif key == 'give_coins.enabled':
            giveaway.give_coins['enabled'] = bool(value)
        elif key == 'give_coins.amount':
            giveaway.give_coins['amount'] = int(value or 0)


async def _send_giveaway_message(guild, giveaway):
    """Post the live giveaway message and stamp message_id + Ongoing status onto
    the document (caller is responsible for persisting). Returns (ok, error)."""
    channel = guild.get_channel(int(giveaway.channel_id))
    if channel is None:
        return False, 'Channel not found'

    view = discord.ui.View(timeout=None)
    view.add_item(discord.ui.Button(
        label="🎯 Join Giveaway",
        style=discord.ButtonStyle.blurple,
        custom_id="JoinGiveaway"
    ))

    try:
        msg = await channel.send(embed=_build_giveaway_embed(giveaway), view=view)
    except discord.Forbidden:
        return False, "I don't have permission to send messages in that channel"
    except Exception as e:
        logger.error(f"Error sending giveaway message for {giveaway.id}: {e}", exc_info=True)
        return False, 'Failed to send giveaway message'

    giveaway.message_id = str(msg.id)
    giveaway.status = 'Ongoing'
    return True, None


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways")
@plugin_guard('giveaway')
async def giveaways(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the giveaway config from dashboard
    config = (await Guild.get(str(guild.id))).dashboard.giveaways
    
    # Get all giveaways for this guild
    giveaways_list = await Giveaway.find(Giveaway.guild_id == str(guild.id)).to_list()

    logger.info(f"Loaded {len(giveaways_list)} giveaways for guild {guild_id}")
    
    return await render_template(
        "dashboard/plugins/giveaways/gway_index.html",
        user=current_user,
        guild=guild,
        config=config,
        data=giveaways_list
    )


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/creation", methods=['GET', 'POST'])
@plugin_guard('giveaway')
async def giveaways_creation(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Validate required fields
        if not data.get('channel_id'):
            return jsonify({'status': 'error', 'message': 'Channel ID is required'}), 400
        
        if not data.get('prize'):
            return jsonify({'status': 'error', 'message': 'Prize is required'}), 400

        uuid = v.uuid(length=12, strCase="upper/lower/nums")
        channel = guild.get_channel(int(data['channel_id']))
        
        if not channel:
            return jsonify({'status': 'error', 'message': 'Channel not found'}), 400

        giveaway_data = {
            'id': uuid,
            'guild_id': str(guild.id),
            'name': data.get('name', 'giveaway'),
            'prize': data.get('prize', ''),
            'status': 'Draft',
            'channel_id': str(channel.id),
            'channel_name': channel.name,
            'message_id': '',
            'author_id': str(current_user.id),
            'embed_title': data.get('embed.title', ''),
            'embed_desc': data.get('embed.desc', ''),
            'end_epoch': float(data.get('time.epoch') or 0),
            'end_timestamp': data.get('time.timestamp', ''),
            'winner_count': int(data.get('winners') or 1),
            'participants': [],
            'winners': [],
            'give_xp': {
                'enabled': bool(data.get('give_xp.enabled', False)),
                'amount': int(data.get('give_xp.amount') or 0)
            },
            'give_coins': {
                'enabled': bool(data.get('give_coins.enabled', False)),
                'amount': int(data.get('give_coins.amount') or 0)
            }
        }

        giveaway = Giveaway(**giveaway_data)

        if data.get('button') == 'publish':
            if not giveaway.end_epoch or giveaway.end_epoch <= 0:
                return jsonify({'status': 'error', 'message': 'Set an end time before publishing'}), 400

            ok, error = await _send_giveaway_message(guild, giveaway)
            if not ok:
                return jsonify({'status': 'error', 'message': error}), 400

            await giveaway.insert()
            await flash('Giveaway published successfully!', 'success')
            logger.info(f"Published giveaway {uuid} for guild {guild_id}")
            return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})

        # Default: save as draft
        await giveaway.insert()
        await flash('Giveaway saved successfully!', 'success')
        logger.info(f"Saved giveaway draft {uuid} for guild {guild_id}")
        return jsonify({'status': 'success', 'message': 'Giveaway saved successfully!'})

    return await render_template(
        "dashboard/plugins/giveaways/gway_create.html",
        user=current_user,
        guild=guild
    )


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/edition", methods=['GET', 'POST'])
@plugin_guard('giveaway')
async def giveaways_edition(guild_id, gway_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the giveaway using Beanie
    giveaway = await Giveaway.find_one(
        Giveaway.guild_id == str(guild.id),
        Giveaway.id == gway_id
    )
    
    if giveaway is None:
        await flash('Giveaway not found', 'error')
        return redirect(url_for('giveaways.giveaways', guild_id=guild_id))

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        async def update_giveaway():
            try:
                _apply_giveaway_fields(giveaway, data)

                # Update the Discord message if it exists
                if giveaway.message_id and giveaway.channel_id:
                    channel = guild.get_channel(int(giveaway.channel_id))
                    if channel:
                        try:
                            msg = await channel.fetch_message(int(giveaway.message_id))
                            embed = discord.Embed.from_dict(msg.embeds[0].to_dict())
                            embed.title = f"🎉 {giveaway.prize} 🎉"
                            embed.description = giveaway.embed_desc
                            embed.fields[0].value = f"<t:{int(giveaway.end_epoch)}:R> (<t:{int(giveaway.end_epoch)}:f>)"
                            embed.fields[2].value = f"**{giveaway.winner_count}**"
                            embed.fields[3].value = f"**{len(giveaway.participants)}**"
                            await msg.edit(embed=embed)
                            logger.info(f"Updated giveaway message for {gway_id} in guild {guild_id}")
                        except discord.NotFound:
                            logger.warning(f"Giveaway message not found for {gway_id} in guild {guild_id}")
                        except Exception as e:
                            logger.error(f"Error updating giveaway message: {e}")

                await giveaway.save()
                logger.info(f"Updated giveaway {gway_id} for guild {guild_id}")
            
            except Exception as e:
                logger.error(f"Error updating giveaway for guild {guild_id}: {e}", exc_info=True)

        # Fire and forget
        asyncio.create_task(update_giveaway())
        
        await flash('Giveaway updated successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Giveaway updated successfully!'})

    return await render_template(
        "dashboard/plugins/giveaways/gway_edit.html",
        user=current_user,
        guild=guild,
        data=dict(giveaway)
    )


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/publish", methods=['POST'])
@plugin_guard('giveaway')
async def giveaways_publish(guild_id, gway_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    giveaway = await Giveaway.find_one(
        Giveaway.guild_id == str(guild.id),
        Giveaway.id == gway_id
    )
    if giveaway is None:
        return jsonify({'status': 'error', 'message': 'Giveaway not found'}), 404

    if giveaway.status != 'Draft':
        return jsonify({'status': 'error', 'message': 'Only drafts can be published'}), 400

    # apply any pending edits sent alongside the publish request
    pending = await request.get_json(silent=True) or {}
    if pending:
        _apply_giveaway_fields(giveaway, pending)

    if not giveaway.end_epoch or giveaway.end_epoch <= 0:
        return jsonify({'status': 'error', 'message': 'Set an end time before publishing'}), 400

    ok, error = await _send_giveaway_message(guild, giveaway)
    if not ok:
        return jsonify({'status': 'error', 'message': error}), 400

    await giveaway.save()
    await flash('Giveaway published successfully!', 'success')
    logger.info(f"Published draft giveaway {gway_id} for guild {guild_id}")
    return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/delete", methods=['DELETE'])
@plugin_guard('giveaway')
async def giveaways_delete(guild_id, gway_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    giveaway = await Giveaway.find_one(
        Giveaway.guild_id == str(guild.id),
        Giveaway.id == gway_id
    )
    if giveaway is None:
        return jsonify({'status': 'error', 'message': 'Giveaway not found'}), 404

    if giveaway.message_id and giveaway.channel_id:
        channel = guild.get_channel(int(giveaway.channel_id))
        if channel:
            try:
                msg = await channel.fetch_message(int(giveaway.message_id))
                await msg.delete()
            except Exception:
                pass  # message may already be gone

    await giveaway.delete()
    logger.info(f"Deleted giveaway {gway_id} for guild {guild_id}")
    return jsonify({'status': 'success', 'message': 'Giveaway deleted'})