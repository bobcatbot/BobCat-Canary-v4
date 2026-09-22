"""Small YouTube helper: channel resolution + video lookups via the Data API v3
(plain API key, no OAuth needed for public data), plus WebSub (PubSubHubbub)
subscription management for push-based new-video/went-live detection. Same
ad-hoc aiohttp-per-request style as modules/twitch.py - no shared HTTP client
helper in this codebase to build on."""
import aiohttp
from web_dashboard.config import youtube_config, URL_BASE

DATA_API_BASE = "https://www.googleapis.com/youtube/v3"
WEBSUB_HUB = "https://pubsubhubbub.appspot.com/subscribe"
WEBSUB_CALLBACK = f"{URL_BASE}/webhook/youtube/websub"
WEBSUB_TOPIC = "https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"

# Google caps WebSub leases at ~10 days - request just under that so a lease
# never lapses between housekeeping renewal passes (see cogs/social/B_youtube.py).
WEBSUB_LEASE_SECONDS = 828000  # ~9.6 days

def _extract_identifier(raw: str) -> tuple[str, str]:
    """Classify a dashboard-entered channel URL/handle into (kind, value), where
    kind is 'id', 'handle', or 'query' (best-effort fallback for anything else,
    e.g. a legacy /c/CustomName vanity URL that isn't a real handle)."""
    value = raw.strip()
    for prefix in ("https://www.youtube.com/", "https://youtube.com/", "www.youtube.com/", "youtube.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix):]
            break
    value = value.strip("/")

    if value.startswith("channel/"):
        return "id", value[len("channel/"):]
    if value.startswith("@"):
        return "handle", value
    if value.startswith("c/") or value.startswith("user/"):
        value = value.split("/", 1)[1]
        return "query", value
    if value.startswith("UC") and len(value) == 24:
        return "id", value
    return "handle", f"@{value}" if not value.startswith("@") else value

async def resolve_channel(identifier: str) -> dict | None:
    """Resolve a dashboard-entered handle/URL/channel ID to a real channel.
    Returns {id, title, thumbnail_url} or None if nothing matches."""
    kind, value = _extract_identifier(identifier)
    params = {"part": "snippet", "key": youtube_config["API_KEY"]}
    if kind == "id":
        params["id"] = value
    elif kind == "handle":
        params["forHandle"] = value
    else:
        params["forUsername"] = value

    async with aiohttp.ClientSession() as http:
        async with http.get(f"{DATA_API_BASE}/channels", params=params) as resp:
            resp.raise_for_status()
            data = await resp.json()

    channels = data.get("items") or []
    if not channels and kind != "query":
        return None
    if not channels:
        # Legacy vanity URLs (/c/CustomName) aren't resolvable via the Data API
        # directly - search is the only fallback, at a much higher quota cost.
        async with aiohttp.ClientSession() as http:
            async with http.get(f"{DATA_API_BASE}/search", params={
                "part": "snippet", "type": "channel", "q": value, "maxResults": 1,
                "key": youtube_config["API_KEY"],
            }) as resp:
                resp.raise_for_status()
                search_data = await resp.json()
        results = search_data.get("items") or []
        if not results:
            return None
        channel_id = results[0]["snippet"]["channelId"]
        return await resolve_channel(channel_id)

    channel = channels[0]
    snippet = channel["snippet"]
    return {
        "id": channel["id"],
        "title": snippet.get("title"),
        "thumbnail_url": (snippet.get("thumbnails") or {}).get("default", {}).get("url"),
    }


async def get_uploads_playlist_id(channel_id: str) -> str | None:
    """Data API 'Channels: list' (1 quota unit) - the channel's uploads
    playlist id, cached on YoutubeSubscription and used by get_latest_upload()
    as a cheap "went live" polling fallback (WebSub's push for the scheduled
    -> live transition specifically isn't reliable in practice - see
    cogs/social/B_youtube.py). 2 units/poll total this way instead of the much
    pricier search.list?eventType=live (100 units/call)."""
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{DATA_API_BASE}/channels", params={
            "part": "contentDetails",
            "id": channel_id,
            "key": youtube_config["API_KEY"],
        }) as resp:
            resp.raise_for_status()
            data = await resp.json()

    channels = data.get("items") or []
    if not channels:
        return None
    return channels[0]["contentDetails"]["relatedPlaylists"]["uploads"]

async def get_latest_upload(playlist_id: str) -> str | None:
    """Data API 'PlaylistItems: list' (1 quota unit) - the most recent video id
    in a channel's uploads playlist. A stream appears here the instant it goes
    live, same as a normal upload does."""
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{DATA_API_BASE}/playlistItems", params={
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 1,
            "key": youtube_config["API_KEY"],
        }) as resp:
            resp.raise_for_status()
            data = await resp.json()

    items = data.get("items") or []
    if not items:
        return None
    return items[0]["contentDetails"]["videoId"]

async def get_video(video_id: str) -> dict | None:
    """Data API 'Videos: list' - used to classify a WebSub-pinged video as a
    genuinely new upload, a stream that's live now, or one that's merely
    scheduled (liveBroadcastContent: none/live/upcoming). Returns None if the
    video doesn't exist (e.g. deleted between the ping and this lookup)."""
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{DATA_API_BASE}/videos", params={
            "part": "snippet,liveStreamingDetails",
            "id": video_id,
            "key": youtube_config["API_KEY"],
        }) as resp:
            resp.raise_for_status()
            data = await resp.json()

    videos = data.get("items") or []
    return videos[0] if videos else None

async def subscribe(channel_id: str) -> None:
    """Subscribe (or renew) a WebSub lease for a channel's upload feed."""
    async with aiohttp.ClientSession() as http:
        async with http.post(WEBSUB_HUB, data={
            "hub.callback": WEBSUB_CALLBACK,
            "hub.topic": WEBSUB_TOPIC.format(channel_id=channel_id),
            "hub.mode": "subscribe",
            "hub.verify": "async",
            "hub.secret": youtube_config["WEBSUB_SECRET"],
            "hub.lease_seconds": str(WEBSUB_LEASE_SECONDS),
        }) as resp:
            if resp.status not in (202, 204):
                resp.raise_for_status()

async def unsubscribe(channel_id: str) -> None:
    async with aiohttp.ClientSession() as http:
        async with http.post(WEBSUB_HUB, data={
            "hub.callback": WEBSUB_CALLBACK,
            "hub.topic": WEBSUB_TOPIC.format(channel_id=channel_id),
            "hub.mode": "unsubscribe",
            "hub.verify": "async",
            "hub.secret": youtube_config["WEBSUB_SECRET"],
        }) as resp:
            if resp.status not in (202, 204):
                resp.raise_for_status()
