import os, discord, json, logging, pymongo, pytz, stripe
from threading import Thread
from datetime import datetime, timezone
from zenora import BadTokenError, APIClient
from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify
from modules import bot as v
from .plugins import fetch_plugins
from .consts import premium_faqs, premium_types, langs, tz
from .config import URL_BASE, PY_ENV, BOT_TOKEN, CLIENT_ID, CLIENT_SECRET, OAUTH_URL, REDIRECT_URI, WEBHOOK_PREM, mongoURI_db, mongo_cdn, stripe_config

app = Flask(__name__)

app.config["SECRET_KEY"] = "mysecret"
app.config['DEBUG'] = True
app.config['TEMPLATES_AUTO_RELOAD'] = True  # Force template reload
app.config["STRIPE_PUBLIC_KEY"] = stripe_config["PUBLIC_KEY"]
app.config["STRIPE_SECRET_KEY"] = stripe_config["SECRET_KEY"]
app.config["STRIPE_WEBHOOK_KEY"] = stripe_config["WH_KEY"]

bot = v.client
client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)

stripe.api_key = app.config["STRIPE_SECRET_KEY"]

logging.getLogger('werkzeug').setLevel(logging.ERROR)

MongoClientBot = pymongo.MongoClient(mongoURI_db)
db = MongoClientBot['Bot']['Bot']

def bearer_client():
  bearer_client = APIClient(session.get("token"), bearer=True)
  return bearer_client.users

def get_server_config(guild: int, all=False):
  try:
    guildID = guild.id
  except AttributeError:
    guildID = guild
  
  data: dict = db.find_one({"_id": str(guildID)})
  if data is None:
    return None
  
  if all:
    return data
  return data["Bot"]

def get_dash_config(guild: int):
  try:
    id = str(guild.id)
  except AttributeError:
    id = str(guild)

  data = db.find_one({'_id': id})
  if data is None:
    return None
  
  return data["Dash"]

def update_config(guild_id: int, key: str, value):
  try:
    id = str(guild_id.id)
  except AttributeError:
    id = str(guild_id)

  d = db.update_one(
    { '_id': id },
    { '$set': { key: value } }
  )
  if d:
    return True
  return False

def uuid_(length=8, strCase='upper/lower/nums/special'):
    import random

    nums = "0123456789"
    uppers = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lowers = "abcdefghijklmnopqrstuvwxyz"
    special = "!@#$%^&*()_+-=[]{};:,./<>?"
    
    combination = (strCase
        .replace("/", '')
        .replace("upper", uppers)
        .replace("lower", lowers)
        .replace("nums", nums)
        .replace("special", special)
    )
    code = random.choices(combination, k=length)
    return "".join(code)

# TODO: 403, 410, 500
@app.errorhandler(404)
async def redirect_error_page(e):
  return render_template('error/404.html'), 404

@app.template_filter('titlecase')
def titlecase(s):
  return f"{s}".capitalize()

## Main web ##
@app.route("/")
async def index():
  if not "token" in session:
    return render_template("index.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("index.html", user=current_user)

@app.route("/plugins/management")
async def web_token_management():
  if not "token" in session:
    return render_template("web-plugins/management.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("web-plugins/management.html", user=current_user)
  
@app.route("/plugins/utilities")
async def web_token_utilities():
  if not "token" in session:
    return render_template("web-plugins/utilities.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("web-plugins/utilities.html", user=current_user)

@app.route("/plugins/engagement-and-fun")
async def web_token_engagement():
  if not "token" in session:
    return render_template("web-plugins/engagement-and-fun.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("web-plugins/engagement-and-fun.html", user=current_user)

@app.route('/contact-us') # update
async def contactUs():
  if not "token" in session:
    return render_template("contact-us.html", logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template("contact-us.html", user=current_user)

@app.route('/thanks')
async def thanks():
  if not "token" in session:
    return render_template("thanks.html", logInWithDiscord=OAUTH_URL)
  
  current_user = bearer_client().get_current_user()
  return render_template("thanks.html", user=current_user)

@app.route('/terms')
async def terms():
  if not "token" in session:
    return render_template('terms.html', logInWithDiscord=OAUTH_URL)

  current_user = bearer_client().get_current_user()
  return render_template('terms.html', user=current_user)

"""@app.route("/privacy")
async def privacy():
  if not "token" in session:
    return render_template('privacy.html', logInWithDiscord=OAUTH_URL)
  
  current_user = bearer_client().get_current_user()
  return render_template('privacy.html', user=current_user)"""

## Bot ##
@app.route("/status")
async def status():
  if not "token" in session:
    shards = await fetch_shard_data()
    return render_template("status.html", logInWithDiscord=OAUTH_URL, shards=shards)
  
  current_user = bearer_client().get_current_user()
  
  shards = await fetch_shard_data(current_user)

  return render_template("status.html", user=current_user, shards=shards)

@app.route("/api/shard_status", methods=["GET"])
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

## Dashboard ##
@app.context_processor
def utility_processor():
  def plugs(guild):
    """Retrieve plugins based on guild"""
    dash_data = get_dash_config(guild)
    plugins_list = fetch_plugins(dash_data)
    return plugins_list
  
  def get_plugin(guild, plugin):
    plug_list = plugs(guild)
    for _item, _plugin in plug_list:
      if _item != plugin:
        continue
      return _plugin

  def GetUserGuilds():
    g = []
    user_guilds = bearer_client().get_my_guilds()
    guild_ids = [gID.id for gID in bot.guilds]
    for _guild in user_guilds:
      if _guild.id in guild_ids:
        _guild.active = True
        g.append(_guild)
    return g
  
  def server_config(guild):
    return get_server_config(guild, True)

  def notifications(guild):
    read_notifis = []
    unread_notifis = []
    for notif in server_config(guild)['notifications']:
      if notif['read'] == True:
        read_notifis.append(notif)
      else:
        unread_notifis.append(notif)
    
    def sortFn(notif):
      return notif['created_at']['timestamp']
    read_notifis.sort(key=sortFn)
    unread_notifis.sort(key=sortFn)
    unread_notifis.reverse()
    return {'read': read_notifis, 'unread': unread_notifis[:5], 'unread_count': len(unread_notifis)}

  return {'plugins': plugs, 'get_plugin': get_plugin, 'guilds': GetUserGuilds,  'guild_models': guild_models, 'server_config': server_config, 'notifications': notifications}

## Auth ##
@app.errorhandler(BadTokenError)
def handle_bad_token_error(e):
  # Remove the token from the session
  session.pop("token", None)
  # Redirect to the OAuth login route
  return redirect(OAUTH_URL)

@app.route("/oauth/login")
async def login():  
  return redirect(OAUTH_URL)
  
@app.route("/oauth/logout")
async def logout():
  session.pop("token")
  flash("Logged you out...", "log-out")
  return redirect(url_for("index"))

@app.route("/oauth/callback")
async def oauth_callback():
  try:
    code = request.args.get("code")
    token = client.oauth.get_access_token(code, REDIRECT_URI).access_token
    session["token"] = token
    session["lastSignedIn"] = datetime.now()

    user = bearer_client().get_current_user()
    flash(f'Logged in as {user.username}#{user.discriminator} !', 'log-in')

    redirect_url = session.get('redirect', url_for("index"))
    session.pop('redirect')
    session.pop('_flashes', None)
    return redirect(redirect_url)
  except:
    flash('Oh no, something went wrong during authentication', 'login-error')
    return redirect(url_for("index"))

def login_required(f):
  from functools import wraps
  
  @wraps(f)
  async def decorated_function(*args, **kwargs):
    if 'token' not in session:
      session['redirect'] = request.url
      return render_template("login.html", logInWithDiscord=url_for('login'))
    return await f(*args, **kwargs)
  return decorated_function

class PremiumModuleError(Exception):
  pass
def premium_module(guild, module):
  # Fetch server and module configurations
  data = get_server_config(guild, True)

  plug = json.load(open(f'dashboard/plugin_list.json', 'r', encoding='utf-8'))[module]

  # Check if the module requires premium and the guild doesn't have premium
  if plug.get('premium') and not data['premium']['status']:
    print(f"⛔ Wait, {module} is a premium module.", 'error')
    raise PremiumModuleError(f"Guild {guild} does not have access to {module}.")
  return data

@app.errorhandler(PremiumModuleError)
def handle_premium_module_error(e):
  guild_id = request.view_args.get('guild_id')
  flash("You don't have access to this module", "PremiumModal")
  return redirect(url_for('dashboard_home', guild_id=guild_id))

## Leaderboard ##
@app.route("/leaderboard/<guild_id>", methods=['GET', 'POST'])
async def leaderboard_home(guild_id):
  lvl_config = get_dash_config(guild_id).get('leveling')

  # ✅ Public access check
  if not lvl_config['leaderboard'].get('public', False):
    if "token" not in session:
      flash('You are not allowed to view the leaderboard', 'error')
      return redirect(url_for('index'))
  
  current_user = None
  if "token" in session:
    try:
      current_user = bearer_client().get_current_user()
    except Exception:
      current_user = None

  guild = bot.get_guild(int(guild_id))


  # ✅ Public access check
  if not lvl_config['leaderboard'].get('public', False):
    if not current_user or guild.get_member(current_user.id):
      flash('You are not allowed to view the leaderboard', 'error')
      return redirect(url_for('index'))

  users = []
  lvl_users = get_server_config(guild).get('leveling')
  sorted_players = sorted(lvl_users.items(), key=lambda x: int(x[1]['lvl']), reverse=True)

  for idx, (player_id, data) in enumerate(sorted_players, start=1):    
    player = bot.get_user(int(player_id))
    data['msg_count'] = data.get('msg_count', 0)
    users.append((idx, (player, data)))

  # Determine guild permissions only if user is logged in
  gp = False
  if current_user:
    user = guild.get_member(current_user.id)
    if user:
      if user.guild_permissions.administrator:
        gp = { 'administrator': True, 'bot_master': False }
      else:
        config = get_server_config(guild.id, True)
        if config:
          roles = config['settings']
          bot_master = any(
            str(role.id) in roles['admin_roles'] or 
            str(role.id) in roles['bot_masters'] 
            for role in user.roles
          )
          if bot_master:
            gp = { 'administrator': False, 'bot_master': True }

  return render_template("dashboard/leaderboard.html", user=current_user, guild_permissions=gp, guild=guild, data=lvl_config, users=users)


## Forms ##
@app.route("/form/<int:guild_id>/<form_id>", methods=['GET', 'POST'])
@login_required
async def form(guild_id, form_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  server_config = get_server_config(guild, True).get('settings')

  if request.method == 'POST':
    data = request.get_json()
    
    forms = get_server_config(guild).get('forms')
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)

    form['responses'].append(data)
    update_config(guild, f'Bot.forms.{form_idx}.responses', form['responses'])

    channel = guild.get_channel(int(form['settings']['submission_channel']))
    async def send_message():
      submitted_at = datetime.fromisoformat(data['submitted_at'])
      embed = discord.Embed(
        title=f"{form['name']} (#{len(form['responses'])})", 
        color=0x5865F2, timestamp=submitted_at, 
      ) 

      for index, question in enumerate(form['questions']):
        embed.add_field(name=question['title'], value=data['answers'][index], inline=False)        

      embed.set_footer(text=f"User ID: {data['user']['id']}")
      msg = await channel.send(embed=embed)

      # thread on submission
      if form['settings']['options']['thread'] == True:
        await msg.create_thread(name=f"{form['name']} ({form['id']})")
      
      form_reactions = form['settings']['options']['reactions']
      if form_reactions['status'] == True and form_reactions['emojis']:
        for emoji in form_reactions['emojis']:
          await msg.add_reaction(emoji)

    bot.loop.create_task(send_message())
    return jsonify({ 'status': 200 })
  
  forms = get_server_config(guild).get('forms')

  for form in forms:
    if form['id'] != form_id:
      continue
    data = form

  return render_template("form.html", user=current_user, guild=guild, data=data)
@app.route("/form/<int:guild_id>/<form_id>/submissions", methods=['GET', 'POST', 'DELETE'])
@login_required
async def form_submissions(guild_id, form_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  user = guild.get_member(current_user.id)
  
  forms = get_server_config(guild).get('forms')

  if request.method == 'DELETE':
    res = request.get_json()
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)
    for response in form['responses']:
      if response['id'] != res['id']:
        continue
      form['responses'].remove(response)
      update_config(guild, f'Bot.forms.{form_idx}.responses', form['responses'])

    return jsonify({ 'status': 200 })

  for _form in forms:
    if _form['id'] != form_id:
      continue
    form = _form
  
  submission_viewers = form['settings'].get('submission_viewers', [])
  submission_managers = form['settings'].get('submission_managers', [])

  allowed_roles = set(submission_viewers) | set(submission_managers)
  user_role_ids = {str(role.id) for role in user.roles}

  if allowed_roles and not user_role_ids & allowed_roles:
    flash('You are not allowed to view the submissions', 'error')
    return redirect(url_for('index'))
  
  # Check if the user can manage submissions
  can_manage = any(str(role.id) in submission_managers for role in user.roles)

  return render_template("form_subs.html", user=current_user, guild=guild, form=form, can_manage=can_manage)

@app.route("/dashboard")
@login_required
async def guilds():
  guilds = []
  current_user = bearer_client().get_current_user()
  user_guilds = bearer_client().get_my_guilds()
  guild_ids = [gID.id for gID in bot.guilds]

  for guild in user_guilds:
    bot_master = False

    config = get_server_config(guild.id, True)
    if config:
      roles = config['settings']
      bot_master = any(
        str(role.id) in roles['admin_roles'] or 
        str(role.id) in roles['bot_masters'] 
        for role in bot.get_guild(guild.id).get_member(current_user.id).roles
      )
    #
    
    if (  # Owner, bot master
      guild.is_owner == True or
      bot_master == True or
      int(guild.permissions) & 0x8 == 0x8
    ):
      guild.perm = (
        "Owner" if guild.is_owner == True else
        "Bot Master" if bot_master == True else
        "Admin" if int(guild.permissions) & 0x8 == 0x8 else
        "Member"
      )
      guild.btn_name = "Go" if guild.id in guild_ids else "Setup"
      guild.color = "#5865F2" if guild.id in guild_ids else "#36393f"

      guilds.append(guild)

  guilds.sort(key=lambda x: x.btn_name == "Go", reverse=True)
  guilds.sort(key=lambda x: x.color == "#5865f2", reverse=True)
  return render_template("dashboard/guilds.html", user=current_user, guilds=guilds)

@app.route("/dashboard/<int:guild_id>")
@login_required
async def dashboard_home(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  session['guild_id'] = guild.id
  
  if guild is None:
    return redirect(f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={URL_BASE}/dashboard")
  
  return render_template("dashboard/dashboard.html", user=current_user, guild=guild)

@app.route("/dashboard/<int:guild_id>/settings")
@login_required
async def settings(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  data = get_server_config(guild, True).get('settings')
  return render_template("dashboard/settings.html", user=current_user, guild=guild, data=data, languages=langs, timezones=tz)


@app.route("/dashboard/<int:guild_id>/premium", methods=["GET", "POST"])
@login_required
async def premium(guild_id):
  import aiohttp
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  prem_data = get_server_config(guild, True).get('premium')
  
  if prem_data['status'] == False:
    return render_template("dashboard/premium/index.html", user=current_user, guild=guild, data=prem_data, faqs=premium_faqs, types=premium_types)
  
  createdAt_later = "Never"
  days_countdown = "0"
  if prem_data['plan'] == 'monthly':
    date = prem_data['subscribed_at'] #+ relativedelta(months=1)
    days_countdown = (date - datetime.now()).days
    createdAt_later = date.strftime("%B %d %Y")
  if prem_data['plan'] == 'yearly':
    date = prem_data['subscribed_at'] #+ relativedelta(years=1)
    days_countdown = (date - datetime.now()).days
    createdAt_later = date.strftime("%B %d %Y")
  
  user = bot.get_user(int(prem_data['user_id']))
  
  data = {
    'next_bill': createdAt_later,
    'countdown': days_countdown,
    'user': {
      'avatar': user.avatar.url,
      'name': user.name,
    },
  } | prem_data
  
  return render_template("dashboard/premium/manage.html", user=current_user, guild=guild, data=data, types=premium_types)

@app.route("/dashboard/<int:guild_id>/notifications", methods=["GET", "POST"])
@login_required
async def notifications(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  data = get_server_config(guild, True).get('notifications')

  if request.method == 'POST':
    res = request.get_json()
    for _notification in data:
      if _notification['id'] == res['id']:
        notif = _notification

    notif_idx = data.index(notif)
    res.pop('id')
    for key, val in res.items():
      update_config(guild.id, f'notifications.{notif_idx}.{key}', val)
    return jsonify({'status': 'success', 'message': 'Successfully updated notifications'})
  
  notifications_by_date = {}

  for notification in data:
    date = notification['created_at']['date']
    if not date in notifications_by_date:
      notifications_by_date[date] = []
    notifications_by_date[date].append(notification)
    notifications_by_date[date].sort(key=lambda x: x['created_at']['time'], reverse=True)

  notifications_by_date = dict(reversed(list(notifications_by_date.items())))
  
  return render_template("dashboard/notifications.html", user=current_user, guild=guild, config=data, data=notifications_by_date)

@app.route("/dashboard/<int:guild_id>/welcome")
@login_required
async def welcome(guild_id):
  premium_module(guild_id, 'welcome')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  data = get_dash_config(guild).get('welcome')
  return render_template("dashboard/plugins/welcome.html", user=current_user, guild=guild, data=data)

@app.route("/dashboard/<int:guild_id>/moderator")
@login_required
async def moderation(guild_id):
  premium_module(guild_id, 'moderation')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild).get('moderation')
  logs = dash_data['logging']
  return render_template("dashboard/plugins/moderation.html", user=current_user, guild=guild, data=dash_data, logging=logs)

@app.route("/dashboard/<int:guild_id>/verification", methods=['GET', 'POST', 'UPDATE', 'DELETE'])
@login_required
async def verify(guild_id):
  premium_module(guild_id, 'verification')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == 'POST':
    data = request.get_json()
    config = get_dash_config(guild)['verification']
    
    async def send_message():
      embed = discord.Embed.from_dict(data['embed'])
      
      style = {
        'secondary': discord.ButtonStyle.gray,
        'blurple': discord.ButtonStyle.blurple,
        'danger': discord.ButtonStyle.red,
        'success': discord.ButtonStyle.green,
      }[data['btn']['color']]

      view = discord.ui.View()
      view.add_item(discord.ui.Button(
        emoji=data['btn']['emoji'] if data['btn']['emoji'] else None, 
        label=data['btn']['title'], 
        style=style,
        custom_id='Verification'
      ))

      if config['message_published']:
        channel = guild.get_channel(int(config['channel']))
        msg = await channel.fetch_message(int(config['message_id']))
        await msg.edit(embed=embed, view=view)
        return

      role = guild.get_role(int(config['role']))
      if not role:
        role = await guild.create_role(name='Verified', reason='Enabled verification system')
      
        update_config(guild, 'Dash.verification.role', role.id)

      channel = guild.get_channel(int(config['channel']))
      if not channel:
        channel = await guild.create_text_channel('verification', reason='Enabled verification system', overwrites={
          guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
          role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True,)
        })

        update_config(guild, 'Dash.verification.channel', channel.id)

      await channel.set_permissions(guild.default_role, overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=False))
      await channel.set_permissions(role, overwrite=discord.PermissionOverwrite(read_messages=False, send_messages=False))

      await guild.default_role.edit( # @everyone
        reason="Verification system enabled",
        permissions=discord.Permissions(read_messages=False,)
      )

      if role.id == int(config['role']):
        await role.edit(
          reason="Verification system enabled",
          permissions=discord.Permissions(read_messages=True)
        )
      
      msg = await channel.send(embed=embed, view=view)
      update_config(guild, 'Dash.verification.message_id', f'{msg.id}')
      update_config(guild, 'Dash.verification.message_published', True)
    bot.loop.create_task(send_message())

    return jsonify({'status': 'success', 'message': 'Successfully published verification message'})

  if request.method == 'DELETE':
    config = get_dash_config(guild)['verification']

    async def send_message():
      channel = guild.get_channel(int(config['channel']))
      msg = await channel.fetch_message(int(config['message_id']))
      await msg.delete()

      update_config(guild, 'Dash.verification.message_published', False)
    bot.loop.create_task(send_message())

    return jsonify({'status': 'success', 'message': 'Successfully deleted verification message'})
  
  if request.method == 'UPDATE':
    data = request.get_json()
    config = get_dash_config(guild)['verification']

    return jsonify({'status': 'success', 'message': 'Successfully updated verification message'})

  data = get_dash_config(guild).get('verification')
  return render_template("dashboard/plugins/verification.html", user=current_user, guild=guild, data=data)

"""Embed Messages TBD
# @app.route("/dashboard/<int:guild_id>/embeds")
@login_required
async def embed_messages(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  data = get_dash_config(guild).get('embeds')
  return render_template("dashboard/plugins/embeds/em_index.html", user=current_user, guild=guild, data=data)
# @app.route("/dashboard/<int:guild_id>/embeds/creation", methods=['GET', 'POST'])
@login_required
async def embed_messages_create(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == 'POST':
    data = request.form
    print(data)
    return
  
  data = get_dash_config(guild).get('embeds')
  return render_template("dashboard/plugins/embeds/em_create.html", user=current_user, guild=guild, data=data)"""

@app.route("/dashboard/<int:guild_id>/starboard")
@login_required
async def starboard(guild_id):
  premium_module(guild_id, 'starboard')

  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild.id).get('starboard')
  return render_template("dashboard/plugins/starboard.html", user=current_user, guild=guild, data=dash_data)

## Forms ##
@app.route("/dashboard/<int:guild_id>/forms")
@login_required
async def forms(guild_id):
  premium_module(guild_id, 'forms')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  data = get_server_config(guild).get('forms')
  plugin = get_dash_config(guild).get('forms')
  return render_template("dashboard/plugins/forms/form_index.html", user=current_user, guild=guild, data=data, plugin=plugin)
@app.route("/dashboard/<int:guild_id>/forms/creation", methods=['GET', 'POST'])
@login_required
async def forms_create(guild_id):
  premium_module(guild_id, 'forms')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  if request.method == 'POST':
    data = request.get_json()

    def generateId(length=8):
      import random, string
      letters = string.ascii_letters + string.digits
      return ''.join(random.choice(letters) for i in range(length))

    data['id'] = generateId(12)

    forms = get_server_config(guild).get('forms')

    for key, val in data.items():
      update_config(guild.id, f'Bot.forms.{len(forms)}.{key}', val)
    
    flash(f"Successfully created form {data['id']}", 'success')
    return jsonify({'status': 'success', 'message': f"Successfully created form {data['id']}"})
  
  return render_template("dashboard/plugins/forms/form_create.html", user=current_user, guild=guild)
@app.route("/dashboard/<int:guild_id>/forms/<form_id>/edit", methods=['GET', 'POST', 'DELETE'])
@login_required
async def forms_edit(guild_id, form_id):
  premium_module(guild_id, 'forms')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  if request.method == 'POST':
    data = request.get_json()

    forms = get_server_config(guild).get('forms')
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)
    
    for key, val in data.items():
      update_config(guild.id, f'Bot.forms.{form_idx}.{key}', val)

    return jsonify({'status': 'success', 'message': 'Successfully updated form'})
  
  if request.method == 'DELETE':
    forms = get_server_config(guild).get('forms')
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)
    forms.pop(form_idx)
    update_config(guild.id, 'Bot.forms', forms)
    return jsonify({'status': 'success', 'message': 'Successfully deleted form'})

  forms = get_server_config(guild).get('forms')

  for form in forms:
    if form['id'] != form_id:
      continue
    data = form
  
  emojis = guild_models(guild).emojis
  return render_template("dashboard/plugins/forms/form_edit.html", user=current_user, guild=guild, data=data, emojis=emojis)

## Temporary Channels ##
@app.route("/dashboard/<int:guild_id>/temporary-channels", methods=['GET'])
@login_required
async def temporary_channels(guild_id):
  premium_module(guild_id, 'temporary_channels')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  tempchan_data = get_dash_config(guild.id).get('temporary_channels')
  return render_template("dashboard/plugins/temporary_channels/tc_index.html", user=current_user, guild=guild, data=tempchan_data)
@app.route("/dashboard/<int:guild_id>/temporary-channels/creation", methods=['GET', 'POST'])
@login_required
async def temporary_channels_create(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == 'POST':
    data = request.get_json()

    def generateId(length=8):
      import random, string
      letters = string.ascii_letters + string.digits
      return ''.join(random.choice(letters) for i in range(length))

    data['id'] = generateId(12)

    async def runDiscordTask():
      if data['sync_hub_category'] == True:
        if data['category_id'] == '':
          # create category
          category = await guild.create_category_channel(data['hub_name'], reason=f"Temporary category for hub {data['id']}")
          data['category_id'] = category.id
        else:
          category = await guild.fetch_channel(data['category_id'])
          data['category_id'] = category.id
      else:
        category = guild

      vc = await category.create_voice_channel(data['hub_name'], reason=f"Temporary voice channel for hub {data['id']}")
      data['channel_id'] = vc.id
      
      tempchan_data = get_dash_config(guild.id).get('temporary_channels')['hubs']
      
      for key, val in data.items():
        update_config(guild.id, f'Dash.temporary_channels.hubs.{len(tempchan_data)}.{key}', val)
      
      return vc
    bot.loop.create_task(runDiscordTask())

    flash(f"Successfully created hub {data['id']}", 'success')
    return jsonify({'status': 'success', 'message': f"Successfully created hub {data['id']}"})
  
  return render_template("dashboard/plugins/temporary_channels/tc_create.html", user=current_user, guild=guild)
@app.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/edition", methods=['GET', 'POST', 'DELETE'])
@login_required
async def temporary_channels_edit(guild_id, hub_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  tempchan_data = get_dash_config(guild.id).get('temporary_channels')['hubs']

  for _hub in tempchan_data:
    if _hub['id'] != hub_id:
      continue
    hub = _hub
  
  if request.method == 'POST':
    data = request.get_json()

    hub_idx = tempchan_data.index(hub)
    
    async def runDiscordTask():
      if data['sync_hub_category'] == True:
        if data['category_id'] != '':
          category = await guild.fetch_channel(data['category_id'])
          data['category_id'] = category.id

      channel = await guild.fetch_channel(hub['channel_id'])
      await channel.edit(name=data['hub_name'], category=category)
      
      for key, val in data.items():
        update_config(guild.id, f'Dash.temporary_channels.hubs.{hub_idx}.{key}', val)
    
    bot.loop.create_task(runDiscordTask())
    flash(f"Successfully updated hub {hub['id']}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully updated hub'})
  
  return render_template("dashboard/plugins/temporary_channels/tc_edit.html", user=current_user, guild=guild, data=hub)
@app.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/delete", methods=['DELETE'])
async def temporary_channels_delete(guild_id, hub_id):
  guild = bot.get_guild(guild_id)

  tempchan_data = get_dash_config(guild.id).get('temporary_channels')['hubs']

  for hub in tempchan_data:
    if hub['id'] != hub_id:
      continue
    data = hub
  
  async def runDiscordTask():
    await bot.get_channel(data['channel_id']).delete()

    if data['sync_hub_category'] == True:
      if data['category_id'] != '':
        await bot.get_channel(data['category_id']).delete()

    tempchan_idx = tempchan_data.index(data)
    tempchan_data.pop(tempchan_idx)
    update_config(guild.id, 'Dash.temporary_channels.hubs', tempchan_data)
    return
  bot.loop.create_task(runDiscordTask())

  flash(f"Successfully deleted hub {data['id']}", 'success')
  return jsonify({'status': 'success', 'message': 'Successfully deleted hub'})

## Ticketing ##
@app.route("/dashboard/<int:guild_id>/ticketing")
@login_required
async def ticketing(guild_id):
  premium_module(guild_id, 'ticketing')
  
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild.id).get('ticketing')
  return render_template("dashboard/plugins/ticketing/ticketing_index.html", user=current_user, guild=guild, data=dash_data)
@app.route("/dashboard/<int:guild_id>/ticketing/creation", methods=['GET', 'POST'])
@login_required
async def ticketing_create(guild_id):
  premium_module(guild_id, 'ticketing')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == "POST":
    data = request.get_json()

    def generateId(length=8):
      import random, string
      letters = string.ascii_letters + string.digits
      return ''.join(random.choice(letters) for i in range(length))

    data['id'] = generateId(12)

    async def runDiscordTask():
      ticketing_data = get_dash_config(guild.id).get('ticketing')['pannels']

      for key, val in data.items():
        # print(guild.id, f'Dash.ticketing.pannels.{len(ticketing_data)}.{key}', val)
        update_config(guild.id, f'Dash.ticketing.pannels.{len(ticketing_data)}.{key}', val)

      pmEmbed = discord.Embed(
        title=data['pannel_message.embed.title'],
        description=data['pannel_message.embed.description'],
        color=data['pannel_message.embed.color']
      )

      view = discord.ui.View()
      view.add_item(discord.ui.Button(
        emoji=data['pannel_button.emoji'],
        label=data['pannel_button.label'],
        style=getattr(discord.ButtonStyle, data['pannel_button.style']),
        custom_id='create_ticket'
      ))

      channel = guild.get_channel(int(data['channel_id']))
      msg = await channel.send(embed=pmEmbed, view=view)

      update_config(guild.id, f'Dash.ticketing.pannels.{len(ticketing_data)}.pannel_message_id', str(msg.id))
      return
    bot.loop.create_task(runDiscordTask())
    flash(f"Successfully created ticket pannel {data['id']}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully created ticket'})
  
  return render_template("dashboard/plugins/ticketing/ticketing_create.html", user=current_user, guild=guild)
@app.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/edition", methods=['GET', 'POST'])
@login_required
async def ticketing_edit(guild_id, ticket_id):
  premium_module(guild_id, 'ticketing')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  ticket_data = get_dash_config(guild.id).get('ticketing')['pannels']

  for ticket in ticket_data:
    if ticket['id'] != ticket_id:
      continue
    tk_data = ticket
  
  ticket_idx = ticket_data.index(tk_data)

  if request.method == 'POST':
    data = request.get_json()
    
    async def runDiscordTask():
      pannel_message = guild.get_channel(int(tk_data['channel_id'])).get_partial_message(int(tk_data['pannel_message_id']))
      
      pmEmbed = discord.Embed(
        title=data.get('pannel_message.embed.title', tk_data['pannel_message']['embed']['title']),
        description=data.get('pannel_message.embed.description', tk_data['pannel_message']['embed']['description']),
        color=data.get('pannel_message.embed.color', tk_data['pannel_message']['embed']['color'])
      )
      
      view = discord.ui.View()
      view.add_item(discord.ui.Button(
        emoji=data.get('pannel_button.emoji', tk_data['pannel_button']['emoji']),
        label=data.get('pannel_button.label', tk_data['pannel_button']['label']),
        style=getattr(discord.ButtonStyle, data.get('pannel_button.style', tk_data['pannel_button']['style'])),
        custom_id='create_ticket'
      ))
      await pannel_message.edit(embed=pmEmbed, view=view)

      for key, val in data.items():
        update_config(guild.id, f'Dash.ticketing.pannels.{ticket_idx}.{key}', val)
      return
    bot.loop.create_task(runDiscordTask())

    flash(f"Successfully updated ticket pannel {ticket_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully updated ticket'})
  
  return render_template("dashboard/plugins/ticketing/ticketing_edit.html", user=current_user, guild=guild, data=tk_data)
@app.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/delete", methods=['DELETE'])
async def ticketing_delete(guild_id, ticket_id):
  guild = bot.get_guild(guild_id)

  ticket_data = get_dash_config(guild.id).get('ticketing')['pannels']

  for ticket in ticket_data:
    if ticket['id'] != ticket_id:
      continue
    data = ticket

  async def runDiscordTask():
    pannel_message = guild.get_channel(int(data['channel_id'])).get_partial_message(int(data['pannel_message_id']))
    await pannel_message.delete()
    
    ticket_data.pop(ticket_data.index(data))
    update_config(guild.id, 'Dash.ticketing.pannels', ticket_data)
  bot.loop.create_task(runDiscordTask())

  flash(f"Successfully deleted ticket pannel {ticket_id}", 'success')
  return jsonify({'status': 'success', 'message': 'Successfully deleted ticket pannel'})

## Leveling ##
@app.route("/dashboard/<int:guild_id>/leveling")
@login_required
async def levelling(guild_id):
  premium_module(guild_id, 'leveling')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild.id).get('leveling')

  mongoRankCards = pymongo.MongoClient(mongo_cdn)['RankCards']['Cards']
  
  default_cards = [
    { "card": card['card'], "bar_bg": card["bar_bg"], "bar_fill": card["bar_fill"], "bar_indent_left": card["bar_indent_left"], "bar_width": card["bar_width"] }
    for card in mongoRankCards.find({"theme": "default"}).sort("theme", pymongo.ASCENDING)
  ]
  fun_cards = [
    { "card": card['card'], "bar_bg": card["bar_bg"], "bar_fill": card["bar_fill"], "bar_indent_left": card["bar_indent_left"], "bar_width": card["bar_width"] }
    for card in mongoRankCards.find({"theme": "bobcat"}).sort("theme", pymongo.ASCENDING)
  ]
  cards = { 'all': default_cards + fun_cards, 'default': default_cards, 'cards': fun_cards }
  return render_template("dashboard/plugins/leveling.html", user=current_user, guild=guild, data=dash_data, server_cards=cards)

@app.route("/lvl-cards", methods=['POST'])
async def lvl_cards():
  mongoRankCards = pymongo.MongoClient(mongo_cdn)['RankCards']['Cards']
  
  default_cards = [
    { "card": card['card'], "bar_bg": card["bar_bg"], "bar_fill": card["bar_fill"], "bar_indent_left": card["bar_indent_left"], "bar_width": card["bar_width"] }
    for card in mongoRankCards.find({"theme": "default"}).sort("theme", pymongo.ASCENDING)
  ]
  fun_cards = [
    { "card": card['card'], "bar_bg": card["bar_bg"], "bar_fill": card["bar_fill"], "bar_indent_left": card["bar_indent_left"], "bar_width": card["bar_width"] }
    for card in mongoRankCards.find({"theme": "bobcat"}).sort("theme", pymongo.ASCENDING)
  ]
  cards = { 'all': default_cards + fun_cards, 'default': default_cards, 'cards': fun_cards }
  return jsonify(cards)

## Birthdays ##
@app.route("/dashboard/<int:guild_id>/birthdays")
@login_required
async def birthdays(guild_id):
  premium_module(guild_id, 'birthdays')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild.id).get('birthdays')
  return render_template("dashboard/plugins/birthdays.html", user=current_user, guild=guild, data=dash_data)

## Giveaways ##
@app.route("/dashboard/<int:guild_id>/giveaways")
@login_required
async def giveaways(guild_id):
  premium_module(guild_id, 'giveaway')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  plugin = get_dash_config(guild.id).get('giveaway')

  data = get_server_config(guild)['giveaways']
  return render_template("dashboard/plugins/giveaways/gway_index.html", user=current_user, guild=guild, config=plugin, data=data)
@app.route("/dashboard/<int:guild_id>/giveaways/creation", methods=['GET', 'POST'])
@login_required
async def giveaways_creation(guild_id):
  premium_module(guild_id, 'giveaway')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  gways = get_server_config(guild)['giveaways']

  if request.method == 'POST':
    data = request.get_json()

    uuid = uuid_(length=12, strCase="upper/lower/nums")

    channel = guild.get_channel(int(data['channel_id']))

    sdata = {
      'id': uuid, 'guild': guild.id, 'name': data['name'], 'status': 'Ongoing',  'channel': { 'id': channel.id, 'name': channel.name }, 'message': '', 'author': current_user.id, 'time': { 'epoch': data['time.epoch'], 'timestamp': data['time.timestamp'] }, 'prize': data['prize'], 
      'winners': data['winners'],
      'givexp': { 'enabled': data.get('givexp.enabled', False), 'amount': data.get('givexp.amount', 0) },
      'givecoins': { 'enabled': data.get('givecoins.enabled', False), 'amount': data.get('givecoins.amount', 0) },
      'gwinners': [], 'participants': [], 'embed_title': data['embed.title'], 'embed_desc': data['embed.desc'],
    }

    if data['button'] == 'save':
      sdata['status'] = 'Draft'
      # only update the database
      update_config(guild.id, f'Bot.giveaways.{len(gways)}', sdata) 
      
      flash('Giveaway saved successfully!', 'success')
      return jsonify({'status': 'success', 'message': 'Giveaway saved successfully!'})

    if data['button'] == 'publish':
      # create giveaway to discord
      async def create_giveaway():
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(emoji="🎉", style=discord.ButtonStyle.blurple, custom_id="JoinGiveaway"))

        embed = discord.Embed(title=sdata['embed_title'], description=sdata['embed_desc'], color=discord.Color.embed_background())
        embed.add_field(name="Ends", value=f"<t:{int(sdata['time']['epoch'])}:R> (<t:{int(sdata['time']['epoch'])}:f>)", inline=False)
        embed.add_field(name="Hosted by", value=f"<@{current_user.id}>", inline=False)
        embed.add_field(name="Winners", value=f"**{sdata['winners']}**", inline=False)
        embed.add_field(name="Participants", value="**0**", inline=False)
        embed.set_footer(text="Click on the button below to participate!")

        msg = await channel.send(embed=embed, view=view)
        sdata['message'] = msg.id

        update_config(guild.id, f'Bot.giveaways.{len(gways)}', sdata)
      bot.loop.create_task(create_giveaway())      

      flash('Giveaway published successfully!', 'success')
      return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})

  return render_template("dashboard/plugins/giveaways/gway_create.html", user=current_user, guild=guild)
@app.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/edition", methods=['GET', 'POST'])
@login_required
async def giveaways_edition(guild_id, gway_id):
  premium_module(guild_id, 'giveaway')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  gways = get_server_config(guild)['giveaways']

  for _gway in gways:
    if _gway['id'] != gway_id:
      continue
    data = _gway
  
  gway_idx = gways.index(data)

  if request.method == 'POST': # update only
    jdata = request.get_json()
    
    async def runDiscordTask():
      msg = await guild.get_channel(int(data['channel']['id'])).fetch_message(int(data['message']))

      embed = discord.Embed.to_dict(msg.embeds[0])
      embed['title'] = f"🎉 {jdata['prize']} 🎉"
      embed['description'] = jdata['embed.desc']
      embed['fields'][0]['value'] = f"<t:{int(jdata['time.epoch'])}:R> (<t:{int(jdata['time.epoch'])}:f>)"
      embed['fields'][2]['value'] = f"**{jdata['winners']}**"
      embed['fields'][3]['value'] = f"**{len(data['participants'])}**"

      await msg.edit(embed=discord.Embed.from_dict(embed))

      for key, value in jdata.items():
        print(guild.id, f'Bot.giveaways.{gway_idx}.{key}', value)
      return
    bot.loop.create_task(runDiscordTask())
    
    flash('Giveaway updated successfully!', 'success')
    return jsonify({'status': 'successs', 'message': 'Giveaway updated successfully!'})

  return render_template("dashboard/plugins/giveaways/gway_edit.html", user=current_user, guild=guild, data=data)

## Economy ##
@app.route("/dashboard/<int:guild_id>/economy")
@login_required
async def economy(guild_id):
  premium_module(guild_id, 'economy')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash = get_dash_config(guild.id).get('economy')
  dash_data = dash | {'num_items': len(dash['shop'])}
  return render_template("dashboard/plugins/economy.html", user=current_user, guild=guild, data=dash_data)


## Data ##
@app.route("/dashboard/<int:guild_id>/data/post", methods=["POST"])
async def data_post(guild_id):
  data = request.get_json().items()
  guild = bot.get_guild(guild_id)

  for key, val in data:
    if key == "EconomyUsers":
      server = get_server_config(guild)['economy']
      for user in server:
        server[user]['wallet'] = 0
        server[user]['bank'] = 0
        server[user]['bag'] = []
        update_config(guild, 'Bot.economy', server)
      break

    settings_configs = ['settings.language', 'settings.timezone', 'settings.color', 'settings.admin_roles', 'settings.bot_masters']
    if key in settings_configs:
      update_config(guild, key, val)
      break
    
    update_config(guild, "Dash." + key, val)
  return {'status': 'success', 'message': 'Successfully updated data'}

## Stripe ##
@app.route('/<int:guild_id>/stripe/pay/<type>')
def stripe_pay(guild_id, type):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  existing_customers = stripe.Customer.list(email=current_user.email).data
  if existing_customers:
    customer_id = existing_customers[0].id
  else:
    customer = stripe.Customer.create(
      email=current_user.email,
      name=current_user.username
    )
    customer_id = customer.id
  
  session = stripe.checkout.Session.create(
    payment_method_types=['card'],
    line_items=[{
      'price': premium_types[type]['price_id'],
      'quantity': 1,
    }],
    mode=premium_types[type]['mode'],
    customer=customer_id,
    success_url=url_for('premium', _external=True, guild_id=guild.id) + '?session_id={CHECKOUT_SESSION_ID}',
    cancel_url =url_for('premium', _external=True, guild_id=guild.id),
    metadata={
      "guild_id": guild.id,
      "user_id": current_user.id
    }
  )
  return {
    'checkout_session_id': session['id'], 
    'checkout_public_key': app.config['STRIPE_PUBLIC_KEY']
  }
@app.route('/stripe/portal/<customer_id>', methods=['POST'])
def stripe_portal(customer_id):
  data = db.find_one({'premium.customer': customer_id})
  if not data:
    return {'error': 'customer id not found'}, 400

  guild_id = data['_id']
  portal = stripe.billing_portal.Session.create(
    customer=customer_id,
    return_url=url_for('premium', _external=True, guild_id=guild_id),
  )
  return {
    'url': portal["url"],
    'checkout_public_key': app.config['STRIPE_PUBLIC_KEY']
  }
@app.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
  if request.content_length > 1024 * 1024:
    print('REQUEST TOO BIG')
    return "REQUEST TOO BIG", 400

  payload = request.get_data();
  sig_header = request.environ.get('HTTP_STRIPE_SIGNATURE')
  endpoint_secret = app.config["STRIPE_WEBHOOK_KEY"]

  event = None
  try:
    event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
  except ValueError:
    print('INVALID PAYLOAD')
    return {}, 400
  except stripe.error.SignatureVerificationError:
    print('INVALID SIGNATURE')
    return {}, 400

  # === Handle checkout.session.completed (New Payment or Subscription) ===
  if event['type'] == 'checkout.session.completed':
    session = event['data']['object']
    # print("✅ Checkout Session Completed:", session)

    if not session:
      return {}, 400

    line_items = stripe.checkout.Session.list_line_items(session['id'], limit=1)

    guild_id = session['metadata']['guild_id']
    user_id = session['metadata']['user_id']

    # Convert timestamp
    server_config = get_server_config(guild_id, True)['settings']
    tzu = pytz.timezone(server_config['timezone'])
    createdAt = datetime.fromtimestamp(session["created"], tz=timezone.utc).astimezone(tzu)

    # billing_history = [{
    #   "invoice": session['invoice'],
    #   "created": datetime.now(pytz.timezone(server_config['timezone'])),
    # }]

    if session["mode"] == "subscription":
      print('subscription mode')
      subscription = stripe.Subscription.retrieve(session["subscription"])
      # print(subscription)

      data = {
        "id": session['subscription'],
        "status": True,
        "active": session['status'] == 'complete',
        "plan": line_items['data'][0]['description'].lower(),
        "customer": session['customer'],
        "user_id": user_id,
        "subscribed_at": createdAt,
      }
      update_config(int(guild_id), 'premium', data)
    
    if session["mode"] == "payment":
      print('payment mode')

      data = {
        "id": session['payment_intent'],
        "status": True,
        "active": session['status'] == 'complete',
        "plan": line_items['data'][0]['description'].lower(),
        "customer": session['customer'],
        "user_id": user_id,
        "subscribed_at": createdAt,
      }
      update_config(int(guild_id), 'premium', data)
    return {}
  
  # === Handle customer.subscription.updated (Updates, Cancellations) ===
  if event['type'] == 'customer.subscription.updated':
    subscription = event['data']['object']
    # print("🔄 Subscription Updated:", subscription)
  
    if not subscription:
      return jsonify({"error": "Invalid subscription data"}), 400
    
    subscription_id = subscription['id']

    # Fetch from DB using subscription ID instead of looping
    db_entry = db.find_one({"premium.id": subscription_id})
    if not db_entry:
      return jsonify({"error": "Subscription data not found"}), 400

    guild_id = db_entry['_id']
    premium = db_entry['premium']
    config = db_entry['settings']
    
    ptimezone = pytz.timezone(config['timezone'])

    # Cancellation
    if subscription.get('cancel_at') or subscription.get('canceled_at'):
      print(f"🚨 Subscription {subscription_id} is canceled")
      update_config(int(guild_id), 'premium.status', False)
      update_config(int(guild_id), 'premium.active', False)
      return jsonify({"status": "success", "msg": "User canceled subscription"}), 200
    
    # TODO: Trial

    # Renewal
    if premium['status'] == False and not subscription.get('cancel_at'):
      print(f"✅ Subscription {subscription_id} is renewed! Restoring premium access.")

      update_config(int(guild_id), 'premium.status', True)
      update_config(int(guild_id), 'premium.active', True)

      # Update renewal date
      updatedAt = datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc).astimezone(ptimezone)
      update_config(int(guild_id), 'premium.subscribed_at', updatedAt)
      
      return jsonify({"status": "success", "msg": "User subscribed to premium"}), 200

    return jsonify({"status": "success"}), 200

  if event['type'] == 'customer.subscription.deleted':
    subscription = event['data']['object']
    # print("🚫 Subscription Canceled:", subscription['id'])

    # Find user in your database
    db_entry = db.find_one({"premium.id": subscription['id']})
    if not db_entry:
      print("⚠️ Subscription data not found")
      return jsonify({"error": "Subscription not found"}), 400

    guild_id = db_entry['_id']

    # Remove premium access
    update_config(int(guild_id), 'premium.active', False)
    update_config(int(guild_id), 'premium.status', False)
    print(f"⚠️ Premium access removed for guild {guild_id}")

    return jsonify({"status": "success", "msg": "Subscription canceled"}), 200
  
  if event['type'] == 'invoice.paid':
    invoice = event['data']['object']
    # print("💰 Invoice Paid:", invoice)

    subscription_id = invoice['subscription']

    # Fetch subscription details
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Find user in your database
    db_entry = db.find_one({"premium.id": subscription_id})
    if not db_entry:
      print("⚠️ Subscription not found in database")
      return jsonify({"error": "Subscription data not found"}), 400

    guild_id = db_entry['_id']

    # Update subscription status in database
    data = {
      "id": subscription_id,
      "status": True,
      "active": True,
      "plan": subscription['items']['data'][0]['description'].lower(),
      "customer": subscription['customer'],
      "user_id": db_entry['premium']['user_id'],
      "subscribed_at": datetime.now(),
    }
    update_config(int(guild_id), 'premium', data)

    # Update renewal date
    renewedAt = datetime.fromtimestamp(subscription["current_period_end"], tz=timezone.utc).astimezone(ptimezone)
    update_config(int(guild_id), 'premium.subscribed_at', renewedAt)

    return jsonify({"status": "success", "msg": "Invoice paid, subscription updated"}), 200
  
  if event['type'] == 'invoice.payment_failed':
    invoice = event['data']['object']
    # print("❌ Invoice Payment Failed:", invoice['id'])

    subscription_id = invoice['subscription']

    # Fetch subscription details
    subscription = stripe.Subscription.retrieve(subscription_id)

    # Find user in your database
    db_entry = db.find_one({"premium.id": subscription_id})
    if not db_entry:
      print("⚠️ Subscription not found in database")
      return jsonify({"error": "Subscription data not found"}), 400

    guild_id = db_entry['_id']
    config = db_entry['settings']
    ptimezone = pytz.timezone(config['timezone'])

    # Mark subscription as "past_due" in database
    update_config(int(guild_id), 'premium.active', False)
    update_config(int(guild_id), 'premium.status', False)

    # Optional: Notify the user to update their payment method
    print(f"🚨 Notify user {db_entry['premium']['user_id']} to update payment method!")

    return jsonify({"status": "success", "msg": "Invoice payment failed"}), 200

  # print(f"Unhandled event type {event['type']}")
  return jsonify({"status": "ignored"}), 200


class guild_models:
  def __init__(self, guild=None):
    super().__init__()
    self.guild: discord.Guild = guild

  @property
  def roles(self):
    roles = []
    for role in self.guild.roles:
      roles.append({
        'id': role.id,
        'name': role.name,
        'color': role.color,
        'permissions': role.permissions.value,
        'position': role.position,
        'disabled': role.position >= self.guild.me.top_role.position,
      })
    
    roles.sort(key=lambda x: x['position'], reverse=True)
    return roles
  
  @property
  def channels(self):
    text_channels = []
    voice = [channel for channel in self.guild.voice_channels]
    categories = [category for category in self.guild.categories]

    for channel in self.guild.text_channels:
      text_channels.append({
        'type': 'text',
        'id': channel.id,
        'name': channel.name,
        'position': channel.position,
        'can_send': channel.permissions_for(self.guild.me).send_messages,
      })
    
    def sortFn(chan):
      return chan.position
    
    text_channels.sort(key=lambda x: x['position'], reverse=False)
    voice.sort(key=sortFn)
    categories.sort(key=sortFn)
    return {"text": text_channels, "voice": voice, "categories": categories}
  
  @property
  def emojis(self):
    emojis: list[discord.Emoji] = []
    for emoji in self.guild.emojis:
      emojis.append({
        'id': emoji.id,
        'name': emoji.name,
        'url': emoji.url,
        'animated': emoji.animated,
      })
    return emojis

  @property
  def isPremium(self):
    premiumStatus = False
    data = get_server_config(self.guild, True)
    
    premiumStatus = data['premium']['status'] and data['premium']['active']
    return premiumStatus


app_started = False # Define a flag to check if the app is running

@bot.event
async def on_ready():
  if app_started:
    print("Dashboard is Online")
    
    try:
      stop_premium.start()
    except RuntimeError:
      pass

from discord.ext import tasks
@tasks.loop(hours=24) # Loop through all guilds every 24 hours
async def stop_premium():
  for guild in bot.guilds:
    config = get_server_config(guild, True)
    premium = config['premium']

    if premium['status'] == True:
      if premium['plan'] != "trial":
        continue
      
      subscribed_at = datetime.fromisoformat(str(premium['subscribed_at'])) # Convert the subscribed_at string to a datetime object
      
      expiry_date = subscribed_at + datetime.fromisoformat(str(premium['code_expiry']))
      
      if expiry_date <= (datetime.now()):
        update_config(guild.id, 'premium.status', False)
        update_config(guild.id, 'premium.active', False)
        print(f"Premium expired for {guild.name} ({guild.id})")

def run_app():
  global app_started
  app_started = True  # Update the flag when the app starts
  app.run(host='localhost', port=8000, use_reloader=False)

def run_dashboard():
  Thread(target=run_app).start()