from dashboard.index import bearer_client, OAUTH_URL
from flask import Blueprint, render_template, session

web = Blueprint('web', __name__)

@web.route("/")
async def index():
  if not "token" in session:
    return render_template("index.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("index.html", user=current_user)

@web.route("/plugins/management")
async def web_token_management():
  if not "token" in session:
    return render_template("web-plugins/management.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("web-plugins/management.html", user=current_user)
  
@web.route("/plugins/utilities")
async def web_token_utilities():
  if not "token" in session:
    return render_template("web-plugins/utilities.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("web-plugins/utilities.html", user=current_user)

@web.route("/plugins/engagement-and-fun")
async def web_token_engagement():
  if not "token" in session:
    return render_template("web-plugins/engagement-and-fun.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("web-plugins/engagement-and-fun.html", user=current_user)

@web.route('/contact-us') # update
async def contactUs():
  if not "token" in session:
    return render_template("contact-us.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("contact-us.html", user=current_user)

@web.route('/thanks')
async def thanks():
  if not "token" in session:
    return render_template("thanks.html", logInWithDiscord=OAUTH_URL)
  
  current_user = bearer_client().get_current_user()
  return render_template("thanks.html", user=current_user)

@web.route('/terms')
async def terms():
  if not "token" in session:
    return render_template('terms.html', logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template('terms.html', user=current_user)

"""@web.route("/privacy")
async def privacy():
  if not "token" in session:
    return render_template('privacy.html', logInWithDiscord=OAUTH_URL)
  
  current_user = bearer_client().get_current_user()
  return render_template('privacy.html', user=current_user)"""



# =================================================================================
from dashboard.index import bot
from flask import jsonify

@web.route("/status")
async def status():
  if not "token" in session:
    shards = await fetch_shard_data()
    return render_template("status.html", logInWithDiscord=OAUTH_URL, shards=shards)
  
  current_user = bearer_client().get_current_user()
  
  shards = await fetch_shard_data(current_user)

  return render_template("status.html", user=current_user, shards=shards)

@web.route("/api/shard_status", methods=["GET"])
async def api_shard_status():
  try:
    current_user = bearer_client().get_current_user()
  except:
    current_user = None

  # Fetch shard data
  api_shards = await fetch_shard_data(current_user)
  # Return as JSON
  return jsonify(api_shards)

async def fetch_shard_data(user=None):
  shard_list = []
  user_in_guilds = []

  for shard_id, shard in bot.shards.items():
    if not shard.is_closed() and not shard.is_ws_ratelimited():
      emoji, state, color = "", "Ready", "green"  # No emoji, ready and functioning
    elif not shard.is_closed() and shard.is_ws_ratelimited():
      emoji, state, color = "C", "Connected", "green"  # Bot connected, but some commands may not work
    elif not shard.is_closed() and shard.is_ws_ratelimited():
      emoji, state, color = "P", "Partially connected", "orange"  # Some servers might be unresponsive
    elif shard.is_closed() and not shard.is_ws_ratelimited():
      emoji, state, color = "L", "Logging in", "orange"  # Bot is logging in to Discord
    elif shard.is_closed() and shard.is_ws_ratelimited():
      emoji, state, color = "Q", "Offline, waiting turn", "red"  # Bot is offline and waiting
    else:
      emoji, state, color = "🔥", "Offline, not reconnecting", "red"  # Offline and not reconnecting

    if user:
      for guild in [g for g in bot.guilds if g.shard_id == shard_id]:
        member = guild.get_member(user.id)
        if member:
          user_in_guilds.append(guild.name)
    
    shard_list.append({
      "id": shard_id,
      "emoji": emoji,
      "state": state,
      "color": color,
      "latency": f"{shard.latency * 1000:.0f}",
      "servers": len([g for g in bot.guilds if g.shard_id == shard_id]),
      "user_in_guilds": user_in_guilds,
    })
  return shard_list