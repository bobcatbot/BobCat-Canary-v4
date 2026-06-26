from flask import Blueprint, render_template

from modules import bot as v
from ...db import get_dash_config
from ...utils import bearer_client, login_required, premium_module

moderation_bp = Blueprint('moderation', __name__)

@moderation_bp.route("/dashboard/<int:guild_id>/moderator")
@login_required
def moderation(guild_id):
    premium_module(guild_id, 'moderation')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    dash_data = get_dash_config(guild).get('moderation')
    
    return render_template(
        "dashboard/plugins/moderation.html",
        user=current_user, guild=guild, 
        data=dash_data, 
        logging=dash_data['logging']
    )