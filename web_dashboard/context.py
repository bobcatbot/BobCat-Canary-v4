from quart import g

from modules import bot as v
from modules.models import Notification
from .plugins import fetch_plugins
from .utils import bearer_client, GuildModels, _cached_guild

def register_context_processors(app):
    @app.context_processor
    async def utility_processor():

        async def plugs(guild):
            # dashboard.html iterates this 4x and the sidebar once more per
            # render; memoize the shaped list per-request/per-guild on Quart's
            # `g` so fetch_plugins (a deepcopy of PLUGIN_LIST + a status merge)
            # runs once instead of ~5x on the event loop shared with the bot.
            # _cached_guild already memoizes the underlying Guild doc the same
            # way; this also spares a blocking PyMongo call per iteration.
            guild_id = str(getattr(guild, "id", guild))
            cache = getattr(g, "_plugins_cache", None)
            if cache is None:
                cache = {}
                g._plugins_cache = cache
            if guild_id not in cache:
                doc = await _cached_guild(guild_id)
                cache[guild_id] = fetch_plugins(doc.dashboard if doc else None)
            return cache[guild_id]

        async def get_plugin(guild, plugin):
            return next(
                (_plugin for _item, _plugin in await plugs(guild) if _item == plugin),
                None
            )

        def get_user_guilds():
            from quart import session
            if "token" not in session:
                return []

            guild_ids = {g.id for g in v.client.guilds}

            return [
                {'id': guild.id, 'name': guild.name, 'icon_url': guild.icon_url}
                for guild in bearer_client().get_my_guilds()
                if guild.id in guild_ids
            ]

        _notif_cache = {}

        async def notifications(guild):
            """Returns the guild's unread notifications for the navbar bell.

            Only `unread` (capped to 5) and `unread_count` are used by
            DashNavbar.html, which calls this 3 times per page render - so
            this queries unread-only (sorted/newest-first at the DB level,
            not fetching+sorting the guild's whole notification history in
            Python) and caches the result per-request/per-guild so the 3
            calls only hit Mongo once.
            """
            guild_id = str(getattr(guild, "id", guild))
            if guild_id in _notif_cache:
                return _notif_cache[guild_id]

            # Only the 5 newest are shown; fetch just those, and get the total
            # with a count() rather than materialising every unread doc (the
            # backlog is unbounded - nothing marks notifications read).
            unread_docs = await Notification.find(
                Notification.guild_id == guild_id,
                Notification.read == False,
            ).sort(
                [(Notification.created_at, -1)]  # Newest first
            ).limit(5).to_list()
            unread_count = await Notification.find(
                Notification.guild_id == guild_id,
                Notification.read == False,
            ).count()

            unread = [
                {
                    'id': n.notification_id,
                    'type': n.type,
                    'title': n.title,
                    'description': n.description,
                    'fix': n.fix,
                    'link': n.link,
                    'user': n.user,
                    'read': n.read,
                    'created_at': {
                        'date': n.created_at.strftime('%Y-%m-%d') if n.created_at else '',
                        'time': n.created_at.strftime('%H:%M:%S') if n.created_at else '',
                        'timestamp': n.created_at.timestamp() if n.created_at else 0,
                    },
                }
                for n in unread_docs
            ]
            result = {'unread': unread, 'unread_count': unread_count}
            _notif_cache[guild_id] = result
            return result

        return {
            'plugins': plugs,
            'get_plugin': get_plugin,
            'guilds': get_user_guilds,
            'guild_models': GuildModels,
            'notifications': notifications,
        }