import discord
import asyncio
import logging
from quart import Blueprint, request, flash, jsonify, render_template, redirect, url_for

from modules import bot as v
from modules.models import Guild, Giveaway
from ...utils import bearer_client, login_required, premium_module

giveaways_bp = Blueprint('giveaways', __name__)
logger = logging.getLogger(__name__)


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways")
@login_required
async def giveaways(guild_id):
    premium_module(guild_id, 'giveaway')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the giveaway config from dashboard
    config = Guild.get(str(guild.id)).run().dashboard.giveaways
    
    # Get all giveaways for this guild
    giveaways_list = Giveaway.find(Giveaway.guild_id == str(guild.id)).run()

    logger.info(f"Loaded {len(giveaways_list)} giveaways for guild {guild_id}")
    
    return await render_template(
        "dashboard/plugins/giveaways/gway_index.html",
        user=current_user,
        guild=guild,
        config=config,
        data=giveaways_list
    )


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/creation", methods=['GET', 'POST'])
@login_required
async def giveaways_creation(guild_id):
    premium_module(guild_id, 'giveaway')
    
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
            'status': 'Ongoing' if data.get('button') == 'publish' else 'Draft',
            'channel_id': str(channel.id),
            'channel_name': channel.name,
            'message_id': '',
            'author_id': str(current_user.id),
            'embed_title': data.get('embed_title', ''),
            'embed_desc': data.get('embed_desc', ''),
            'end_epoch': float(data.get('time.epoch', 0)),
            'end_timestamp': data.get('time.timestamp', ''),
            'winner_count': int(data.get('winners', 1)),
            'participants': [],
            'winners': [],
            'give_xp': {
                'enabled': data.get('givexp.enabled', False),
                'amount': int(data.get('givexp.amount', 0))
            },
            'give_coins': {
                'enabled': data.get('givecoins.enabled', False),
                'amount': int(data.get('givecoins.amount', 0))
            }
        }

        if data.get('button') == 'save':
            # Save as draft
            giveaway = Giveaway(**giveaway_data)
            giveaway.insert()
            await flash('Giveaway saved successfully!', 'success')
            logger.info(f"Saved giveaway draft {uuid} for guild {guild_id}")
            return jsonify({'status': 'success', 'message': 'Giveaway saved successfully!'})

        if data.get('button') == 'publish':
            async def create_giveaway():
                try:
                    view = discord.ui.View(timeout=None)
                    view.add_item(discord.ui.Button(
                        emoji="🎉",
                        style=discord.ButtonStyle.blurple,
                        custom_id="JoinGiveaway"
                    ))
                    
                    embed = discord.Embed(
                        title=giveaway_data['embed_title'] or f"🎉 {giveaway_data['prize']} 🎉",
                        description=giveaway_data['embed_desc'],
                        color=discord.Color.embed_background()
                    )
                    embed.add_field(
                        name="Ends",
                        value=f"<t:{int(giveaway_data['end_epoch'])}:R> (<t:{int(giveaway_data['end_epoch'])}:f>)",
                        inline=False
                    )
                    embed.add_field(
                        name="Hosted by",
                        value=f"<@{current_user.id}>",
                        inline=False
                    )
                    embed.add_field(
                        name="Winners",
                        value=f"**{giveaway_data['winner_count']}**",
                        inline=False
                    )
                    embed.add_field(
                        name="Participants",
                        value="**0**",
                        inline=False
                    )
                    embed.set_footer(text="Click the button below to participate!")
                    
                    msg = await channel.send(embed=embed, view=view)
                    giveaway_data['message_id'] = str(msg.id)
                    
                    # Save the giveaway with message_id
                    giveaway = Giveaway(**giveaway_data)
                    giveaway.insert()
                    logger.info(f"Published giveaway {uuid} for guild {guild_id}")
                except discord.Forbidden:
                    logger.error(f"No permissions to send message in channel for guild {guild_id}")
                except Exception as e:
                    logger.error(f"Error creating giveaway for guild {guild_id}: {e}", exc_info=True)

            # Fire and forget
            asyncio.create_task(create_giveaway())
            
            await flash('Giveaway published successfully!', 'success')
            return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})

    return await render_template(
        "dashboard/plugins/giveaways/gway_create.html",
        user=current_user,
        guild=guild
    )


@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/edition", methods=['GET', 'POST'])
@login_required
async def giveaways_edition(guild_id, gway_id):
    premium_module(guild_id, 'giveaway')
    
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the giveaway using Bunnet
    giveaway = Giveaway.find_one(
        Giveaway.guild_id == str(guild.id),
        Giveaway.id == gway_id
    ).run()
    
    if giveaway is None:
        await flash('Giveaway not found', 'error')
        return redirect(url_for('giveaways.giveaways', guild_id=guild_id))

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        async def update_giveaway():
            try:
                # Update the giveaway
                for key, value in data.items():
                    if key == 'time.epoch':
                        giveaway.end_epoch = float(value)
                    elif key == 'time.timestamp':
                        giveaway.end_timestamp = value
                    elif key == 'prize':
                        giveaway.prize = value
                    elif key == 'winners':
                        giveaway.winner_count = int(value)
                    elif key == 'embed.desc':
                        giveaway.embed_desc = value
                    elif key == 'give_xp.enabled':
                        giveaway.give_xp['enabled'] = bool(value)
                    elif key == 'give_xp.amount':
                        giveaway.give_xp['amount'] = int(value)
                    elif key == 'give_coins.enabled':
                        giveaway.give_coins['enabled'] = bool(value)
                    elif key == 'give_coins.amount':
                        giveaway.give_coins['amount'] = int(value)

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

                giveaway.save()
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