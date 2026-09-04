import logging
from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, plugin_guard

starboard_bp = Blueprint('starboard', __name__)
logger = logging.getLogger(__name__)

@starboard_bp.route("/dashboard/<int:guild_id>/starboard")
@plugin_guard('starboard')
async def starboard(guild_id):
    current_user = bearer_client().get_current_user()

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.starboard
    
    return await render_template(
        "dashboard/plugins/starboard.html",
        user=current_user,
        guild=guild,
        data=config
    )