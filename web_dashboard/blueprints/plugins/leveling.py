import pymongo
from pathlib import Path
from flask import Blueprint, flash, jsonify, redirect, render_template, session, url_for, send_from_directory

from modules import bot as v
from ...config import mongo_cdn
from ...db import get_dash_config, get_server_config
from ...utils import bearer_client, login_required, premium_module

leveling_bp = Blueprint('leveling', __name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RANK_CARD_DIR = PROJECT_ROOT / "images" / "lvl-cards"

rank_cards = pymongo.MongoClient(mongo_cdn)['RankCards']['Cards']

def _get_rank_cards():
    projection = { '_id': 0, 'card': 1, 'card_name': 1, 'theme': 1, 'bar_bg': 1, 'bar_fill': 1, 'bar_indent_left': 1, 'bar_width': 1}
    
    all_cards = list(rank_cards.find({}, projection))
    
    default = [c for c in all_cards if c.get("theme") == "default"]
    fun = [c for c in all_cards if c.get("theme") == "bobcat"]
    
    return {'all': all_cards, 'default': default, 'cards': fun}

# ── Public JSON endpoint for rank cards ──────────────────────────────────────
@leveling_bp.route("/lvl-cards")
def lvl_cards():
    return jsonify(_get_rank_cards())

@leveling_bp.route("/lvl-cards/image/<path:filename>")
def lvl_card_image(filename):
    return send_from_directory(RANK_CARD_DIR, filename)

# ── Public leaderboard ────────────────────────────────────────────────────────
@leveling_bp.route("/leaderboard/<guild_id>")
def leaderboard_home(guild_id):
    lvl_config = get_dash_config(guild_id).get('leveling')

    if not lvl_config['leaderboard'].get('public', False):
        if "token" not in session:
            flash('You are not allowed to view the leaderboard', 'error')
            return redirect(url_for('web.index'))

    current_user = None
    if "token" in session:
        try:
            current_user = bearer_client().get_current_user()
        except Exception:
            current_user = None

    guild = v.client.get_guild(int(guild_id))

    if not lvl_config['leaderboard'].get('public', False):
        if not current_user or not guild.get_member(current_user.id):
            flash('You are not allowed to view the leaderboard', 'error')
            return redirect(url_for('web.index'))

    lvl_users = get_server_config(guild).get('leveling')
    sorted_players = sorted(lvl_users.items(), key=lambda x: int(x[1]['lvl']), reverse=True)

    users = []
    for idx, (player_id, data) in enumerate(sorted_players, start=1):
        player = v.client.get_user(int(player_id))
        data['msg_count'] = data.get('msg_count', 0)
        users.append((idx, (player, data)))

    gp = False
    if current_user:
        member = guild.get_member(current_user.id)
        if member:
            if member.guild_permissions.administrator:
                gp = {'administrator': True, 'bot_master': False}
            else:
                config = get_server_config(guild.id, True)
                if config:
                    roles = config['settings']
                    if any(
                        str(role.id) in roles['admin_roles'] or str(role.id) in roles['bot_masters']
                        for role in member.roles
                    ):
                        gp = {'administrator': False, 'bot_master': True}

    return render_template(
        "dashboard/leaderboard.html",
        user=current_user, 
        guild_permissions=gp, 
        guild=guild, 
        data=lvl_config, 
        users=users
    )


# ── Dashboard plugin page ─────────────────────────────────────────────────────
@leveling_bp.route("/dashboard/<int:guild_id>/leveling")
@login_required
def levelling(guild_id):
    premium_module(guild_id, 'leveling')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    dash_data = get_dash_config(guild.id).get('leveling')
    
    return render_template(
        "dashboard/plugins/leveling.html",
        user=current_user, 
        guild=guild, 
        data=dash_data, 
        server_cards=_get_rank_cards()
    )