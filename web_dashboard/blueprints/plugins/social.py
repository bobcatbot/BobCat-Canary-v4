import logging
from pydantic import ValidationError
from quart import Blueprint, request, flash, jsonify, render_template, redirect, url_for

from modules import bot as v
from modules import twitch
from modules.models import Guild, TwitchStreamer, TwitchSubscription, YoutubeChannel, EmbedConfig
from modules.models.social import YoutubeNotifyConfig
from ...utils import get_current_user, plugin_guard, is_premium, plugin_item_cap
from ...plugins import PLUGIN_LIST

social_bp = Blueprint('social', __name__)
logger = logging.getLogger(__name__)


# ── Shared helpers ────────────────────────────────────────────────────────
def _apply_fields(doc, data: dict, model_cls):
    """Whitelist-assign a dashboard payload onto a document, same approach as
    giveaways._apply_giveaway_fields - only real model fields are settable,
    id/guild_id are never overwritten by client data."""
    for field, value in data.items():
        if field in model_cls.model_fields and field not in ('id', 'guild_id'):
            setattr(doc, field, value)


@social_bp.errorhandler(ValidationError)
async def _bad_social_data(error):
    first = error.errors()[0]
    return jsonify({'status': 'error', 'message': f"Invalid {'.'.join(str(x) for x in first['loc'])}: {first['msg']}"}), 400


# ── Twitch ────────────────────────────────────────────────────────────────
@social_bp.route("/dashboard/<int:guild_id>/twitch/search")
@plugin_guard('twitch')
async def twitch_search(guild_id):
    """Live-search suggestions for the streamer picker (twitch_form.html)."""
    query = (request.args.get('q') or '').strip()
    if not query:
        return jsonify({'status': 'success', 'data': []})

    try:
        results = await twitch.search_channels(query)
    except Exception as e:
        logger.error("Twitch channel search failed for %r: %s", query, e)
        return jsonify({'status': 'error', 'message': 'Search failed'}), 502

    return jsonify({'status': 'success', 'data': results})


@social_bp.route("/dashboard/<int:guild_id>/twitch")
@plugin_guard('twitch')
async def twitch_index(guild_id):
    current_user = get_current_user()
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = (await Guild.get(str(guild.id))).dashboard.twitch
    streamers = await TwitchStreamer.find(TwitchStreamer.guild_id == str(guild.id)).to_list()

    return await render_template(
        "dashboard/plugins/social/twitch_index.html",
        user=current_user,
        guild=guild,
        config=config,
        data=streamers,
    )


@social_bp.route("/dashboard/<int:guild_id>/twitch/creation", methods=['GET', 'POST'])
@plugin_guard('twitch')
async def twitch_creation(guild_id):
    current_user = get_current_user()
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        login = (data.get('streamer_login') or '').strip().lstrip('@').lower()
        if not login:
            return jsonify({'status': 'error', 'message': 'Streamer login is required'}), 400
        if not data.get('channel_id'):
            return jsonify({'status': 'error', 'message': 'Notification channel is required'}), 400

        existing_count = await TwitchStreamer.find(TwitchStreamer.guild_id == str(guild.id)).count()
        guild_premium = await is_premium(guild)
        cap = plugin_item_cap('twitch', guild_premium)
        if existing_count >= cap:
            msg = f"You've reached your limit of {cap} streamers."
            if not guild_premium:
                msg += f" Upgrade to premium for up to {PLUGIN_LIST.get('twitch', {}).get('max_premium', 10)}."
            return jsonify({'status': 'error', 'message': msg, 'code': 'item_cap'}), 409

        if await TwitchStreamer.find_one(
            TwitchStreamer.guild_id == str(guild.id),
            TwitchStreamer.streamer_login == login,
        ):
            return jsonify({'status': 'error', 'message': f'{login} is already being watched in this server'}), 409

        channel = guild.get_channel(int(data['channel_id']))
        if not channel:
            return jsonify({'status': 'error', 'message': 'Channel not found'}), 400

        user = await twitch.get_user(login)
        if not user:
            return jsonify({'status': 'error', 'message': f'No Twitch user found for "{login}"'}), 400
        broadcaster_id = user['id']

        subscription = await TwitchSubscription.get(broadcaster_id)
        if subscription is None:
            try:
                eventsub_ids = await twitch.create_eventsub_subscription(broadcaster_id)
            except Exception as e:
                logger.error("Failed to create EventSub subscription for %s: %s", login, e)
                return jsonify({'status': 'error', 'message': 'Failed to subscribe to Twitch notifications for this streamer'}), 502
            subscription = TwitchSubscription(id=broadcaster_id, eventsub_ids=eventsub_ids)
            await subscription.insert()

        uuid = v.uuid(length=12, strCase="upper/lower/nums")
        streamer = TwitchStreamer(
            id=uuid,
            guild_id=str(guild.id),
            streamer_login=login,
            streamer_user_id=broadcaster_id,
            streamer_display_name=user.get('display_name', login),
            avatar_url=user.get('profile_image_url'),
            channel_id=str(channel.id),
        )
        _apply_fields(streamer, data, TwitchStreamer)
        await streamer.insert()

        await flash('Streamer added successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Streamer added successfully!'})

    return await render_template(
        "dashboard/plugins/social/twitch_form.html",
        user=current_user,
        guild=guild,
        data={
            'streamer_login': '',
            'channel_id': None,
            'mention_role_id': None,
            'custom_message': '{streamer} is now live!',
            'watch_button': True,
        },
        is_edit=False,
    )


@social_bp.route("/dashboard/<int:guild_id>/twitch/<streamer_id>/edition", methods=['GET', 'POST'])
@plugin_guard('twitch')
async def twitch_edition(guild_id, streamer_id):
    current_user = get_current_user()
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    streamer = await TwitchStreamer.find_one(
        TwitchStreamer.guild_id == str(guild.id),
        TwitchStreamer.id == streamer_id,
    )
    if streamer is None:
        await flash('Streamer not found', 'error')
        return redirect(url_for('social.twitch_index', guild_id=guild_id))

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        _apply_fields(streamer, data, TwitchStreamer)
        await streamer.save()

        await flash('Streamer updated successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Streamer updated successfully!'})

    return await render_template(
        "dashboard/plugins/social/twitch_form.html",
        user=current_user,
        guild=guild,
        data=dict(streamer),
        is_edit=True,
    )


@social_bp.route("/dashboard/<int:guild_id>/twitch/<streamer_id>/delete", methods=['DELETE'])
@plugin_guard('twitch')
async def twitch_delete(guild_id, streamer_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    streamer = await TwitchStreamer.find_one(
        TwitchStreamer.guild_id == str(guild.id),
        TwitchStreamer.id == streamer_id,
    )
    if streamer is None:
        return jsonify({'status': 'error', 'message': 'Streamer not found'}), 404

    broadcaster_id = streamer.streamer_user_id
    await streamer.delete()

    # If no guild watches this broadcaster anymore, drop the EventSub subscription too.
    remaining = await TwitchStreamer.find(TwitchStreamer.streamer_user_id == broadcaster_id).count()
    if remaining == 0:
        subscription = await TwitchSubscription.get(broadcaster_id)
        if subscription:
            for eventsub_id in subscription.eventsub_ids:
                try:
                    await twitch.delete_eventsub_subscription(eventsub_id)
                except Exception as e:
                    logger.warning("Failed to delete EventSub subscription %s: %s", eventsub_id, e)
            await subscription.delete()

    logger.info("Deleted Twitch streamer %s for guild %s", streamer_id, guild_id)
    return jsonify({'status': 'success', 'message': 'Streamer removed'})


# ── YouTube ───────────────────────────────────────────────────────────────
@social_bp.route("/dashboard/<int:guild_id>/youtube")
@plugin_guard('youtube')
async def youtube_index(guild_id):
    current_user = get_current_user()
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = (await Guild.get(str(guild.id))).dashboard.youtube
    channels = await YoutubeChannel.find(YoutubeChannel.guild_id == str(guild.id)).to_list()

    return await render_template(
        "dashboard/plugins/social/youtube_index.html",
        user=current_user,
        guild=guild,
        config=config,
        data=channels,
    )


@social_bp.route("/dashboard/<int:guild_id>/youtube/creation", methods=['GET', 'POST'])
@plugin_guard('youtube')
async def youtube_creation(guild_id):
    current_user = get_current_user()
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        identifier = (data.get('channel_identifier') or '').strip()
        if not identifier:
            return jsonify({'status': 'error', 'message': 'A channel handle or URL is required'}), 400

        existing_count = await YoutubeChannel.find(YoutubeChannel.guild_id == str(guild.id)).count()
        guild_premium = await is_premium(guild)
        cap = plugin_item_cap('youtube', guild_premium)
        if existing_count >= cap:
            msg = f"You've reached your limit of {cap} channels."
            if not guild_premium:
                msg += f" Upgrade to premium for up to {PLUGIN_LIST.get('youtube', {}).get('max_premium', 10)}."
            return jsonify({'status': 'error', 'message': msg, 'code': 'item_cap'}), 409

        uuid = v.uuid(length=12, strCase="upper/lower/nums")
        channel = YoutubeChannel(
            id=uuid,
            guild_id=str(guild.id),
            channel_identifier=identifier,
            video=YoutubeNotifyConfig(embed=EmbedConfig(color=0xFF0000)),
            live=YoutubeNotifyConfig(embed=EmbedConfig(color=0xFF0000)),
        )
        _apply_fields(channel, data, YoutubeChannel)
        await channel.insert()

        await flash('Channel added successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Channel added successfully!'})

    return await render_template(
        "dashboard/plugins/social/youtube_form.html",
        user=current_user,
        guild=guild,
        data={
            'channel_identifier': '',
            'video': YoutubeNotifyConfig(embed=EmbedConfig(color=0xFF0000)),
            'live': YoutubeNotifyConfig(embed=EmbedConfig(color=0xFF0000)),
        },
        is_edit=False,
    )


@social_bp.route("/dashboard/<int:guild_id>/youtube/<channel_id>/edition", methods=['GET', 'POST'])
@plugin_guard('youtube')
async def youtube_edition(guild_id, channel_id):
    current_user = get_current_user()
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    channel = await YoutubeChannel.find_one(
        YoutubeChannel.guild_id == str(guild.id),
        YoutubeChannel.id == channel_id,
    )
    if channel is None:
        await flash('Channel not found', 'error')
        return redirect(url_for('social.youtube_index', guild_id=guild_id))

    if request.method == 'POST':
        data = await request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400

        _apply_fields(channel, data, YoutubeChannel)
        await channel.save()

        await flash('Channel updated successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Channel updated successfully!'})

    return await render_template(
        "dashboard/plugins/social/youtube_form.html",
        user=current_user,
        guild=guild,
        data=dict(channel),
        is_edit=True,
    )


@social_bp.route("/dashboard/<int:guild_id>/youtube/<channel_id>/delete", methods=['DELETE'])
@plugin_guard('youtube')
async def youtube_delete(guild_id, channel_id):
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    channel = await YoutubeChannel.find_one(
        YoutubeChannel.guild_id == str(guild.id),
        YoutubeChannel.id == channel_id,
    )
    if channel is None:
        return jsonify({'status': 'error', 'message': 'Channel not found'}), 404

    await channel.delete()
    logger.info("Deleted YouTube channel %s for guild %s", channel_id, guild_id)
    return jsonify({'status': 'success', 'message': 'Channel removed'})
