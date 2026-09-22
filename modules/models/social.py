from beanie import Document
from pydantic import ConfigDict, Field
from datetime import datetime, timezone
from typing import List, Optional
from .core import DictModel, EmbedConfig

# ---------------------------------------------------------
# Twitch notifications plugin
# ---------------------------------------------------------
class TwitchConfig(DictModel):
    status: bool = False

class TwitchStreamer(Document):
    # The dashboard assigns whatever the page posts, so validate on assignment,
    # same reasoning as Giveaway (modules/models/giveaways.py).
    model_config = ConfigDict(validate_assignment=True)

    class Settings:
        name = "twitch_streamers"
        indexes = ["guild_id", "streamer_user_id"]

    id: str = Field(alias="_id")
    guild_id: str
    streamer_login: str
    streamer_user_id: str
    streamer_display_name: str
    avatar_url: Optional[str] = None  # captured once at add-time, for the notification card
    channel_id: str
    mention_role_id: Optional[str] = None
    custom_message: str = "{streamer} is now live!"
    watch_button: bool = True
    show_viewers: bool = False
    # "none" - no embed at all, just the plain message
    # "preview" - stream preview image (default)
    # "preview_boxart" - stream preview + the game's box art as the embed thumbnail
    # "minimal" - embed shown, no image/thumbnail at all
    embed_image_mode: str = "preview"

    # Live-state tracking, written by the EventSub webhook handler.
    is_live: bool = False
    current_stream_id: Optional[str] = None
    notification_message_id: Optional[str] = None

class TwitchSubscription(Document):
    """One row per Twitch broadcaster with an active EventSub subscription - shared
    across every guild watching that streamer, since EventSub subscriptions are
    owned by the app, not by a guild."""

    class Settings:
        name = "twitch_subscriptions"

    id: str = Field(alias="_id")  # Twitch broadcaster user_id
    # Twitch requires one subscription per event type - one each for
    # stream.online and stream.offline (see modules/twitch.py).
    eventsub_ids: List[str] = Field(default_factory=list)
    status: str = "enabled"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TwitchAppToken(Document):
    """Single-doc cache for the Twitch app access token (client-credentials grant),
    mirroring the Maintenance singleton pattern (modules/models/core.py)."""

    class Settings:
        name = "twitch_app_token"

    id: str = "twitch_app_token"
    access_token: str
    expires_at: datetime

class TwitchEvent(Document):
    """Record of a processed EventSub notification, keyed on Twitch's message id -
    mirrors StripeEvent (modules/models/core.py) so a Twitch retry of the same
    notification is skipped rather than double-posted."""

    class Settings:
        name = "twitch_events"

    id: str = Field(alias="_id")  # Twitch-Eventsub-Message-Id
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ---------------------------------------------------------
# YouTube notifications plugin
# ---------------------------------------------------------
class YoutubeConfig(DictModel):
    status: bool = False

class YoutubeNotifyConfig(DictModel):
    """Shared shape for a YoutubeChannel's Video-tab or Live-tab settings block."""
    channel_id: Optional[str] = None
    mention_role_id: Optional[str] = None
    custom_message: str = ""
    embed: EmbedConfig = Field(default_factory=lambda: EmbedConfig(color=0xFF0000))
    enabled: bool = False

class YoutubeChannel(Document):
    model_config = ConfigDict(validate_assignment=True)

    class Settings:
        name = "youtube_channels"
        indexes = ["guild_id"]

    id: str = Field(alias="_id")
    guild_id: str
    channel_identifier: str  # handle/URL as entered on the dashboard
    resolved_channel_id: Optional[str] = None  # filled in once detection ships
    video: YoutubeNotifyConfig = Field(default_factory=YoutubeNotifyConfig)
    live: YoutubeNotifyConfig = Field(default_factory=YoutubeNotifyConfig)
