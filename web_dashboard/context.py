from modules import bot as v
from .db import get_dash_config
from .plugins import fetch_plugins
from .utils import bearer_client, GuildModels

def register_context_processors(app):
    @app.context_processor
    async def utility_processor():

        def plugs(guild):
            guild_dash = get_dash_config(guild)
            return fetch_plugins(guild_dash)

        def get_plugin(guild, plugin):
            return next(
                (_plugin for _item, _plugin in plugs(guild) if _item == plugin),
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

        def notifications(guild):
            """Returns the guild's notifications for the navbar (read-only, sync)."""
            guild_id = str(getattr(guild, "id", guild))
            all_notifs = list(v._sync_notifs.find({"guild_id": guild_id}))

            shaped = []
            for n in all_notifs:
                created = n.get("created_at")
                shaped.append({
                    'id': n.get('notification_id'),
                    'type': n.get('type', 'info'),
                    'title': n.get('title'),
                    'description': n.get('description'),
                    'fix': n.get('fix'),
                    'link': n.get('link'),
                    'user': n.get('user'),
                    'read': n.get('read', False),
                    'created_at': {
                        'date': created.strftime('%Y-%m-%d') if created else '',
                        'time': created.strftime('%H:%M:%S') if created else '',
                        'timestamp': created.timestamp() if created else 0,
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
            'guild_models': GuildModels,
            'notifications': notifications,
        }