"""YouTube notification housekeeping. New-video detection is push-based
(WebSub/PubSubHubbub, handled in web_dashboard/blueprints/social_webhooks.py)
and reliable enough there to not need polling. The scheduled->live transition
specifically is NOT reliable over WebSub in practice - live testing showed
zero pings delivered for a confirmed-live, confirmed-public stream, a known
issue other YouTube-notifier bots report too - so this cog also runs a cheap
polling fallback just for "went live" detection, using the channel's uploads
playlist (2 quota units/poll) instead of search.list?eventType=live (100
units/call, the reason polling was ruled out for this originally). Both paths
funnel into the same _handle_video_ping()/YoutubeVideoState dedup, so a late
WebSub delivery can never double-post on top of what polling already caught."""
import logging
from datetime import datetime, timedelta, timezone
from discord.ext import commands, tasks
from modules import youtube
from modules.models import YoutubeChannel, YoutubeSubscription
from web_dashboard.blueprints.social_webhooks import _handle_video_ping

logger = logging.getLogger(__name__)
RENEWAL_WINDOW = timedelta(days=2)
LIVE_POLL_MINUTES = 2

class YoutubeHousekeeping(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.maintain_subscriptions.is_running():
            self.maintain_subscriptions.start()
        if not self.poll_live_status.is_running():
            self.poll_live_status.start()

    def cog_unload(self):
        self.maintain_subscriptions.cancel()
        self.poll_live_status.cancel()

    @tasks.loop(hours=24)
    async def maintain_subscriptions(self):
        subscriptions = await YoutubeSubscription.find_all().to_list()
        now = datetime.now(timezone.utc)

        for subscription in subscriptions:
            remaining = await YoutubeChannel.find(YoutubeChannel.resolved_channel_id == subscription.id).count()
            if remaining == 0:
                try:
                    await youtube.unsubscribe(subscription.id)
                except Exception as e:
                    logger.warning("Failed to unsubscribe orphaned YouTube channel %s: %s", subscription.id, e)
                await subscription.delete()
                logger.info("Pruned orphaned YouTube subscription for channel %s", subscription.id)
                continue

            lease_expires = subscription.lease_expires
            if lease_expires and lease_expires.tzinfo is None:
                lease_expires = lease_expires.replace(tzinfo=timezone.utc)
            if lease_expires and lease_expires > now + RENEWAL_WINDOW:
                continue

            try:
                await youtube.subscribe(subscription.id)
            except Exception as e:
                logger.error("Failed to renew YouTube WebSub lease for %s: %s", subscription.id, e)

    @maintain_subscriptions.before_loop
    async def before_maintain_subscriptions(self):
        await self.client.wait_until_ready()

    @tasks.loop(minutes=LIVE_POLL_MINUTES)
    async def poll_live_status(self):
        channels = await YoutubeChannel.find_all().to_list()
        watched_channel_ids = {c.resolved_channel_id for c in channels if c.live.enabled and c.resolved_channel_id}

        for channel_id in watched_channel_ids:
            # Directly re-check any video already tracked as live for this
            # channel - catches the ended transition even when the uploads-
            # playlist discovery below hasn't picked the video up at all,
            # which happens often enough in practice to not rely on it alone.
            live_video_ids = {
                c.current_video_id for c in channels
                if c.resolved_channel_id == channel_id and c.is_live and c.current_video_id
            }
            for video_id in live_video_ids:
                try:
                    await _handle_video_ping(channel_id, video_id)
                except Exception as e:
                    logger.error("Failed to re-check live video %s on channel %s: %s", video_id, channel_id, e)

            subscription = await YoutubeSubscription.get(channel_id)
            if subscription is None:
                continue

            if not subscription.uploads_playlist_id:
                try:
                    subscription.uploads_playlist_id = await youtube.get_uploads_playlist_id(channel_id)
                except Exception as e:
                    logger.error("Failed to resolve uploads playlist for YouTube channel %s: %s", channel_id, e)
                    continue
                if not subscription.uploads_playlist_id:
                    continue
                await subscription.save()

            try:
                video_id = await youtube.get_latest_upload(subscription.uploads_playlist_id)
            except Exception as e:
                logger.error("Failed to poll latest upload for YouTube channel %s: %s", channel_id, e)
                continue
            if not video_id:
                continue

            await _handle_video_ping(channel_id, video_id)

    @poll_live_status.before_loop
    async def before_poll_live_status(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(YoutubeHousekeeping(client))