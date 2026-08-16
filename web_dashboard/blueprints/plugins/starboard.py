import logging
from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild
from ...db import get_guild
from ...utils import bearer_client, login_required, premium_module

starboard_bp = Blueprint('starboard', __name__)
logger = logging.getLogger(__name__)

@starboard_bp.route("/dashboard/<int:guild_id>/starboard")
@login_required
async def starboard(guild_id):
    try:
        premium_module(guild_id, 'starboard')

        current_user = bearer_client().get_current_user()

        guild = v.client.get_guild(guild_id)
        if guild is None:
            return await render_template("error/404.html"), 404

        # Get the guild document using Bunnet
        config = Guild.get(str(guild.id)).run().dashboard.starboard
        
        return await render_template(
            "dashboard/plugins/starboard.html",
            user=current_user,
            guild=guild,
            data=config
        )
    except Exception as e:
        logger.error(f"Error loading starboard page for guild {guild_id}: {e}", exc_info=True)
        return await render_template("error/500.html"), 500