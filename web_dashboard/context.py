from quart import g
from modules import bot as v
from .config import INVITE_URL
from .db import get_bell_notifications
from .plugins import fetch_plugins
from .utils import get_current_user, GuildModels, _cached_guild
from .i18n import tr, viewer_lang

def register_context_processors(app):
    @app.context_processor
    async def utility_processor():

        async def plugs(guild):
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

            user_id = get_current_user().id
            return [
                {
                    'id': guild.id,
                    'name': guild.name,
                    'icon_url': guild.icon.with_size(64).url if guild.icon else None,
                }
                for guild in v.client.guilds
                if guild.get_member(user_id)
            ]

        async def guild_models(guild):
            await _cached_guild(guild.id)
            return GuildModels(guild)

        async def notifications(guild):
            return await get_bell_notifications(guild)

        return {
            'plugins': plugs,
            'get_plugin': get_plugin,
            'guilds': get_user_guilds,
            'guild_models': guild_models,
            'notifications': notifications,
            'inviteURL': INVITE_URL,
            't': tr,
            'lang': viewer_lang(),
        }