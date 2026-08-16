import logging
from datetime import datetime, timezone
from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild, Economy
from ...utils import bearer_client, login_required, premium_module

economy_bp = Blueprint('economy', __name__)
logger = logging.getLogger(__name__)

@economy_bp.route("/dashboard/<int:guild_id>/economy")
@login_required
async def economy(guild_id):
    try:
        premium_module(guild_id, 'economy')
        
        current_user = bearer_client().get_current_user()
        
        guild = v.client.get_guild(guild_id)
        if guild is None:
            return await render_template("error/404.html"), 404

        # Get the guild document
        config = Guild.get(str(guild.id)).run()
        if config is None:
            # Create default config if it doesn't exist
            config = Guild(
                id=str(guild.id),
                premium={},
                settings={
                    'language': guild.preferred_locale or 'en-US',
                    'timezone': 'UTC',
                    'color': '#5865f2',
                    'admin_roles': [],
                    'bot_masters': [],
                    'moderator_roles': []
                },
                dashboard={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            config.insert()
            config = Guild.get(str(guild.id)).run()
            logger.info(f"Created default config for guild {guild_id}")

        # Get economy config from dashboard
        dash_data = config.dashboard.economy
        
        # Count shop items
        shop_items = dash_data.get('shop', [])
        num_items = len(shop_items)
        
        # Add num_items to the data for the template
        data = dash_data.copy() if isinstance(dash_data, dict) else {}
        data['num_items'] = num_items
        
        return await render_template(
            "dashboard/plugins/economy.html",
            user=current_user,
            guild=guild,
            data=data
        )
    except Exception as e:
        logger.error(f"Error loading economy page for guild {guild_id}: {e}", exc_info=True)
        return await render_template("error/500.html"), 500