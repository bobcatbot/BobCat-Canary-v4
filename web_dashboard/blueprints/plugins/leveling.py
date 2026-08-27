import pymongo
import logging
from pathlib import Path
from quart import Blueprint, flash, jsonify, redirect, render_template, session, url_for, send_from_directory

from modules import bot as v
from modules.models import Guild, Leveling
from ...config import mongo_cdn
from ...db import get_guild
from ...utils import bearer_client, login_required, premium_module

leveling_bp = Blueprint('leveling', __name__)
logger = logging.getLogger(__name__)

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
async def lvl_cards():
    return jsonify(_get_rank_cards())

@leveling_bp.route("/lvl-cards/image/<path:filename>")
async def lvl_card_image(filename):
    return await send_from_directory(RANK_CARD_DIR, filename)

# ── Public leaderboard ────────────────────────────────────────────────────────
@leveling_bp.route("/leaderboard/<guild_id>")
async def leaderboard_home(guild_id):
    try:
        guild = v.client.get_guild(int(guild_id))
        if guild is None:
            await flash('Guild not found', 'error')
            return redirect(url_for('web.index'))

        # Get leveling config from dashboard
        config = await Guild.get(str(guild.id))
        if config is None:
            await flash('Guild config not found', 'error')
            return redirect(url_for('web.index'))

        lvl_config = config.dashboard.get('leveling', {})
        leaderboard_config = lvl_config.get('leaderboard', {})

        # Check if leaderboard is public
        if not leaderboard_config.get('public', False):
            if "token" not in session:
                await flash('You are not allowed to view the leaderboard', 'error')
                return redirect(url_for('web.index'))

        current_user = None
        if "token" in session:
            try:
                current_user = bearer_client().get_current_user()
            except Exception:
                current_user = None

        # Check access for private leaderboards
        if not leaderboard_config.get('public', False):
            if not current_user or not guild.get_member(current_user.id):
                await flash('You are not allowed to view the leaderboard', 'error')
                return redirect(url_for('web.index'))

        # Get leveling data from Leveling collection
        leveling_users = await Leveling.find(Leveling.guild_id == str(guild.id)).to_list()
        sorted_players = sorted(leveling_users, key=lambda x: x.lvl, reverse=True)

        users = []
        for idx, data in enumerate(sorted_players, start=1):
            player = v.client.get_user(int(data.user_id))
            if player:
                users.append((idx, (player, {
                    'lvl': data.lvl,
                    'exp': data.exp,
                    'msg_count': data.msg_count or 0
                })))

        # Check guild permissions for the current user
        gp = False
        if current_user:
            member = guild.get_member(current_user.id)
            if member:
                if member.guild_permissions.administrator:
                    gp = {'administrator': True, 'bot_master': False}
                else:
                    settings = config.settings
                    if any(
                        str(role.id) in settings.get('admin_roles', []) or 
                        str(role.id) in settings.get('bot_masters', [])
                        for role in member.roles
                    ):
                        gp = {'administrator': False, 'bot_master': True}

        return await render_template(
            "dashboard/leaderboard.html",
            user=current_user,
            guild_permissions=gp,
            guild=guild,
            data=lvl_config,
            users=users
        )
    except Exception as e:
        logger.error(f"Error loading leaderboard for guild {guild_id}: {e}", exc_info=True)
        await flash('An error occurred loading the leaderboard', 'error')
        return redirect(url_for('web.index'))


# ── Dashboard plugin page ─────────────────────────────────────────────────────
@leveling_bp.route("/dashboard/<int:guild_id>/leveling")
@login_required
async def levelling(guild_id):
    await premium_module(guild_id, 'leveling')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    # Get the guild document using Beanie
    config = (await Guild.get(str(guild.id))).dashboard.leveling
        
    return await render_template(
        "dashboard/plugins/leveling.html",
        user=current_user,
        guild=guild,
        data=config,
        server_cards=_get_rank_cards()
    )