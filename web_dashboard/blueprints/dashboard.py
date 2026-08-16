from datetime import datetime
from quart import Blueprint, jsonify, redirect, render_template, request, session
from modules import bot as v
from modules.models import Guild, Notification, Economy
from ..config import CLIENT_ID, URL_BASE
from ..consts import langs, premium_faqs, premium_types, tz
from ..utils import bearer_client, login_required

dashboard_bp = Blueprint('dashboard', __name__)

# ── Guild picker ──────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard")
@login_required
async def guilds():
    current_user = bearer_client().get_current_user()
    guild_ids = [g.id for g in v.client.guilds]
    guilds = []

    for guild in bearer_client().get_my_guilds():
        bot_master = False
        config = Guild.get(str(guild.id)).run()
        if config:
            bot_guild = v.client.get_guild(guild.id)
            member = bot_guild.get_member(current_user.id) if bot_guild else None
            if member:
                settings = config.settings
                bot_master = any(
                    str(role.id) in settings.get('admin_roles', []) or
                    str(role.id) in settings.get('bot_masters', [])
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

    return await render_template(
        "dashboard/guilds.html", 
        user=current_user, guilds=guilds
    )


# ── Dashboard home ────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>")
@login_required
async def dashboard_home(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    session['guild_id'] = guild_id

    if guild is None:
        return redirect(
            f"https://discord.com/oauth2/authorize?client_id={CLIENT_ID}"
            f"&scope=bot&permissions=8&guild_id={guild_id}"
            f"&response_type=code&redirect_uri={URL_BASE}/dashboard"
        )

    return await render_template(
        "dashboard/dashboard.html", 
        user=current_user, guild=guild
    )


# ── Settings ──────────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/settings")
@login_required
async def settings(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    config = Guild.get(str(guild.id)).run()
    data = config.settings if config else {}
    return await render_template(
        "dashboard/settings.html",
        user=current_user, guild=guild, data=data, languages=langs, timezones=tz
    )


# ── Premium ───────────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/premium", methods=["GET", "POST"])
@login_required
async def premium(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    config = Guild.get(str(guild.id)).run()
    prem_data = config.premium if config else {}

    if not prem_data.get('status', False):
        return await render_template(
            "dashboard/premium/index.html",
            user=current_user, guild=guild, data=prem_data,
            faqs=premium_faqs, types=premium_types
        )

    createdAt_later = "Never"
    days_countdown = "0"
    if prem_data.get('plan') in ('monthly', 'yearly'):
        date = prem_data.get('subscribed_at')
        if date:
            days_countdown = (date - datetime.now()).days
            createdAt_later = date.strftime("%B %d %Y")

    user = v.client.get_user(int(prem_data.get('user_id', 0)))
    data = {
        'next_bill': createdAt_later,
        'countdown': days_countdown,
        'user': {'avatar': user.avatar.url if user else '', 'name': user.name if user else 'Unknown'},
    } | prem_data

    return await render_template(
        "dashboard/premium/manage.html",
        user=current_user, guild=guild, data=data, types=premium_types
    )


# ── Notifications ─────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/notifications", methods=["GET", "POST"])
@login_required
async def notifications(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    
    all_notifs = Notification.find(Notification.guild_id == str(guild.id)).run()

    if request.method == 'POST':
        res = await request.get_json()
        notif = next((n for n in all_notifs if n.notification_id == res['id']), None)
        if notif:
            res.pop('id')
            for key, val in res.items():
                setattr(notif, key, val)
            notif.save()
        return jsonify({'status': 'success', 'message': 'Successfully updated notifications'})

    notifications_by_date = {}
    for notification in all_notifs:
        date = notification.created_at.strftime('%Y-%m-%d')
        notifications_by_date.setdefault(date, []).append({
            'id': notification.notification_id,
            'type': notification.type,
            'title': notification.title,
            'description': notification.description,
            'fix': notification.fix,
            'link': notification.link,
            'user': notification.user,
            'read': notification.read,
            'created_at': {
                'date': notification.created_at.strftime('%Y-%m-%d'),
                'time': notification.created_at.strftime('%H:%M:%S'),
            }
        })
        notifications_by_date[date].sort(key=lambda x: x['created_at']['time'], reverse=True)
    notifications_by_date = dict(reversed(list(notifications_by_date.items())))

    return await render_template(
        "dashboard/notifications.html",
        user=current_user, guild=guild, config=all_notifs, data=notifications_by_date
    )


# ── Data post (catch-all config update) ──────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/data/post", methods=["POST"])
async def data_post(guild_id):
    """
    Catch-all endpoint for dashboard setting updates.
    Handles:
    - Settings (language, timezone, color, admin_roles, bot_masters)
    - Economy reset (EconomyUsers)
    - Dashboard plugin settings (Dash.*)
    - List indices (e.g., economy.shop.0)
    """
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return {'status': 'error', 'message': 'Guild not found'}, 404

    data = await request.get_json()
    if not data:
        return {'status': 'error', 'message': 'No data provided'}, 400

    settings_keys = {
        'settings.language', 'settings.timezone', 'settings.color',
        'settings.admin_roles', 'settings.bot_masters'
    }

    # Get the guild document once
    doc = Guild.get(str(guild.id)).run()
    if doc is None:
        return {'status': 'error', 'message': 'Guild config not found'}, 404

    for key, val in data.items():
        # ── Special case: Reset economy ──────────────────────────────────
        if key == "EconomyUsers":
            deleted_count = Economy.find(Economy.guild_id == str(guild.id)).delete()
            print(f"🗑️ Deleted {deleted_count} economy records")
            continue

        # ── Settings keys (saved to Guild.settings) ─────────────────────
        if key in settings_keys:
            if key.startswith("settings."):
                actual_key = key.replace("settings.", "")
                doc.settings[actual_key] = val
            else:
                parts = key.split('.')
                current = doc.settings
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = val
            doc.save()
            continue

        # ── Dashboard plugin settings (saved to Guild.dashboard) ────────
        dash_key = key.replace("Dash.", "")
        parts = dash_key.split('.')

        # Navigate to the parent of the final key
        current = doc.dashboard
        for part in parts[:-1]:
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            elif isinstance(current, list):
                # If we're inside a list, part should be an index
                try:
                    idx = int(part)
                    # Ensure the list is long enough
                    while len(current) <= idx:
                        current.append({})
                    current = current[idx]
                except ValueError:
                    # If part isn't a number, treat as attribute (fallback)
                    current = getattr(current, part, {})
            else:
                # Fallback for other object types
                current = getattr(current, part, {})

        final = parts[-1]

        # ── Assign the value based on the type of `current` ─────────────
        if isinstance(current, dict):
            current[final] = val
        elif isinstance(current, list):
            # Final part should be an index for a list
            try:
                idx = int(final)
                # Ensure the list is long enough
                while len(current) <= idx:
                    current.append(None)
                current[idx] = val
            except ValueError:
                # If final isn't an integer, fallback to attribute (unlikely)
                setattr(current, final, val)
        else:
            # For Pydantic models or other objects
            setattr(current, final, val)

        doc.save()

    return {'status': 'success', 'message': 'Successfully updated data'}