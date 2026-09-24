from quart import Blueprint, redirect, render_template

from modules import bot as v
from modules.models import Guild, PersonalInvite
from ...utils import get_current_user, plugin_guard

invite_bp = Blueprint('invite', __name__)

# Short link handed out by /invites. Only codes the bot created are honoured, so this
# can't be used as an open redirect to arbitrary discord.gg invites.
@invite_bp.route("/i/<code>")
async def personal_invite(code):
    if await PersonalInvite.find_one(PersonalInvite.code == code) is None:
        return await render_template("error/404.html"), 404
    return redirect(f"https://discord.gg/{code}")


@invite_bp.route("/dashboard/<int:guild_id>/invite-tracker")
@plugin_guard('invite_tracker')
async def invite_tracker(guild_id):
    current_user = get_current_user()

    guild = v.get_client(guild_id).get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    config = (await Guild.get(str(guild.id))).dashboard.invite_tracker

    return await render_template(
        "dashboard/plugins/invite_tracker.html",
        user=current_user,
        guild=guild,
        data=config,
    )