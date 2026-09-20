# web_dashboard/db.py – QUART VERSION (NO FLASK g)

from modules import bot as v
from modules.models import Guild, Notification, DashConfig, SettingsConfig

def _guild_id(guild) -> str:
    return str(getattr(guild, "id", guild))

async def get_guild(guild) -> Guild | None:
    """
    Fetch the full Guild Beanie document.
    Removed Flask's `g` caching - Quart handles this differently.
    """
    guild_id = _guild_id(guild)
    return await Guild.get(guild_id)

async def get_settings_config(guild) -> SettingsConfig | None:
    doc = await get_guild(guild)
    return doc.settings if doc else None

async def get_dash_config(guild) -> DashConfig | None:
    """Async read of the guild's DashConfig. Quart's Jinja environment runs
    async, so context-processor helpers can await this directly instead of
    going through the blocking PyMongo client, which stalls the event loop
    that's shared with the Discord bot."""
    doc = await get_guild(guild)
    return doc.dashboard if doc else None

async def get_premium_config(guild) -> dict | None:
    doc = await get_guild(guild)
    return doc.premium if doc else None

async def get_bell_notifications(guild, limit: int = 5) -> dict:
    """What the navbar bell shows: the `limit` newest unread notifications and
    the guild's total unread count. Fetches just `limit` docs and uses count()
    for the total, since the backlog can be large. Shared by the bell's server
    render and its poll endpoint."""
    guild_id = _guild_id(guild)
    # Two queries on purpose: sort()/limit() mutate a query, and count() would
    # then honour the limit and cap the total at `limit`.
    def unread():
        return Notification.find(Notification.guild_id == guild_id, Notification.read == False)

    docs = await unread().sort([(Notification.created_at, -1)]).limit(limit).to_list()
    return {
        'unread': [
            {'id': n.notification_id, 'type': n.type, 'title': n.title, 'description': n.description}
            for n in docs
        ],
        'unread_count': await unread().count(),
    }
