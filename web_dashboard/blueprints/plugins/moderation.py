import logging
from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, plugin_guard

moderation_bp = Blueprint('moderation', __name__)
logger = logging.getLogger(__name__)

@moderation_bp.route("/dashboard/<int:guild_id>/moderator")
@plugin_guard('moderation')
async def moderation(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.moderation

    # Get logging config from moderation
    logging_config = config.get('logging', {})
    
    return await render_template(
        "dashboard/plugins/moderation.html",
        user=current_user,
        guild=guild,
        data=config,
        logging=logging_config
    )