import asyncio
import hmac
import hashlib
import logging
import discord
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from quart import Blueprint, current_app, jsonify, request, Response

from modules import bot as v
from modules import twitch
from modules import youtube
from modules.models import TwitchStreamer as TwitchStreamers, TwitchSubscription, TwitchEvent
from modules.models import YoutubeChannel, YoutubeSubscription, YoutubeVideoState

TWITCH_PURPLE = 0x9146FF
YOUTUBE_RED = 0xFF0000

# Twitch's live preview thumbnail isn't generated the instant a stream starts -
# fetching stream details (and posting) right on stream.online gets a generic
# "404 preview" placeholder image instead of a real one. Wait this long before
# doing either, so the thumbnail's actually ready. Counted from when the event
# reaches us, which is ~15-19s after the stream actually starts; the preview has
# been seen ready anywhere from ~38s to ~63s after the stream starts.
STREAM_ONLINE_DELAY_SECONDS = 45

social_webhooks_bp = Blueprint('social_webhooks', __name__)
logger = logging.getLogger(__name__)

MESSAGE_TYPE_HEADER = "Twitch-Eventsub-Message-Type"
MESSAGE_ID_HEADER = "Twitch-Eventsub-Message-Id"
MESSAGE_TIMESTAMP_HEADER = "Twitch-Eventsub-Message-Timestamp"
MESSAGE_SIGNATURE_HEADER = "Twitch-Eventsub-Message-Signature"

# ── Idempotency ───────────────────────────────────────────────────────────
async def _claim_event(message_id: str) -> bool:
    try:
        await TwitchEvent(id=message_id).insert()
    except DuplicateKeyError:
        return False
    return True

# ── Signature verification ───────────────────────────────────────────────
def _verify_signature(secret: str, message_id: str, timestamp: str, body: bytes, signature: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode(),
        (message_id + timestamp).encode() + body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

# ── Notification handling ────────────────────────────────────────────────
async def _build_notification_embed(streamer: TwitchStreamers, stream: dict | None, channel_url: str) -> discord.Embed | None:
    """Pre-built stream-info card - not user-customizable, just assembled fresh
    from Twitch's data each time (title/game/preview thumbnail), same shape as
    every other Twitch notification bot's live card. embed_image_mode controls
    whether there's an embed at all, and if so what image(s) it carries."""
    mode = streamer.embed_image_mode
    if mode == "none":
        return None

    title = stream.get("title") if stream else None
    game = stream.get("game_name") if stream else None
    game_id = stream.get("game_id") if stream else None
    viewer_count = stream.get("viewer_count") if stream else None
    thumbnail_template = stream.get("thumbnail_url") if stream else None

    embed = discord.Embed(color=TWITCH_PURPLE, timestamp=datetime.now(timezone.utc))
    embed.set_author(
        name=f"{streamer.streamer_display_name} is now live on Twitch!",
        icon_url=streamer.avatar_url,
        url=channel_url,
    )
    if title:
        embed.description = f"[{title}]({channel_url})"
    if game:
        embed.add_field(name="Game", value=game, inline=True)
    if streamer.show_viewers and viewer_count is not None:
        embed.add_field(name="Viewers", value=str(viewer_count), inline=True)

    if mode != "minimal" and thumbnail_template:
        # The image URL is one fixed URL per streamer for every stream they ever
        # do, and Discord caches embed images by URL - so a per-stream query
        # string forces a fresh fetch (Twitch's CDN ignores it) instead of
        # reusing an older stream's picture or a placeholder.
        preview_url = f"{thumbnail_template.format(width=440, height=248)}?stream={stream.get('id')}"
        embed.set_image(url=preview_url)

    if mode == "preview_boxart" and game_id:
        try:
            game_data = await twitch.get_game(game_id)
        except Exception as e:
            logger.warning("Failed to fetch box art for game %s: %s", game_id, e)
            game_data = None
        if game_data and game_data.get("box_art_url"):
            embed.set_thumbnail(url=game_data["box_art_url"].format(width=144, height=192))
    return embed

async def _build_offline_embed(streamer: TwitchStreamers, channel_url: str) -> discord.Embed | None:
    """Pre-built "was live" card, shown by editing the original live message
    once stream.offline fires. Get Streams only works while live, so this
    needs two different follow-up calls: Get Channel Information (works
    regardless of live status) for the game, and Get Videos for the archived
    VOD's title/duration/link."""
    if streamer.embed_image_mode == "none":
        return None

    try:
        channel_info = await twitch.get_channel_info(streamer.streamer_user_id)
    except Exception as e:
        logger.warning("Failed to fetch channel info for %s: %s", streamer.streamer_user_id, e)
        channel_info = None
    try:
        vod = await twitch.get_latest_vod(streamer.streamer_user_id)
    except Exception as e:
        logger.warning("Failed to fetch latest VOD for %s: %s", streamer.streamer_user_id, e)
        vod = None

    game = channel_info.get("game_name") if channel_info else None
    title = (vod.get("title") if vod else None) or (channel_info.get("title") if channel_info else None)

    embed = discord.Embed(color=discord.Color.dark_grey().value, timestamp=datetime.now(timezone.utc))
    embed.set_author(
        name=f"{streamer.streamer_display_name} was live on Twitch",
        icon_url=streamer.avatar_url,
        url=channel_url,
    )
    if title:
        embed.description = title
    if game:
        embed.add_field(name="Game", value=game, inline=True)
    if vod and vod.get("url"):
        embed.add_field(name="VOD", value=f"{vod.get('duration', '')}, [Click to view]({vod['url']})", inline=True)
    embed.set_footer(text="Offline")
    return embed

async def _handle_stream_online(event: dict):
    await asyncio.sleep(STREAM_ONLINE_DELAY_SECONDS)

    broadcaster_id = event["broadcaster_user_id"]
    streamers = await TwitchStreamers.find(TwitchStreamers.streamer_user_id == broadcaster_id).to_list()
    if not streamers:
        return

    try:
        stream = await twitch.get_stream(broadcaster_id)
        lookup_ok = True
    except Exception as e:
        logger.warning("Failed to fetch live stream details for %s: %s", broadcaster_id, e)
        stream = None
        lookup_ok = False

    # The stream this event announced may have ended (or been replaced by a
    # newer one) during the sleep above - the offline event for it was skipped
    # since nothing was marked live yet, so posting now would announce a stream
    # that's already over. A stream's id in Get Streams matches the event's id.
    if lookup_ok and event.get("type") == "live" and (stream is None or stream.get("id") != event.get("id")):
        return

    for streamer in streamers:
        client = v.get_client(int(streamer.guild_id))
        guild = client.get_guild(int(streamer.guild_id)) if client else None
        if guild is None:
            continue
        channel = guild.get_channel(int(streamer.channel_id))
        if channel is None:
            continue

        channel_url = f"https://twitch.tv/{streamer.streamer_login}"
        content = (streamer.custom_message or "{streamer} is now live!").format(
            streamer=streamer.streamer_display_name,
            title=stream.get("title", "") if stream else "",
            game=stream.get("game_name", "") if stream else "",
            url=channel_url,
        )
        if streamer.mention_role_id:
            content = f"<@&{streamer.mention_role_id}> {content}"

        view = discord.ui.View(timeout=None)

        if streamer.watch_button:
            view.add_item(discord.ui.Button(label="Watch Stream", style=discord.ButtonStyle.link, url=channel_url))

        try:
            msg = await channel.send(
                content=content,
                embed=await _build_notification_embed(streamer, stream, channel_url),
                view=view,
            )
        except discord.HTTPException as e:
            logger.error("Failed to send Twitch notification for %s in guild %s: %s", streamer.streamer_login, streamer.guild_id, e)
            continue

        streamer.is_live = True
        streamer.current_stream_id = event.get("id")
        streamer.notification_message_id = str(msg.id)
        await streamer.save()

async def _handle_stream_offline(event: dict):
    broadcaster_id = event["broadcaster_user_id"]
    streamers = await TwitchStreamers.find(TwitchStreamers.streamer_user_id == broadcaster_id).to_list()
    for streamer in streamers:
        if not streamer.is_live:
            continue

        if streamer.notification_message_id:
            client = v.get_client(int(streamer.guild_id))
            guild = client.get_guild(int(streamer.guild_id)) if client else None
            channel = guild.get_channel(int(streamer.channel_id)) if guild else None
            if channel:
                try:
                    msg = await channel.fetch_message(int(streamer.notification_message_id))
                    channel_url = f"https://twitch.tv/{streamer.streamer_login}"
                    offline_embed = await _build_offline_embed(streamer, channel_url)
                    await msg.edit(embed=offline_embed, view=None)
                except discord.NotFound:
                    logger.info("Original Twitch live message not found in guild %s, skipping edit", streamer.guild_id)
                except discord.HTTPException as e:
                    logger.error("Failed to edit ended Twitch notification in guild %s: %s", streamer.guild_id, e)

        streamer.is_live = False
        streamer.current_stream_id = None
        await streamer.save()

async def _handle_revocation(subscription: dict):
    sub_id = subscription.get("id")
    broadcaster_id = (subscription.get("condition") or {}).get("broadcaster_user_id")
    if not broadcaster_id:
        return
    record = await TwitchSubscription.get(broadcaster_id)
    if record and sub_id in record.eventsub_ids:
        record.eventsub_ids.remove(sub_id)
        if not record.eventsub_ids:
            record.status = "revoked"
        await record.save()
    logger.warning("Twitch EventSub subscription %s revoked: %s", sub_id, subscription.get("status"))

NOTIFICATION_HANDLERS = {
    "stream.online": _handle_stream_online,
    "stream.offline": _handle_stream_offline,
}

async def _run_handler(handler, sub_type: str, event: dict):
    """Runs a notification handler in the background, off the request/response
    cycle - stream.online sleeps for STREAM_ONLINE_DELAY_SECONDS first, and
    Twitch expects a 2xx ack within a few seconds or it'll treat delivery as
    failed and retry."""
    try:
        await handler(event)
    except Exception as e:
        logger.error("Failed to handle Twitch notification %s: %s", sub_type, e)


# ── YouTube: WebSub signature + feed parsing ─────────────────────────────
YOUTUBE_ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}

def _verify_websub_signature(secret: str, body: bytes, signature_header: str) -> bool:
    if not signature_header or "=" not in signature_header:
        return False
    algo, _, sig = signature_header.partition("=")
    hash_fn = {"sha1": hashlib.sha1, "sha256": hashlib.sha256}.get(algo)
    if hash_fn is None:
        return False
    expected = hmac.new(secret.encode(), body, hash_fn).hexdigest()
    return hmac.compare_digest(expected, sig)

def _parse_websub_entries(body: bytes) -> list[tuple[str, str]]:
    """Parses a WebSub Atom feed into [(video_id, channel_id), ...]. Skips
    <at:deleted-entry> entries (video removed) - nothing to notify there."""
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []

    entries = []
    for entry in root.findall("atom:entry", YOUTUBE_ATOM_NS):
        video_id = entry.findtext("yt:videoId", namespaces=YOUTUBE_ATOM_NS)
        channel_id = entry.findtext("yt:channelId", namespaces=YOUTUBE_ATOM_NS)
        if video_id and channel_id:
            entries.append((video_id, channel_id))
    return entries

# ── YouTube: notification handling ───────────────────────────────────────
def _format_duration(seconds: float) -> str:
    """"4h21m30s"-style formatting, matching Twitch's own VOD duration string
    so both platforms' ended cards read consistently."""
    hours, remainder = divmod(max(int(seconds), 0), 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if hours or minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return "".join(parts)

def _build_youtube_embed(video: dict, video_url: str, *, channel_title: str, avatar_url: str | None, kind: str) -> discord.Embed:
    """Pre-built video/stream card - not user-customizable, assembled fresh
    from YouTube's own data each time (title/thumbnail/publish-or-start time),
    same shape and same reasoning as Twitch's notification card."""
    snippet = video.get("snippet") or {}
    thumbnails = snippet.get("thumbnails") or {}
    thumbnail_url = (
        thumbnails.get("maxres") or thumbnails.get("high")
        or thumbnails.get("medium") or thumbnails.get("default") or {}
    ).get("url")
    details = video.get("liveStreamingDetails") or {}

    color = YOUTUBE_RED
    include_image = True
    vod_field = None
    if kind == "upcoming":
        author_name = f"{channel_title} has a stream scheduled on YouTube"
        footer_text = "Scheduled"
        timestamp = details.get("scheduledStartTime")
    elif kind == "live":
        author_name = f"{channel_title} is now live on YouTube!"
        footer_text = "Live"
        timestamp = details.get("actualStartTime")
    elif kind == "ended":
        author_name = f"{channel_title} was live on YouTube"
        footer_text = "Stream ended"
        timestamp = details.get("actualEndTime")
        color = discord.Color.dark_grey().value
        include_image = False
        start, end = details.get("actualStartTime"), details.get("actualEndTime")
        if start and end:
            duration = (
                datetime.fromisoformat(end.replace("Z", "+00:00"))
                - datetime.fromisoformat(start.replace("Z", "+00:00"))
            ).total_seconds()
            vod_field = f"{_format_duration(duration)}, [Click to view]({video_url})"
    else:
        author_name = f"{channel_title} published a new video on YouTube"
        footer_text = "Published"
        timestamp = snippet.get("publishedAt")

    embed = discord.Embed(color=color, title=snippet.get("title") or "Untitled", url=video_url)
    embed.set_author(name=author_name, icon_url=avatar_url, url=video_url)
    if include_image and thumbnail_url:
        embed.set_image(url=thumbnail_url)
    if vod_field:
        embed.add_field(name="VOD", value=vod_field, inline=True)
    if timestamp:
        embed.timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    embed.set_footer(text=footer_text)
    return embed

async def _send_youtube_notification(guild_id: str, notify, video: dict, video_url: str, *, channel_title: str, avatar_url: str | None, kind: str) -> str | None:
    """Sends one video.*/live.* notification to its guild-configured channel.
    Returns the sent message's id, or None if it wasn't sent (disabled, no
    channel configured, channel/guild missing, or the send itself failed)."""
    if not notify.enabled or not notify.channel_id:
        return None

    client = v.get_client(int(guild_id))
    guild = client.get_guild(int(guild_id)) if client else None
    if guild is None:
        return None
    channel = guild.get_channel(int(notify.channel_id))
    if channel is None:
        return None

    content = v.render_placeholders(notify.custom_message or "", channel=channel_title, url=video_url)
    if notify.mention_role_id:
        content = f"<@&{notify.mention_role_id}> {content}" if content else f"<@&{notify.mention_role_id}>"

    try:
        msg = await channel.send(
            content=content or None,
            embed=_build_youtube_embed(video, video_url, channel_title=channel_title, avatar_url=avatar_url, kind=kind),
        )
    except discord.HTTPException as e:
        logger.error("Failed to send YouTube notification in guild %s: %s", guild_id, e)
        return None
    return str(msg.id)

async def _handle_upcoming(channel_id: str, video_id: str, video: dict) -> bool:
    """Same success-reporting contract as _handle_new_video()."""
    channels = await YoutubeChannel.find(YoutubeChannel.resolved_channel_id == channel_id).to_list()
    if not channels:
        return False
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    any_sent = False
    for yt_channel in channels:
        channel_title = yt_channel.channel_title or (video.get("snippet") or {}).get("channelTitle", "")
        if await _send_youtube_notification(yt_channel.guild_id, yt_channel.upcoming, video, video_url, channel_title=channel_title, avatar_url=yt_channel.avatar_url, kind="upcoming"):
            any_sent = True
    return any_sent

async def _handle_new_video(channel_id: str, video_id: str, video: dict) -> bool:
    """Returns True if at least one guild's notification actually sent -
    callers use this to decide whether it's safe to mark this video as
    notified, so a failed send (Discord hiccup, a bad embed, whatever) gets
    retried on the next ping/poll instead of being silently swallowed forever."""
    channels = await YoutubeChannel.find(YoutubeChannel.resolved_channel_id == channel_id).to_list()
    if not channels:
        return False
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    any_sent = False
    for yt_channel in channels:
        channel_title = yt_channel.channel_title or (video.get("snippet") or {}).get("channelTitle", "")
        if await _send_youtube_notification(yt_channel.guild_id, yt_channel.video, video, video_url, channel_title=channel_title, avatar_url=yt_channel.avatar_url, kind="new_video"):
            any_sent = True
    return any_sent

async def _handle_went_live(channel_id: str, video_id: str, video: dict) -> bool:
    """Same success-reporting contract as _handle_new_video()."""
    channels = await YoutubeChannel.find(YoutubeChannel.resolved_channel_id == channel_id).to_list()
    if not channels:
        return False
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    any_sent = False
    for yt_channel in channels:
        channel_title = yt_channel.channel_title or (video.get("snippet") or {}).get("channelTitle", "")
        msg_id = await _send_youtube_notification(yt_channel.guild_id, yt_channel.live, video, video_url, channel_title=channel_title, avatar_url=yt_channel.avatar_url, kind="live")
        if msg_id:
            any_sent = True
            yt_channel.is_live = True
            yt_channel.current_video_id = video_id
            yt_channel.notification_message_id = msg_id
            await yt_channel.save()
    return any_sent

async def _handle_stream_ended(channel_id: str, video_id: str, video: dict):
    channels = await YoutubeChannel.find(YoutubeChannel.resolved_channel_id == channel_id).to_list()
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    for yt_channel in channels:
        if yt_channel.current_video_id != video_id:
            continue

        if yt_channel.notification_message_id and yt_channel.live.channel_id:
            client = v.get_client(int(yt_channel.guild_id))
            guild = client.get_guild(int(yt_channel.guild_id)) if client else None
            channel = guild.get_channel(int(yt_channel.live.channel_id)) if guild else None
            if channel:
                try:
                    msg = await channel.fetch_message(int(yt_channel.notification_message_id))
                    channel_title = yt_channel.channel_title or (video.get("snippet") or {}).get("channelTitle", "")
                    ended_embed = _build_youtube_embed(video, video_url, channel_title=channel_title, avatar_url=yt_channel.avatar_url, kind="ended")
                    await msg.edit(embed=ended_embed)
                except discord.NotFound:
                    pass
                except discord.HTTPException as e:
                    logger.error("Failed to edit ended YouTube notification in guild %s: %s", yt_channel.guild_id, e)

        yt_channel.is_live = False
        yt_channel.current_video_id = None
        await yt_channel.save()

def _is_actually_live(video: dict) -> bool:
    """liveBroadcastContent alone isn't trustworthy - a stream started via
    Studio's quick "stream now" flow can sit reporting "upcoming" for a long
    time (sometimes until the stream ends) despite genuinely being live, a
    known YouTube Data API quirk. liveStreamingDetails.actualStartTime is the
    reliable fallback signal - it's only set once a broadcast has genuinely
    started (unlike activeLiveChatId, which YouTube creates as soon as a
    stream is scheduled/prepared, well before it actually goes live - a real
    false-positive this produced in testing)."""
    snippet = video.get("snippet") or {}
    if snippet.get("liveBroadcastContent") == "live":
        return True
    details = video.get("liveStreamingDetails") or {}
    return bool(details.get("actualStartTime")) and not details.get("actualEndTime")

def _is_stream_ended(video: dict) -> bool:
    """Same unreliability problem as _is_actually_live(), the other direction:
    liveBroadcastContent can sit stuck on its pre-live value indefinitely even
    after the stream is over. liveStreamingDetails.actualEndTime only gets set
    once a broadcast has genuinely ended, so check that directly instead."""
    details = video.get("liveStreamingDetails") or {}
    return bool(details.get("actualEndTime"))

async def _handle_video_ping(channel_id: str, video_id: str):
    """WebSub only says "this video changed" - fetch it fresh to find out
    whether it's a plain new upload, a stream that's live now, or one that's
    merely scheduled (liveBroadcastContent: none/live/upcoming), then dedup
    against YoutubeVideoState so retries/edits never double-notify."""
    video = await youtube.get_video(video_id)
    if video is None:
        return
    live_status = (video.get("snippet") or {}).get("liveBroadcastContent", "none")
    is_live = _is_actually_live(video)

    state = await YoutubeVideoState.get(video_id)
    if state is None:
        state = YoutubeVideoState(id=video_id, channel_id=channel_id)
        await state.insert()

    if is_live:
        if not state.notified_live:
            sent = await _handle_went_live(channel_id, video_id, video)
            if sent:
                state.notified_live = True
                state.updated_at = datetime.now(timezone.utc)
                await state.save()
    elif live_status == "none" or _is_stream_ended(video):
        # live vs video notifications are kept mutually exclusive per video -
        # a stream's archived VOD is still that same live event, not a
        # separate upload, so it only ever gets the "went live" notification.
        # notified_new is purely for a video that was never a livestream.
        if state.notified_live:
            await _handle_stream_ended(channel_id, video_id, video)
        elif not state.notified_new:
            sent = await _handle_new_video(channel_id, video_id, video)
            if sent:
                state.notified_new = True
                state.updated_at = datetime.now(timezone.utc)
                await state.save()
    elif live_status == "upcoming":
        if not state.notified_upcoming:
            sent = await _handle_upcoming(channel_id, video_id, video)
            if sent:
                state.notified_upcoming = True
                state.updated_at = datetime.now(timezone.utc)
                await state.save()

async def _run_youtube_handler(channel_id: str, video_id: str):
    try:
        await _handle_video_ping(channel_id, video_id)
    except Exception as e:
        logger.error("Failed to handle YouTube notification for video %s: %s", video_id, e)

# ── Route ──────────────────────────────────────────────────────────────────
@social_webhooks_bp.route('/webhook/twitch/eventsub', methods=['POST'])
async def twitch_eventsub():
    if request.content_length and request.content_length > 1024 * 1024:
        return jsonify({"error": "Request too big"}), 400

    body = await request.get_data()
    message_id = request.headers.get(MESSAGE_ID_HEADER)
    timestamp = request.headers.get(MESSAGE_TIMESTAMP_HEADER)
    signature = request.headers.get(MESSAGE_SIGNATURE_HEADER)
    message_type = request.headers.get(MESSAGE_TYPE_HEADER)

    secret = current_app.config.get("TWITCH_EVENTSUB_SECRET")
    if not secret:
        logger.error("Twitch EventSub secret not configured")
        return jsonify({"error": "Webhook not configured"}), 500

    if not message_id or not timestamp or not _verify_signature(secret, message_id, timestamp, body, signature):
        return jsonify({"error": "Invalid signature"}), 403

    payload = await request.get_json()

    if message_type == "webhook_callback_verification":
        return Response(payload.get("challenge", ""), mimetype="text/plain")

    if message_type == "revocation":
        await _handle_revocation(payload.get("subscription", {}))
        return jsonify({"status": "ok"}), 200

    if message_type == "notification":
        if not await _claim_event(message_id):
            return jsonify({"status": "duplicate"}), 200

        sub_type = (payload.get("subscription") or {}).get("type")
        handler = NOTIFICATION_HANDLERS.get(sub_type)
        if not handler:
            return jsonify({"status": "ignored"}), 200

        asyncio.create_task(_run_handler(handler, sub_type, payload.get("event", {})))
        return jsonify({"status": "ok"}), 200

    return jsonify({"status": "ignored"}), 200

@social_webhooks_bp.route('/webhook/youtube/websub', methods=['GET', 'POST'])
async def youtube_websub():
    if request.method == 'GET':
        # The hub's verification handshake for a subscribe/unsubscribe request -
        # echo hub.challenge back to prove this callback is really listening.
        challenge = request.args.get('hub.challenge')
        mode = request.args.get('hub.mode')
        topic = request.args.get('hub.topic') or ""
        lease_seconds = request.args.get('hub.lease_seconds')

        if not challenge:
            return jsonify({"error": "Missing challenge"}), 400

        channel_id = topic.rsplit('channel_id=', 1)[-1] if 'channel_id=' in topic else None

        if channel_id and mode == 'subscribe':
            subscription = await YoutubeSubscription.get(channel_id)
            if subscription:
                if lease_seconds:
                    subscription.lease_expires = datetime.now(timezone.utc) + timedelta(seconds=int(lease_seconds))
                subscription.status = "enabled"
                await subscription.save()

        return Response(challenge, mimetype="text/plain")

    if request.content_length and request.content_length > 1024 * 1024:
        return jsonify({"error": "Request too big"}), 400

    body = await request.get_data()

    secret = current_app.config.get("YOUTUBE_WEBSUB_SECRET")
    if not secret:
        logger.error("YouTube WebSub secret not configured")
        return jsonify({"error": "Webhook not configured"}), 500

    signature = request.headers.get("X-Hub-Signature")
    if not _verify_websub_signature(secret, body, signature):
        return jsonify({"error": "Invalid signature"}), 403

    entries = _parse_websub_entries(body)
    for video_id, channel_id in entries:
        asyncio.create_task(_run_youtube_handler(channel_id, video_id))

    return jsonify({"status": "ok"}), 200