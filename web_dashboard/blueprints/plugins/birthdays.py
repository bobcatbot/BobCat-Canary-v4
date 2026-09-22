from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild, Birthday
from ...utils import get_current_user, plugin_guard

birthdays_bp = Blueprint('birthdays', __name__)


@birthdays_bp.route("/dashboard/<int:guild_id>/birthdays")
@plugin_guard('birthdays')
async def birthdays(guild_id):
    current_user = get_current_user()
    
    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.birthdays
    
    return await render_template(
        "dashboard/plugins/birthdays.html",
        user=current_user,
        guild=guild,
        data=config,
    )