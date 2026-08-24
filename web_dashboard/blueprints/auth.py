from datetime import datetime

from quart import Blueprint, flash, redirect, render_template, request, session, url_for
from zenora import APIClient

from ..config import BOT_TOKEN, CLIENT_SECRET, OAUTH_URL, REDIRECT_URI
from ..utils import bearer_client

auth_bp = Blueprint('auth', __name__)

_api_client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)

@auth_bp.route("/oauth/login")
async def login():
    return redirect(OAUTH_URL)

@auth_bp.route("/oauth/logout")
async def logout():
    session.pop("token", None)
    session.pop("user", None)
    session.pop("cached_guilds", None)
    await flash("Logged you out...", "log-out")
    return redirect(url_for("web.index"))

@auth_bp.route("/oauth/callback")
async def oauth_callback():
    try:
        code = request.args.get("code")
        token = _api_client.oauth.get_access_token(code, REDIRECT_URI).access_token
        session["token"] = token
        session["lastSignedIn"] = datetime.now()

        user = bearer_client().get_current_user()

        # Store the basic user information in the session after getting the user:
        session["user"] = {
            "id": user.id,
            "username": user.username,
            "avatar_url": user.avatar_url,
        }

        await flash(f'Logged in as {user.username}#{user.discriminator} !', 'log-in')

        redirect_url = session.pop('redirect', url_for("web.index"))
        session.pop('_flashes', None)
        return await render_template("oauth_callback.html", redirect_url=redirect_url)
    except Exception as e:
        print(e)
        await flash('Oh no, something went wrong during authentication', 'login-error')
        return redirect(url_for("web.index"))