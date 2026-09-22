import traceback
from datetime import datetime

from quart import Blueprint, flash, redirect, render_template, request, session, url_for
from zenora import APIClient

from ..config import BOT_TOKEN, CLIENT_SECRET, OAUTH_URL, REDIRECT_URI
from ..utils import bearer_client, SessionUser

auth_bp = Blueprint('auth', __name__)

_api_client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)

@auth_bp.route("/oauth/login")
async def login():
    return redirect(OAUTH_URL)

@auth_bp.route("/oauth/logout")
async def logout():
    session.pop("token", None)
    session.pop("user", None)
    await flash("Logged you out...", "log-out")
    return redirect(url_for("web.index"))

@auth_bp.route("/oauth/callback")
async def oauth_callback():
    # Bot-install completion (from dashboard_home's "Setup" redirect) rides
    # the same registered redirect_uri as login, distinguished by `state`
    # (the guild_id it was sent for). There's no identify-scoped code to
    # exchange here - the bot's already been added by the time Discord
    # redirects back - so just send them to that guild's dashboard, which
    # creates the config doc if on_guild_join hasn't landed yet.
    guild_id = request.args.get("state")
    if guild_id and guild_id.isdigit():
        await flash("Bot added! Setting up your server...", "log-in")
        return redirect(url_for("dashboard.dashboard_home", guild_id=int(guild_id)))

    try:
        code = request.args.get("code")
        token = _api_client.oauth.get_access_token(code, REDIRECT_URI).access_token
        session["token"] = token
        session["lastSignedIn"] = datetime.now()

        user = bearer_client().get_current_user()

        # Store the user in the session, so no request has to ask Discord who is signed in
        session["user"] = SessionUser.from_zenora(user).to_session()

        await flash(f'Logged in as {user.username}#{user.discriminator} !', 'log-in')

        redirect_url = session.pop('redirect', url_for("web.index"))
        session.pop('_flashes', None)
        return await render_template("oauth_callback.html", redirect_url=redirect_url)
    except Exception:
        traceback.print_exc()
        await flash('Oh no, something went wrong during authentication', 'login-error')
        return redirect(url_for("web.index"))