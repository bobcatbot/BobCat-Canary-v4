from flask import Blueprint, render_template

from modules import bot as v
from ...db import get_dash_config
from ...utils import bearer_client, login_required, premium_module

birthdays_bp = Blueprint('birthdays', __name__)

@birthdays_bp.route("/dashboard/<int:guild_id>/birthdays")
@login_required
def birthdays(guild_id):
    premium_module(guild_id, 'birthdays')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    data = get_dash_config(guild.id).get('birthdays')
    
    return render_template(
        "dashboard/plugins/birthdays.html", 
        user=current_user, 
        guild=guild, 
        data=data
    )