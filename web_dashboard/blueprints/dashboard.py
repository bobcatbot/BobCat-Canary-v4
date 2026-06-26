from datetime import datetime
from flask import Blueprint, jsonify, redirect, render_template, request, session
from modules import bot as v
from ..config import CLIENT_ID, URL_BASE
from ..consts import langs, premium_faqs, premium_types, tz
from ..db import get_server_config, update_config
from ..utils import bearer_client, login_required

dashboard_bp = Blueprint('dashboard', __name__)

# ── Guild picker ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard")
@login_required
def guilds():
    current_user = bearer_client().get_current_user()
    guild_ids = [g.id for g in v.client.guilds]
    guilds = []

    for guild in bearer_client().get_my_guilds():
        bot_master = False
        config = get_server_config(guild.id, True)
        if config:
            bot_guild = v.client.get_guild(guild.id)
            member = bot_guild.get_member(current_user.id) if bot_guild else None
            if member:
                roles = config['settings']
                bot_master = any(
                    str(role.id) in roles['admin_roles'] or
                    str(role.id) in roles['bot_masters']
                    for role in member.roles
                )

        if guild.is_owner or bot_master or int(guild.permissions) & 0x8 == 0x8:
            perm = (
                "Owner"      if guild.is_owner                      else
                "Bot Master" if bot_master                          else
                "Admin"      if int(guild.permissions) & 0x8 == 0x8 else
                "Member"
            )
            guilds.append({
                'id':       guild.id,
                'name':     guild.name,
                'icon_url': guild.icon_url,
                'perm':     perm,
                'btn_name': "Go"      if guild.id in guild_ids else "Setup",
                'color':    "#5865F2" if guild.id in guild_ids else "#36393f",
            })

    guilds.sort(key=lambda x: ( x['btn_name'] != "Go" and x['color'] != "#5865F2" ))

    return render_template(
        "dashboard/guilds.html", 
        user=current_user, guilds=guilds
    )


# ── Dashboard home ────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>")
@login_required
def dashboard_home(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    session['guild_id'] = guild_id

    if guild is None:
        return redirect(
            f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}"
            f"&scope=bot&permissions=8&guild_id={guild_id}"
            f"&response_type=code&redirect_uri={URL_BASE}/dashboard"
        )

    return render_template(
        "dashboard/dashboard.html", 
        user=current_user, guild=guild
    )


# ── Settings ──────────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/settings")
@login_required
def settings(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    data = get_server_config(guild, True).get('settings')
    return render_template(
        "dashboard/settings.html",
        user=current_user, guild=guild, data=data, languages=langs, timezones=tz
    )


# ── Premium ───────────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/premium", methods=["GET", "POST"])
@login_required
def premium(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    prem_data = get_server_config(guild, True).get('premium')

    if not prem_data['status']:
        return render_template(
            "dashboard/premium/index.html",
            user=current_user, guild=guild, data=prem_data,
            faqs=premium_faqs, types=premium_types
        )

    createdAt_later = "Never"
    days_countdown = "0"
    if prem_data['plan'] in ('monthly', 'yearly'):
        date = prem_data['subscribed_at']
        days_countdown = (date - datetime.now()).days
        createdAt_later = date.strftime("%B %d %Y")

    user = v.client.get_user(int(prem_data['user_id']))
    data = {
        'next_bill': createdAt_later,
        'countdown': days_countdown,
        'user': {'avatar': user.avatar.url, 'name': user.name},
    } | prem_data

    return render_template(
        "dashboard/premium/manage.html",
        user=current_user, guild=guild, data=data, types=premium_types
    )


# ── Notifications ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/notifications", methods=["GET", "POST"])
@login_required
def notifications(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    data = get_server_config(guild, True).get('notifications')

    if request.method == 'POST':
        res = request.get_json()
        notif = next((n for n in data if n['id'] == res['id']), None)
        if notif:
            notif_idx = data.index(notif)
            res.pop('id')
            for key, val in res.items():
                update_config(guild.id, f'notifications.{notif_idx}.{key}', val)
        return jsonify({'status': 'success', 'message': 'Successfully updated notifications'})

    notifications_by_date = {}
    for notification in data:
        date = notification['created_at']['date']
        notifications_by_date.setdefault(date, []).append(notification)
        notifications_by_date[date].sort(key=lambda x: x['created_at']['time'], reverse=True)
    notifications_by_date = dict(reversed(list(notifications_by_date.items())))

    return render_template(
        "dashboard/notifications.html",
        user=current_user, guild=guild, config=data, data=notifications_by_date
    )


# ── Data post (catch-all config update) ──────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/data/post", methods=["POST"])
def data_post(guild_id):
    guild = v.client.get_guild(guild_id)
    settings_keys = {
        'settings.language', 'settings.timezone', 'settings.color',
        'settings.admin_roles', 'settings.bot_masters'
    }

    for key, val in request.get_json().items():
        if key == "EconomyUsers":
            server = get_server_config(guild)['economy']
            for user in server:
                server[user]['wallet'] = 0
                server[user]['bank'] = 0
                server[user]['bag'] = []
            update_config(guild, 'Bot.economy', server)
            break

        if key in settings_keys:
            update_config(guild, key, val)
            break

        update_config(guild, "Dash." + key, val)

    return {'status': 'success', 'message': 'Successfully updated data'}