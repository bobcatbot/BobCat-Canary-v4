import discord
import pymongo
from modules import bot as v
from dashboard.config import mongo_cdn
from dashboard.consts import imgs
from dashboard.index import bot, login_required, bearer_client, get_dash_config, get_server_config, update_config, premium_module
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify

leveling = Blueprint('leveling', __name__)

## Leaderboard ##
@leveling.route("/leaderboard/<guild_id>", methods=['GET', 'POST'])
@login_required
async def leaderboard_home(guild_id):
  current_user = bearer_client().get_current_user()

  if request.method == 'POST':
    json = request.get_json()
    guild = bot.get_guild(int(json['guild_id']))

    leveling = get_server_config(guild).get('leveling')

    if 'reset' in json['key']:
      if 'user_id' in json:
        u = json['user_id']
        update_config(guild, key=f'Bot.leveling.{u}.exp', value=0)
        update_config(guild, key=f'Bot.leveling.{u}.lvl', value=0)
        return jsonify({'status': 200})
      
      for user in leveling:
        lvl_user = leveling[user]
        lvl_user['exp'] = 0
        lvl_user['lvl'] = 0
        update_config(guild, key=f'Bot.leveling.{user}', value=lvl_user)
      return jsonify({'status': 200})
    
    if json['key'] == 'BannerRemove':
      #update_config(guild, key='Dash.leveling.leaderboard.banner', value="")
      return jsonify({'status': 200})
    return jsonify({'status': 400})

  guild = bot.get_guild(int(guild_id))
  print(guild)

  lvl_config = get_dash_config(guild).get('leveling')
  
  if not lvl_config['leaderboard']['public'] and current_user.id not in [member.id for member in guild.members]:
    flash('You are not allowed to view the leaderboard', 'error')
    return redirect(url_for('index'))
  
  users = []
  lvl_users = get_server_config(guild).get('leveling')

  sorted_players = sorted(lvl_users.items(), key=lambda x: int(x[1]['lvl']), reverse=True)
  
  for idx, (player_id, data) in enumerate(sorted_players, start=1):    
    player = bot.get_user(int(player_id))
    data['msg_count'] = lvl_users[player_id]['msg_count'] if 'msg_count' in lvl_users[player_id] else 0
    users.append((idx, (player, data)))

  gp = False 
  user = guild.get_member(current_user.id)

  # if the user not in server
  if not user:
    gp = False
  
  if user and user.guild_permissions.administrator:
    gp = True

  return render_template("dashboard/leaderboard.html", user=current_user, guild_permissions=gp, guild=guild, data=lvl_config, users=users)


## Leveling ##
@leveling.route("/dashboard/<int:guild_id>/leveling")
@login_required
async def levelling_index(guild_id):
  premium_module(guild_id, 'leveling')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild.id).get('leveling')

  mongoRankCards = pymongo.MongoClient(mongo_cdn)['RankCards']['Cards']
  all_rank_cards = mongoRankCards.find({})
  
  default_cards = [
    { "card": card['card'], "bar_bg": card["bar_bg"], "bar_fill": card["bar_fill"], "bar_indent_left": card["bar_indent_left"], "bar_width": card["bar_width"] }
    for card in mongoRankCards.find({"card": {"$in": imgs['default']}})
  ]
  fun_cards = [
    { "card": file['card'], "bar_bg": file["bar_bg"], "bar_fill": file["bar_fill"], "bar_indent_left": file["bar_indent_left"], "bar_width": file["bar_width"] }
    for file in all_rank_cards
    if file['card'] not in imgs['default']
  ]
  cards = { 'all': default_cards + fun_cards, 'default': default_cards, 'cards': fun_cards }
  return render_template("dashboard/plugins/leveling.html", user=current_user, guild=guild, data=dash_data, server_cards=cards)
