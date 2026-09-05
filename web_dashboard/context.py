from modules import bot as v
from modules.models import Notification
from .plugins import fetch_plugins
from .utils import bearer_client, GuildModels, _cached_guild

def register_context_processors(app):
    @app.context_processor
    async def utility_processor():

        async def plugs(guild):
            # _cached_guild memoizes the Guild doc per-request (on Quart's `g`),
            # so calling this repeatedly in one render (dashboard.html and the
            # sidebar each call it) only hits Mongo once, and does so with a
            # real async query instead of a blocking PyMongo call on the event
            # loop shared with the Discord bot.
            doc = await _cached_guild(getattr(guild, "id", guild))
            return fetch_plugins(doc.dashboard if doc else None)

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
            
            if "cached_guilds" in session:
                return [g for g in session["cached_guilds"] if g['id'] in guild_ids]
            
            guilds = []
            for guild in bearer_client().get_my_guilds():
                if guild.id in guild_ids:
                    guilds.append({
                        'id': guild.id,
                        'name': guild.name,
                        'icon_url': guild.icon_url,
                    })
            
            session["cached_guilds"] = guilds
            return guilds

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

            unread_docs = await Notification.find(
                Notification.guild_id == guild_id,
                Notification.read == False,
            ).sort(
                [(Notification.created_at, -1)]  # Newest first
            ).to_list()

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
                for n in unread_docs[:5]
            ]
            result = {'unread': unread, 'unread_count': len(unread_docs)}
            _notif_cache[guild_id] = result
            return result

        return {
            'plugins': plugs,
            'get_plugin': get_plugin,
            'guilds': get_user_guilds,
            'guild_models': GuildModels,
            'notifications': notifications,
        }