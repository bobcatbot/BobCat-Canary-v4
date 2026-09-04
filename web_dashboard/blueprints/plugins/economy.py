import logging
from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild, Economy
from ...utils import bearer_client, plugin_guard, is_premium, plugin_item_cap
from ...plugins import PLUGIN_LIST

economy_bp = Blueprint('economy', __name__)
logger = logging.getLogger(__name__)

@economy_bp.route("/dashboard/<int:guild_id>/economy")
@plugin_guard('economy')
async def economy(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document
    config = await Guild.get(str(guild.id))
    
    # Get economy config from dashboard
    dash_data = config.dashboard.economy
    
    # Count shop items
    shop_items = dash_data.get('shop', [])
    num_items = len(shop_items)
    
    # Add num_items to the data for the template
    data = dash_data.copy() if isinstance(dash_data, dict) else {}
    data['num_items'] = num_items

    guild_premium = await is_premium(guild)

    return await render_template(
        "dashboard/plugins/economy.html",
        user=current_user,
        guild=guild,
        data=data,
        is_premium=guild_premium,
        shop_cap=plugin_item_cap('economy', guild_premium),
        shop_cap_premium=_ECONOMY_META.get('max_premium', 15),
    )