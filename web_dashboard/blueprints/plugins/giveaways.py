import logging
import discord
from quart import Blueprint, request, flash, jsonify, render_template, redirect, url_for

from modules import bot as v
from modules.models import Guild, Giveaway, EmbedFieldConfig
from ...utils import bearer_client, plugin_guard, is_premium, plugin_item_cap
from ...plugins import PLUGIN_LIST

giveaways_bp = Blueprint('giveaways', __name__)
logger = logging.getLogger(__name__)

# The dashboard form posts legacy dotted field names that don't match the
# Giveaway document's own attribute names (e.g. "time.epoch" -> end_epoch,
# "winners" -> winner_count) - one mapping used by both create and edit,
# instead of each route repeating its own copy of the same translation.
_GIVEAWAY_FIELD_MAP = {
    'name': ('name', str),
    'channel_id': ('channel_id', lambda v: str(v) if v else None),
    'prize': ('prize', str),
    'winners': ('winner_count', lambda v: int(v or 1)),
    'embed.title': ('embed_title', lambda v: v or ''),
    'embed.desc': ('embed_desc', lambda v: v or ''),
    # The color picker's JS already sends an int (parseInt(hex, 16), same as
    # ticketing_form.html) - only re-parse here if a hex string shows up instead.
    'embed.color': ('embed_color', lambda v: int(str(v).lstrip('#'), 16) if isinstance(v, str) else (v or 0x5865f2)),
    'embed.fields': ('embed_fields', lambda v: [EmbedFieldConfig(**f) for f in (v or [])]),
    'time.epoch': ('end_epoch', lambda v: float(v or 0)),
    'time.timestamp': ('end_timestamp', lambda v: v or ''),
    'give_xp.enabled': ('give_xp.enabled', bool),
    'give_xp.amount': ('give_xp.amount', lambda v: int(v or 0)),
    'give_coins.enabled': ('give_coins.enabled', bool),
    'give_coins.amount': ('give_coins.amount', lambda v: int(v or 0)),
}

def _translate_giveaway_fields(data: dict) -> dict:
    """Translate a dashboard payload's legacy dotted keys into real Giveaway
    fields (including the nested give_xp.*/give_coins.* dict keys), applying
    each field's type coercion. Unknown keys are ignored."""
    result = {}
    for key, value in data.items():
        mapping = _GIVEAWAY_FIELD_MAP.get(key)
        if mapping is None:
            continue
        field, coerce = mapping
        result[field] = coerce(value)
    return result

def _apply_giveaway_fields(giveaway: Giveaway, data: dict):
    """Apply a dashboard edit payload (legacy dotted keys) onto a Giveaway document."""
    for field, value in _translate_giveaway_fields(data).items():
        if '.' in field:
            parent, child = field.split('.', 1)
            getattr(giveaway, parent)[child] = value
        else:
            setattr(giveaway, field, value)


def _build_giveaway_embed(giveaway):
    """Build the live giveaway embed for a Giveaway document."""
    embed = discord.Embed(
        title=giveaway.embed_title or f"🎉 {giveaway.prize} 🎉",
        description=giveaway.embed_desc,
        color=discord.Color(giveaway.embed_color)
    )
    embed.add_field(
        name="Ends",
        value=f"<t:{int(giveaway.end_epoch)}:R> (<t:{int(giveaway.end_epoch)}:f>)",
        inline=False
    )
    embed.add_field(name="Hosted by", value=f"<@{giveaway.author_id}>", inline=False)
    embed.add_field(name="Winners", value=f"**{giveaway.winner_count}**", inline=False)
    embed.add_field(name="Participants", value=f"**{len(giveaway.participants)}**", inline=False)

    # User-added fields (dashboard "Message" editor) come after the computed
    # ones above so the core giveaway info always reads first.
    for field in giveaway.embed_fields:
        if field.name or field.value:
            embed.add_field(name=field.name or '​', value=field.value or '​', inline=field.inline)

    # Mirrors GiveawayCog._build_giveaway_embed (cogs/system/I giveaway [beta].py) -
    # without this, a giveaway published from the dashboard never shows
    # participants what they're winning, even though coins/XP are configured
    # and will actually be awarded when it ends.
    rewards = []
    if giveaway.give_coins.get('enabled'):
        rewards.append(f"💰 {giveaway.give_coins['amount']} coins")
    if giveaway.give_xp.get('enabled'):
        rewards.append(f"⭐ {giveaway.give_xp['amount']} XP")
    if rewards:
        embed.add_field(name="🎁 Rewards", value="\n".join(rewards), inline=False)

    embed.set_footer(text=f"Giveaway ID: {giveaway.id}")
    return embed


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
    except discord.HTTPException as e:
        logger.error("Error sending giveaway message for %s: %s", giveaway.id, e)
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

    logger.debug("Loaded %d giveaways for guild %s", len(giveaways_list), guild_id)
    
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

        # Enforce the free / premium giveaway cap - the dashboard list page only
        # disables the "New giveaway" button client-side, which a direct request
        # here bypasses entirely.
        existing_count = await Giveaway.find(Giveaway.guild_id == str(guild.id)).count()
        guild_premium = await is_premium(guild)
        cap = plugin_item_cap('giveaway', guild_premium)
        if existing_count >= cap:
            msg = f"You've reached your limit of {cap} giveaways."
            if not guild_premium:
                msg += f" Upgrade to premium for up to {PLUGIN_LIST.get('giveaway', {}).get('max_premium', 100)}."
            return jsonify({'status': 'error', 'message': msg, 'code': 'item_cap'}), 409

        uuid = v.uuid(length=12, strCase="upper/lower/nums")
        channel = guild.get_channel(int(data['channel_id']))
        
        if not channel:
            return jsonify({'status': 'error', 'message': 'Channel not found'}), 400

        giveaway = Giveaway(
            id=uuid,
            guild_id=str(guild.id),
            name='giveaway',
            prize='',
            status='Draft',
            channel_id=str(channel.id),
            channel_name=channel.name,
            message_id='',
            author_id=str(current_user.id),
            embed_title='',
            embed_desc='',
            embed_color=0x5865f2,
            end_epoch=0.0,
            end_timestamp='',
            winner_count=1,
            participants=[],
            winners=[],
            give_xp={'enabled': False, 'amount': 0},
            give_coins={'enabled': False, 'amount': 0},
        )
        _apply_giveaway_fields(giveaway, data)

        if data.get('button') == 'publish':
            if not giveaway.end_epoch or giveaway.end_epoch <= 0:
                return jsonify({'status': 'error', 'message': 'Set an end time before publishing'}), 400

            ok, error = await _send_giveaway_message(guild, giveaway)
            if not ok:
                return jsonify({'status': 'error', 'message': error}), 400

            await giveaway.insert()
            await flash('Giveaway published successfully!', 'success')
            return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})

        # Default: save as draft
        await giveaway.insert()
        await flash('Giveaway saved successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Giveaway saved successfully!'})

    return await render_template(
        "dashboard/plugins/giveaways/gway_form.html",
        user=current_user,
        guild=guild,
        data={
            'name': 'New Giveaway',
            'channel_id': None,
            'prize': '',
            'winner_count': None,
            'end_epoch': 0,
            'embed_desc': '',
            'embed_color': 0x5865f2,
            'embed_fields': [],
            'give_xp': {'enabled': False, 'amount': 0},
            'give_coins': {'enabled': False, 'amount': 0},
            'status': 'Draft',
        },
        is_edit=False,
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

        _apply_giveaway_fields(giveaway, data)

        # Update the Discord message if it exists
        if giveaway.message_id and giveaway.channel_id:
            channel = guild.get_channel(int(giveaway.channel_id))
            if channel is None:
                return jsonify({'status': 'error', 'message': 'Giveaway channel was not found.'}), 400
            try:
                msg = await channel.fetch_message(int(giveaway.message_id))
                # Rebuild from scratch rather than patching fields by index - a
                # fixed index silently went stale or wrong the moment the
                # optional Rewards field was involved (added/removed/updated),
                # since its presence depends on give_coins/give_xp being enabled.
                await msg.edit(embed=_build_giveaway_embed(giveaway))
            except discord.NotFound:
                return jsonify({'status': 'error', 'message': 'Giveaway message was not found; it may have been deleted on Discord.'}), 404
            except discord.HTTPException as e:
                logger.error("Error updating giveaway message for %s in guild %s: %s", gway_id, guild_id, e)
                return jsonify({'status': 'error', 'message': f'Failed to update the giveaway message: {e}'}), 502

        await giveaway.save()

        await flash('Giveaway updated successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Giveaway updated successfully!'})

    return await render_template(
        "dashboard/plugins/giveaways/gway_form.html",
        user=current_user,
        guild=guild,
        data=dict(giveaway),
        is_edit=True,
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
    logger.info("Published draft giveaway %s for guild %s", gway_id, guild_id)
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
    logger.info("Deleted giveaway %s for guild %s", gway_id, guild_id)
    return jsonify({'status': 'success', 'message': 'Giveaway deleted'})