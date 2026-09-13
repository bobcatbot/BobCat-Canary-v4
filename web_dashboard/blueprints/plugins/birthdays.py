from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild, Birthday
from ...utils import bearer_client, plugin_guard

birthdays_bp = Blueprint('birthdays', __name__)


@birthdays_bp.route("/dashboard/<int:guild_id>/birthdays")
@plugin_guard('birthdays')
async def birthdays(guild_id):
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    doc = await Guild.get(str(guild.id))
    config = doc.dashboard.birthdays

    # Pulled straight from the registered commands (see @v.gated_command in
    # cogs/system/K birthdays.py) so the list and its descriptions can't
    # drift out of sync with the actual commands.
    commands = [
        {"name": cmd.qualified_name, "description": cmd.description}
        for cmd in v.gated_commands_for("birthdays")
    ]

    return await render_template(
        "dashboard/plugins/birthdays.html",
        user=current_user,
        guild=guild,
        data=config,
        commands=commands,
        disabled_commands=doc.settings.disabled_commands,
    )