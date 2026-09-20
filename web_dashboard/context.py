from quart import g

from modules import bot as v
from .db import get_bell_notifications
from .plugins import fetch_plugins
from .utils import get_my_guilds, GuildModels, _cached_guild

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

        async def get_user_guilds():
            from quart import session
            if "token" not in session:
                return []

            guild_ids = {g.id for g in v.client.guilds}

            return [
                {'id': guild.id, 'name': guild.name, 'icon_url': guild.icon_url}
                for guild in await get_my_guilds()
                if guild.id in guild_ids
            ]

        _notif_cache = {}

        async def notifications(guild):
            """Returns the guild's unread notifications for the navbar bell.

            DashNavbar.html calls this 3 times per page render, so the result
            is cached per-request/per-guild and Mongo is only hit once.
            """
            guild_id = str(getattr(guild, "id", guild))
            if guild_id in _notif_cache:
                return _notif_cache[guild_id]

            result = await get_bell_notifications(guild_id)
            _notif_cache[guild_id] = result
            return result

        return {
            'plugins': plugs,
            'get_plugin': get_plugin,
            'guilds': get_user_guilds,
            'guild_models': GuildModels,
            'notifications': notifications,
        }