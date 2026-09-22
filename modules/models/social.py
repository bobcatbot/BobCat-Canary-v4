from beanie import Document
from pydantic import ConfigDict, Field
from datetime import datetime, timezone
from typing import List, Optional
from .core import DictModel

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
    """Shared shape for a YoutubeChannel's Upcoming/Video/Live-tab settings
    block. No user-customizable embed here - the notification card itself
    (title/thumbnail/timestamp) is pre-built fresh from YouTube's own data
    each time (see _build_youtube_embed), same reasoning as Twitch's card."""
    channel_id: Optional[str] = None
    mention_role_id: Optional[str] = None
    custom_message: str = ""
    enabled: bool = False

class YoutubeChannel(Document):
    model_config = ConfigDict(validate_assignment=True)

    class Settings:
        name = "youtube_channels"
        indexes = ["guild_id", "resolved_channel_id"]

    id: str = Field(alias="_id")
    guild_id: str
    channel_identifier: str  # handle/URL as entered on the dashboard
    resolved_channel_id: Optional[str] = None
    channel_title: Optional[str] = None  # captured once at add-time, for the notification card
    avatar_url: Optional[str] = None  # captured once at add-time, for the notification card
    upcoming: YoutubeNotifyConfig = Field(default_factory=YoutubeNotifyConfig)
    video: YoutubeNotifyConfig = Field(default_factory=YoutubeNotifyConfig)
    live: YoutubeNotifyConfig = Field(default_factory=YoutubeNotifyConfig)

    # Live-state tracking, written by the WebSub webhook handler.
    is_live: bool = False
    current_video_id: Optional[str] = None
    notification_message_id: Optional[str] = None

class YoutubeSubscription(Document):
    """One row per real YouTube channel id with an active WebSub lease - shared
    across every guild watching that channel, since a WebSub subscription is
    owned by the app+topic, not by a guild (mirrors TwitchSubscription)."""

    class Settings:
        name = "youtube_subscriptions"

    id: str = Field(alias="_id")  # resolved YouTube channel id
    status: str = "enabled"  # enabled | revoked
    # WebSub leases expire (~10 days max) and need periodic renewal - see
    # cogs/social/B_youtube.py.
    lease_expires: Optional[datetime] = None
    # Cached so the "went live" polling fallback (cogs/social/B_youtube.py)
    # only spends 1 quota unit resolving it once, not on every poll.
    uploads_playlist_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class YoutubeVideoState(Document):
    """Per-video notification bookkeeping, keyed on YouTube's own video id.
    WebSub redelivers on every edit to a video (title change, description edit,
    a scheduled stream flipping to live) and can retry deliveries outright, so
    this is what stops a "new video" or "went live" notification from firing
    more than once for the same video."""

    class Settings:
        name = "youtube_video_state"

    id: str = Field(alias="_id")  # YouTube video id
    channel_id: str
    notified_upcoming: bool = False
    notified_new: bool = False
    notified_live: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
