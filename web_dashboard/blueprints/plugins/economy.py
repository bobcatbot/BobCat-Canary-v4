from flask import Blueprint, render_template

from modules import bot as v
from ...db import get_dash_config
from ...utils import bearer_client, login_required, premium_module

economy_bp = Blueprint('economy', __name__)

@economy_bp.route("/dashboard/<int:guild_id>/economy")
@login_required
def economy(guild_id):
    premium_module(guild_id, 'economy')
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    dash = get_dash_config(guild.id).get('economy')
    
    data = dash | {'num_items': len(dash['shop'])}
    
    return render_template(
        "dashboard/plugins/economy.html", 
        user=current_user, 
        guild=guild, 
        data=data
    )