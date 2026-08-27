from quart import Blueprint, render_template
from modules import bot as v
from modules.models import Guild
from ...utils import bearer_client, login_required, premium_module

welcome_bp = Blueprint('welcome', __name__)

@welcome_bp.route("/dashboard/<int:guild_id>/welcome")
@login_required
async def welcome(guild_id):
    await premium_module(guild_id, 'welcome')

    current_user = bearer_client().get_current_user()

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.welcome
    
    return await render_template(
        "dashboard/plugins/welcome.html",
        user=current_user,
        guild=guild,
        data=config
    )