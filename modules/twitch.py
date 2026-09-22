"""Small Twitch Helix API helper: app access token (client-credentials grant, cached
in Mongo), user lookup, and EventSub subscription management. No existing shared HTTP
client helper in this codebase to build on - plain aiohttp calls per request, same
ad-hoc style used elsewhere (e.g. web_dashboard/blueprints/plugins/verification.py)."""

import aiohttp
from datetime import datetime, timedelta, timezone

from web_dashboard.config import twitch_config, URL_BASE
from modules.models import TwitchAppToken

HELIX_BASE = "https://api.twitch.tv/helix"
OAUTH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
EVENTSUB_CALLBACK = f"{URL_BASE}/webhook/twitch/eventsub"

# Refresh a bit before actual expiry so a request never races an expired token.
_REFRESH_MARGIN = timedelta(minutes=10)


async def get_app_token() -> str:
    """Return a cached, valid Twitch app access token - refreshing it (client
    credentials grant) if none is cached or the cached one is near expiry."""
    cached = await TwitchAppToken.get("twitch_app_token")
    if cached:
        expires_at = cached.expires_at
        # Mongo stores datetimes as UTC but the driver hands them back naive
        # (no tzinfo) on read, even though this was saved timezone-aware -
        # reattach UTC so the comparison below doesn't blow up.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at > datetime.now(timezone.utc) + _REFRESH_MARGIN:
            return cached.access_token

    async with aiohttp.ClientSession() as http:
        async with http.post(OAUTH_TOKEN_URL, data={
            "client_id": twitch_config["CLIENT_ID"],
            "client_secret": twitch_config["CLIENT_SECRET"],
            "grant_type": "client_credentials",
        }) as resp:
            resp.raise_for_status()
            data = await resp.json()

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=data["expires_in"])
    token = TwitchAppToken(
        id="twitch_app_token",
        access_token=data["access_token"],
        expires_at=expires_at,
    )
    await token.save()
    return token.access_token


async def _headers() -> dict:
    return {
        "Client-Id": twitch_config["CLIENT_ID"],
        "Authorization": f"Bearer {await get_app_token()}",
    }


async def get_user(login: str) -> dict | None:
    """Helix 'Get Users' - resolve a streamer login to its Twitch user id/display name.
    Returns None if no such user exists."""
    async with aiohttp.ClientSession() as http:
        async with http.get(
            f"{HELIX_BASE}/users",
            params={"login": login},
            headers=await _headers(),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    users = data.get("data") or []
    return users[0] if users else None


async def search_channels(query: str, limit: int = 8) -> list[dict]:
    """Helix 'Search Channels' - live-search suggestions for the dashboard's
    streamer picker. Returns [{login, display_name, thumbnail_url}, ...]."""
    if not query.strip():
        return []

    async with aiohttp.ClientSession() as http:
        async with http.get(
            f"{HELIX_BASE}/search/channels",
            params={"query": query, "first": limit},
            headers=await _headers(),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    return [
        {
            "login": channel["broadcaster_login"],
            "display_name": channel["display_name"],
            "thumbnail_url": channel["thumbnail_url"],
        }
        for channel in (data.get("data") or [])
    ]


async def get_stream(user_id: str) -> dict | None:
    """Helix 'Get Streams' - live stream details (title, game, preview thumbnail) for
    a broadcaster. The stream.online EventSub event itself only carries IDs and a
    started_at timestamp, not this, so the notification card needs this follow-up
    call. Returns None if the stream isn't actually live (e.g. it already ended by
    the time this runs)."""
    async with aiohttp.ClientSession() as http:
        async with http.get(
            f"{HELIX_BASE}/streams",
            params={"user_id": user_id},
            headers=await _headers(),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    streams = data.get("data") or []
    return streams[0] if streams else None


async def get_game(game_id: str) -> dict | None:
    """Helix 'Get Games' - box art for the notification card's "preview + box art"
    image mode. Returns None if Twitch has no game/category with this id."""
    if not game_id:
        return None

    async with aiohttp.ClientSession() as http:
        async with http.get(
            f"{HELIX_BASE}/games",
            params={"id": game_id},
            headers=await _headers(),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()

    games = data.get("data") or []
    return games[0] if games else None


async def create_eventsub_subscription(broadcaster_id: str) -> list[str]:
    """Subscribe to stream.online + stream.offline for a broadcaster. Returns the
    created subscription ids (Twitch requires one subscription per event type)."""
    sub_ids = []
    async with aiohttp.ClientSession() as http:
        for event_type in ("stream.online", "stream.offline"):
            async with http.post(
                f"{HELIX_BASE}/eventsub/subscriptions",
                headers=await _headers(),
                json={
                    "type": event_type,
                    "version": "1",
                    "condition": {"broadcaster_user_id": broadcaster_id},
                    "transport": {
                        "method": "webhook",
                        "callback": EVENTSUB_CALLBACK,
                        "secret": twitch_config["EVENTSUB_SECRET"],
                    },
                },
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                sub_ids.append(data["data"][0]["id"])
    return sub_ids


async def delete_eventsub_subscription(eventsub_id: str) -> None:
    async with aiohttp.ClientSession() as http:
        async with http.delete(
            f"{HELIX_BASE}/eventsub/subscriptions",
            params={"id": eventsub_id},
            headers=await _headers(),
        ) as resp:
            if resp.status not in (204, 404):
                resp.raise_for_status()
