from quart import Blueprint, render_template

from modules import bot as v
from modules.models import Guild
from ...utils import get_current_user, plugin_guard

sticky_messages_bp = Blueprint('sticky_messages', __name__)


@sticky_messages_bp.route("/dashboard/<int:guild_id>/sticky-messages")
@plugin_guard('sticky_messages')
async def sticky_messages(guild_id):
    current_user = get_current_user()

    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = (await Guild.get(str(guild.id))).dashboard.sticky_messages

    return await render_template(
        "dashboard/plugins/sticky_messages.html",
        user=current_user,
        guild=guild,
        data=config,
        messages=[m.model_dump() for m in config.messages],
        channel_names={str(c.id): c.name for c in guild.text_channels},
    )
