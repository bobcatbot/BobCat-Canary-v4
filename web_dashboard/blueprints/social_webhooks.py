import asyncio
import hmac
import hashlib
import logging
import discord
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from quart import Blueprint, current_app, jsonify, request, Response

from modules import bot as v
from modules import twitch
from modules.models import TwitchStreamer as TwitchStreamers, TwitchSubscription, TwitchEvent

TWITCH_PURPLE = 0x9146FF

# Twitch's live preview thumbnail isn't generated the instant a stream starts -
# fetching stream details (and posting) right on stream.online gets a generic
# "404 preview" placeholder image instead of a real one. Wait this long before
# doing either, so the thumbnail's actually ready.
STREAM_ONLINE_DELAY_SECONDS = 90

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
        embed.add_field(name="Game", value=game, inline=False)
    if streamer.show_viewers and viewer_count is not None:
        embed.add_field(name="Viewers", value=str(viewer_count), inline=False)

    if mode != "minimal" and thumbnail_template:
        embed.set_image(url=thumbnail_template.format(width=440, height=248))

    if mode == "preview_boxart" and game_id:
        try:
            game_data = await twitch.get_game(game_id)
        except Exception as e:
            logger.warning("Failed to fetch box art for game %s: %s", game_id, e)
            game_data = None
        if game_data and game_data.get("box_art_url"):
            embed.set_thumbnail(url=game_data["box_art_url"].format(width=144, height=192))

    embed.set_footer(text="BobCat")
    return embed


async def _handle_stream_online(event: dict):
    await asyncio.sleep(STREAM_ONLINE_DELAY_SECONDS)

    broadcaster_id = event["broadcaster_user_id"]
    streamers = await TwitchStreamers.find(TwitchStreamers.streamer_user_id == broadcaster_id).to_list()
    if not streamers:
        return

    try:
        stream = await twitch.get_stream(broadcaster_id)
    except Exception as e:
        logger.warning("Failed to fetch live stream details for %s: %s", broadcaster_id, e)
        stream = None

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
