"""Twitch notification housekeeping. Live-status detection itself is push-based
(Twitch EventSub webhooks, handled in web_dashboard/blueprints/social_webhooks.py)
so this cog carries no polling loop for notifications - just a daily safety-net
pass that prunes EventSub subscriptions no guild references anymore (in case a
dashboard delete route failed partway through) and keeps the cached app token
fresh."""
import logging
from discord.ext import commands, tasks
from modules import twitch
from modules.models import TwitchStreamer, TwitchSubscription

logger = logging.getLogger(__name__)

class TwitchHousekeeping(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.prune_orphaned_subscriptions.is_running():
            self.prune_orphaned_subscriptions.start()

    def cog_unload(self):
        self.prune_orphaned_subscriptions.cancel()

    @tasks.loop(hours=24)
    async def prune_orphaned_subscriptions(self):
        try:
            await twitch.get_app_token()
        except Exception as e:
            logger.error("Failed to refresh Twitch app token: %s", e)
            return

        subscriptions = await TwitchSubscription.find_all().to_list()
        for subscription in subscriptions:
            remaining = await TwitchStreamer.find(TwitchStreamer.streamer_user_id == subscription.id).count()
            if remaining > 0:
                continue

            for eventsub_id in subscription.eventsub_ids:
                try:
                    await twitch.delete_eventsub_subscription(eventsub_id)
                except Exception as e:
                    logger.warning("Failed to delete orphaned EventSub subscription %s: %s", eventsub_id, e)
            await subscription.delete()
            logger.info("Pruned orphaned Twitch subscription for broadcaster %s", subscription.id)

    @prune_orphaned_subscriptions.before_loop
    async def before_prune_orphaned_subscriptions(self):
        await self.client.wait_until_ready()

def setup(client):
    client.add_cog(TwitchHousekeeping(client))