import discord
import pymongo
import logging
from pathlib import Path
from quart import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for, send_from_directory

from modules import bot as v
from modules.models import Guild, Leveling
from ...config import mongo_cdn
from ...db import get_guild
from ...utils import bearer_client, check_guild_permission, plugin_guard, is_premium

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
async def _leaderboard_action(guild, config):
    """Handle admin POST actions (RemoveBanner / rest_all / reset) from the
    public leaderboard page. Returns a JSON response tuple."""
    if "token" not in session:
        return jsonify({"status": 403, "message": "Not authenticated"}), 403
    try:
        current_user = bearer_client().get_current_user()
    except Exception:
        return jsonify({"status": 403, "message": "Not authenticated"}), 403

    has_perm, _level = await check_guild_permission(guild, current_user.id)
    if not has_perm:
        return jsonify({"status": 403, "message": "Insufficient permissions"}), 403

    body = await request.get_json(silent=True) or {}
    key = body.get("key")

    if key == "RemoveBanner":
        config.dashboard.leveling.setdefault("leaderboard", {})["banner"] = ""
        config.updated_at = discord.utils.utcnow()
        await config.save()
        return jsonify({"status": 200, "message": "Banner removed"})

    if key == "rest_all":
        result = await Leveling.find(Leveling.guild_id == str(guild.id)).update(
            {"$set": {"exp": 0, "lvl": 0, "msg_count": 0}}
        )
        modified = getattr(result, "modified_count", 0)
        logger.info(f"Leaderboard: {current_user.id} reset all XP for guild {guild.id} ({modified} members)")
        return jsonify({"status": 200, "message": f"Reset {modified} members"})

    if key == "reset":
        user_id = str(body.get("user_id") or "")
        if not user_id:
            return jsonify({"status": 400, "message": "user_id is required"}), 400
        doc = await Leveling.get(f"{guild.id}_{user_id}")
        if doc is not None:
            doc.exp = 0
            doc.lvl = 0
            doc.msg_count = 0
            await doc.save()
        logger.info(f"Leaderboard: {current_user.id} reset XP for {user_id} in guild {guild.id}")
        return jsonify({"status": 200, "message": "Member XP reset"})

    return jsonify({"status": 400, "message": "Unknown action"}), 400

async def _resolve_leaderboard_guild(identifier: str):
    """Resolve a ``/leaderboard/<identifier>`` segment to a guild.

    ``identifier`` is either a numeric guild id or a guild's custom leaderboard
    slug (premium feature, stored at ``leveling.leaderboard.url``).
    """
    if identifier.isdigit():
        guild = v.client.get_guild(int(identifier))
        if guild is not None:
            return guild

    slug_doc = await Guild.find_one({"Dash.leveling.leaderboard.url": identifier.strip().lower()})
    if slug_doc is not None:
        return v.client.get_guild(int(slug_doc.id))

    return None


@leveling_bp.route("/leaderboard/<identifier>", methods=["GET", "POST"])
async def leaderboard_home(identifier):
    guild = await _resolve_leaderboard_guild(identifier)

    if guild is None:
        if request.method == "POST":
            return jsonify({"status": 404, "message": "Guild not found"}), 404
        await flash('Guild not found', 'error')
        return redirect(url_for('web.index'))

    # Get leveling config from dashboard
    config = await Guild.get(str(guild.id))
    if config is None:
        if request.method == "POST":
            return jsonify({"status": 404, "message": "Guild config not found"}), 404
        await flash('Guild config not found', 'error')
        return redirect(url_for('web.index'))

    if request.method == "POST":
        return await _leaderboard_action(guild, config)

    lvl_config = config.dashboard.leveling
    leaderboard_config = lvl_config.get('leaderboard', {})

    current_user = None
    if "token" in session:
        try:
            current_user = bearer_client().get_current_user()
        except Exception:
            current_user = None

    # Private leaderboards are visible only to logged-in members of the guild
    if not leaderboard_config.get('public', False):
        if not current_user or not guild.get_member(current_user.id):
            await flash('You are not allowed to view the leaderboard', 'error')
            return redirect(url_for('web.index'))

    # Get leveling data from Leveling collection
    leveling_users = await Leveling.find(Leveling.guild_id == str(guild.id)).to_list()
    sorted_players = sorted(leveling_users, key=lambda x: x.lvl, reverse=True)

    users = []
    rank = 0
    for data in sorted_players:
        player = v.client.get_user(int(data.user_id))
        if not player:
            continue
        rank += 1
        users.append((rank, (player, {
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


# ── Dashboard plugin page ─────────────────────────────────────────────────────
@leveling_bp.route("/dashboard/<int:guild_id>/leveling")
@plugin_guard('leveling')
async def levelling(guild_id):
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
        server_cards=_get_rank_cards(),
        is_premium=await is_premium(guild),
    )