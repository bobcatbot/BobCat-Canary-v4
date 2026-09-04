import discord
import asyncio
import logging
from bson import ObjectId
from bson.errors import InvalidId
from quart import Blueprint, render_template, redirect, url_for, flash, jsonify, request

from modules import bot as v
from modules.models import Guild, Ticket
from ...utils import bearer_client, login_required, plugin_guard, is_premium, plugin_item_cap, unflatten_keys, deep_merge
from ...plugins import PLUGIN_LIST

ticketing_bp = Blueprint('ticketing', __name__)
logger = logging.getLogger(__name__)

def _parse_embed_color(value, default=0x5865f2) -> int:
    """Coerce a panel embed color (int, hex string, or missing) to an int."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value.strip().lstrip('#'), 16)
    return default

# ── Public transcript pages ──────────────────────────────────────────────
@ticketing_bp.route("/t/<int:guild_id>/<ticket_id>")
@login_required
async def ticketing_transcript(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return redirect(url_for('web.index'))

    # Use Beanie to get the ticket
    ticket = await Ticket.find_one(
        Ticket.guild_id == str(guild.id),
        Ticket.id == ticket_id
    )
    if ticket is None:
        # Older ticket docs were stored with a BSON ObjectId `_id`; the
        # string-typed query above can't match those, so fall back to a
        # raw ObjectId lookup.
        try:
            oid = ObjectId(ticket_id)
        except InvalidId:
            oid = None
        if oid is not None:
            ticket = await Ticket.find_one(
                Ticket.guild_id == str(guild.id),
                {"_id": oid}
            )

    if ticket is None:
        await flash('Ticket not found', 'error')
        return redirect(url_for('web.index'))

    closed_by_user = None
    if ticket.closed and ticket.closed.get('user'):
        closed_by_user = v.client.get_user(int(ticket.closed['user']))

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_transcript.html",
        guild=guild,
        data=ticket,
        closed_by=closed_by_user,
    )


# ── Dashboard management ────────────────────────────────────────────────
@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing")
@plugin_guard('ticketing')
async def ticketing(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.ticketing

    guild_premium = await is_premium(guild)

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_index.html",
        user=current_user,
        guild=guild,
        data=config,
        is_premium=guild_premium,
        item_cap=plugin_item_cap('ticketing', guild_premium),
        item_cap_premium=PLUGIN_LIST.get('ticketing', {}).get('max_premium', 15),
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/creation", methods=['GET', 'POST'])
@plugin_guard('ticketing')
async def ticketing_create(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == "POST":
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # The form posts dotted paths (panel_button.emoji, intro_message.embed.title);
        # the bot and edit template read the nested shape.
        data = unflatten_keys(data)

        # Validate required fields
        if not data.get('channel_id'):
            return jsonify({'status': 'error', 'message': 'Channel ID is required'}), 400

        # Enforce the free / premium panel cap
        existing = (await Guild.get(str(guild.id))).dashboard.ticketing.get('panels', [])
        guild_premium = await is_premium(guild)
        cap = plugin_item_cap('ticketing', guild_premium)
        if len(existing) >= cap:
            msg = f"You've reached your limit of {cap} ticket panels."
            if not guild_premium:
                msg += f" Upgrade to premium for up to {PLUGIN_LIST.get('ticketing', {}).get('max_premium', 15)}."
            return jsonify({'status': 'error', 'message': msg, 'code': 'item_cap'}), 409

        data['id'] = v.uuid(12, strCase="upper/lower/nums")

        async def create_panel():
            try:
                # Get the guild document
                config = await Guild.get(str(guild.id))
                if config is None:
                    logger.error(f"Guild config not found for {guild_id}")
                    return

                # Ensure ticketing exists
                if not hasattr(config.dashboard, 'ticketing'):
                    config.dashboard.ticketing = {}
                
                panels = config.dashboard.ticketing.get('panels', [])

                # Create the Discord message
                pm_embed = data.get('panel_message', {}).get('embed', {})
                embed = discord.Embed(
                    title=pm_embed.get('title', 'Support Tickets'),
                    description=pm_embed.get('description', 'Click below to create a ticket.'),
                    color=_parse_embed_color(pm_embed.get('color'))
                )
                
                btn = data.get('panel_button', {})
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    emoji=btn.get('emoji') or None,
                    label=btn.get('label') or 'Create Ticket',
                    style=getattr(discord.ButtonStyle, btn.get('style') or 'blurple', discord.ButtonStyle.blurple),
                    custom_id='create_ticket'
                ))
                
                channel = guild.get_channel(int(data.get('channel_id')))
                if channel:
                    msg = await channel.send(embed=embed, view=view)
                    data['panel_message_id'] = str(msg.id)
                    logger.info(f"Created ticket panel message for guild {guild_id}")
                else:
                    logger.error(f"Channel {data.get('channel_id')} not found for guild {guild_id}")
                    return

                # Save to dashboard
                panels.append(data)
                config.dashboard.ticketing['panels'] = panels
                config.updated_at = discord.utils.utcnow()
                await config.save()
                logger.info(f"Saved ticket panel {data['id']} for guild {guild_id}")
            
            except Exception as e:
                logger.error(f"Error creating ticket panel for guild {guild_id}: {e}", exc_info=True)

        # Fire and forget
        asyncio.create_task(create_panel())
        
        await flash(f"Successfully created ticket panel {data['id']}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully created ticket'})

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_create.html",
        user=current_user,
        guild=guild
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/edition", methods=['GET', 'POST'])
@plugin_guard('ticketing')
async def ticketing_edit(guild_id, ticket_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document
    config = await Guild.get(str(guild.id))
    if config is None:
        await flash('Guild config not found', 'error')
        return redirect(url_for('ticketing.ticketing', guild_id=guild_id))

    panels = config.dashboard.ticketing.get('panels', [])
    tk_data = next((t for t in panels if t.get('id') == ticket_id), None)
    
    if tk_data is None:
        await flash('Ticket panel not found', 'error')
        return redirect(url_for('ticketing.ticketing', guild_id=guild_id))

    ticket_idx = panels.index(tk_data)

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        # Expand dotted paths (intro_message.embed.title) to the nested shape.
        data = unflatten_keys(data)

        async def edit_panel():
            try:
                # Get fresh config
                config = await Guild.get(str(guild.id))
                if config is None:
                    return

                panels = config.dashboard.ticketing.get('panels', [])

                # Merge the update in first so a partial edit (e.g. just the
                # intro embed title) doesn't clobber sibling keys, then render
                # the live panel message from the merged result.
                panel = deep_merge(panels[ticket_idx], data)

                panel_msg_id = panel.get('panel_message_id')
                channel_id = panel.get('channel_id')

                if panel_msg_id and channel_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        try:
                            msg = await channel.fetch_message(int(panel_msg_id))

                            pm_embed = panel.get('panel_message', {}).get('embed', {})                            
                            embed = discord.Embed(
                                title=pm_embed.get('title', 'Support Tickets'),
                                description=pm_embed.get('description', 'Click below to create a ticket.'),
                                color=_parse_embed_color(pm_embed.get('color'))
                            )
                            
                            btn = panel.get('panel_button', {})
                            view = discord.ui.View()
                            view.add_item(discord.ui.Button(
                                emoji=btn.get('emoji') or None,
                                label=btn.get('label') or 'Create Ticket',
                                style=getattr(discord.ButtonStyle, btn.get('style') or 'blurple', discord.ButtonStyle.blurple),
                                custom_id='create_ticket'
                            ))
                            
                            await msg.edit(embed=embed, view=view)
                            logger.info(f"Updated ticket panel message for guild {guild_id}")
                        except discord.NotFound:
                            logger.warning(f"Ticket panel message not found for guild {guild_id}")
                        except Exception as e:
                            logger.error(f"Error updating ticket panel message: {e}")

                config.dashboard.ticketing['panels'] = panels
                config.updated_at = discord.utils.utcnow()
                await config.save()
                logger.info(f"Updated ticket panel {ticket_id} for guild {guild_id}")
            
            except Exception as e:
                logger.error(f"Error editing ticket panel for guild {guild_id}: {e}", exc_info=True)

        # Fire and forget
        asyncio.create_task(edit_panel())
        
        await flash(f"Successfully updated ticket panel {ticket_id}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully updated ticket'})

    return await render_template(
        "dashboard/plugins/ticketing/ticketing_edit.html",
        user=current_user,
        guild=guild,
        data=tk_data
    )


@ticketing_bp.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/delete", methods=['DELETE'])
@plugin_guard('ticketing')
async def ticketing_delete(guild_id, ticket_id):
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    panels = config.dashboard.ticketing.get('panels', [])
    data = next((t for t in panels if t.get('id') == ticket_id), None)
    
    if data is None:
        return jsonify({'status': 'error', 'message': 'Ticket panel not found'}), 404

    async def delete_panel():
        try:
            # Get fresh config
            config = await Guild.get(str(guild.id))
            if config is None:
                return

            panels = config.dashboard.ticketing.get('panels', [])
            data = next((t for t in panels if t.get('id') == ticket_id), None)
            
            if data is None:
                return

            # Delete the Discord message
            panel_msg_id = data.get('panel_message_id')
            channel_id = data.get('channel_id')
            
            if panel_msg_id and channel_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        msg = await channel.fetch_message(int(panel_msg_id))
                        await msg.delete()
                        logger.info(f"Deleted ticket panel message for guild {guild_id}")
                    except discord.NotFound:
                        logger.warning(f"Ticket panel message not found for guild {guild_id}")
                    except Exception as e:
                        logger.error(f"Error deleting ticket panel message: {e}")

            # Remove from config
            ticket_idx = panels.index(data)
            panels.pop(ticket_idx)
            config.dashboard.ticketing['panels'] = panels
            config.updated_at = discord.utils.utcnow()
            await config.save()
            logger.info(f"Deleted ticket panel {ticket_id} for guild {guild_id}")
        
        except Exception as e:
            logger.error(f"Error deleting ticket panel for guild {guild_id}: {e}", exc_info=True)

    # Fire and forget
    asyncio.create_task(delete_panel())
    
    await flash(f"Successfully deleted ticket panel {ticket_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted ticket panel'})