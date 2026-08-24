import logging
from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild, Birthday
from ...utils import bearer_client, login_required, premium_module

birthdays_bp = Blueprint('birthdays', __name__)
logger = logging.getLogger(__name__)


@birthdays_bp.route("/dashboard/<int:guild_id>/birthdays")
@login_required
async def birthdays(guild_id):
    premium_module(guild_id, 'birthdays')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Bunnet
    config = Guild.get(str(guild.id)).run().dashboard.birthdays
    
    return await render_template(
        "dashboard/plugins/birthdays.html",
        user=current_user,
        guild=guild,
        data=config,
    )