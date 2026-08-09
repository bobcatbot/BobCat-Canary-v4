from flask import Blueprint, render_template

from modules import bot as v
from modules.models import Guild
from ...db import get_guild
from ...utils import bearer_client, login_required, premium_module

starboard_bp = Blueprint('starboard', __name__)

@starboard_bp.route("/dashboard/<int:guild_id>/starboard")
@login_required
def starboard(guild_id):
    premium_module(guild_id, 'starboard')

    current_user = bearer_client().get_current_user()

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return render_template("error/404.html"), 404

    # Get the guild document using Bunnet
    config = Guild.get(str(guild.id)).run().dashboard.starboard
    
    return render_template(
        "dashboard/plugins/starboard.html",
        user=current_user,
        guild=guild,
        data=config
    )