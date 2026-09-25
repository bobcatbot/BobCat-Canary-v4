from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild
from ...utils import get_current_user, plugin_guard

custom_commands_bp = Blueprint('custom_commands', __name__)


@custom_commands_bp.route("/dashboard/<int:guild_id>/custom-commands")
@plugin_guard('custom_commands')
async def custom_commands(guild_id):
    current_user = get_current_user()

    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = (await Guild.get(str(guild.id))).dashboard.custom_commands

    return await render_template(
        "dashboard/plugins/custom_commands.html",
        user=current_user,
        guild=guild,
        data=config,
        commands=[c.model_dump() for c in config.commands],
    )
