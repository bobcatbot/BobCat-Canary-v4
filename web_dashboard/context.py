from modules import bot as v
from modules.models import Guild, Notification
from .db import get_guild, get_dash_config
from .plugins import fetch_plugins
from .utils import bearer_client, guild_models

def register_context_processors(app):
    @app.context_processor
    async def utility_processor():

        async def plugs(guild):
            guild_dash = await get_dash_config(guild)
            return fetch_plugins(guild_dash)

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

        async def notifications(guild):
            """Returns notifications using the Beanie Notification model."""
            guild_id = str(getattr(guild, "id", guild))
            all_notifs = await Notification.find(Notification.guild_id == guild_id).to_list()

            shaped = []
            for n in all_notifs:
                shaped.append({
                    'id': n.notification_id,
                    'type': n.type,
                    'title': n.title,
                    'description': n.description,
                    'fix': n.fix,
                    'link': n.link,
                    'user': n.user,
                    'read': n.read,
                    'created_at': {
                        'date': n.created_at.strftime('%Y-%m-%d'),
                        'time': n.created_at.strftime('%H:%M:%S'),
                        'timestamp': n.created_at.timestamp(),
                    },
                })

            read = sorted(
                [n for n in shaped if n['read']],
                key=lambda n: n['created_at']['timestamp']
            )
            unread = sorted(
                [n for n in shaped if not n['read']],
                key=lambda n: n['created_at']['timestamp'],
                reverse=True
            )
            return {'read': read, 'unread': unread[:5], 'unread_count': len(unread)}

        return {
            'plugins': plugs,
            'get_plugin': get_plugin,
            'guilds': get_user_guilds,
            'guild_models': guild_models,
            'notifications': notifications,
        }