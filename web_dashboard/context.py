from flask import session

from modules import bot as v
from .db import get_server_config, get_dash_config
from .plugins import fetch_plugins
from .utils import bearer_client, GuildModels

def register_context_processors(app):
    @app.context_processor
    def utility_processor():
        
        def plugs(guild):
            guild_dash = get_dash_config(guild)
            return fetch_plugins(guild_dash)

        def get_plugin(guild, plugin):
            return next(
                (_plugin for _item, _plugin in plugs(guild) if _item == plugin),
                None
            )

        def get_user_guilds():
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
            all_notifs = get_server_config(guild, True)['notifications']
            read = sorted(
                [n for n in all_notifs if n['read']],
                key=lambda n: n['created_at']['timestamp']
            )
            unread = sorted(
                [n for n in all_notifs if not n['read']],
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