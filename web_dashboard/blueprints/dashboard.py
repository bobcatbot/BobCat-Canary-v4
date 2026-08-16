from datetime import datetime
import discord
from quart import Blueprint, jsonify, redirect, render_template, request, session
from modules import bot as v
from modules.models import Guild, Notification, Economy
from ..config import CLIENT_ID, URL_BASE
from ..consts import langs, premium_faqs, premium_types, tz
from ..utils import bearer_client, login_required

dashboard_bp = Blueprint('dashboard', __name__)

def _check_guild_permission(guild, user_id) -> tuple[bool, str]:
    """Check if user has permission to modify guild settings."""
    try:
        member = guild.get_member(user_id)
        if member is None:
            return False, "Not a member of this guild"
        
        # Check if user is guild owner
        if guild.owner_id == user_id:
            return True, "Owner"
        
        # Get guild config for custom roles
        config = Guild.get(str(guild.id)).run()
        if config is None:
            return False, "Guild config not found"
        
        settings = config.settings
        
        # Check if user has administrator permission
        if member.guild_permissions.administrator:
            return True, "Administrator"
        
        # Check custom admin roles
        admin_roles = settings.get('admin_roles', [])
        if any(str(role.id) in admin_roles for role in member.roles):
            return True, "Admin Role"
        
        # Check bot master roles
        bot_masters = settings.get('bot_masters', [])
        if any(str(role.id) in bot_masters for role in member.roles):
            return True, "Bot Master"
        
        return False, "Insufficient permissions"
        
    except Exception as e:
        return False, f"Error checking permissions: {str(e)}"

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
@login_required
async def data_post(guild_id):
    """
    Catch-all endpoint for dashboard setting updates.
    Now includes proper permission checks and input validation.
    """
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    current_user = bearer_client().get_current_user()
    
    # ── PERMISSION CHECK ──────────────────────────────────────────────────
    has_permission, permission_level = _check_guild_permission(guild, current_user.id)
    if not has_permission:
        return jsonify({
            'status': 'error', 
            'message': f'Permission denied: {permission_level}'
        }), 403

    data = await request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # ── VALIDATE ALLOWED KEYS ────────────────────────────────────────────
    ALLOWED_SETTINGS_KEYS = {
        'settings.language': str,
        'settings.timezone': str,
        'settings.color': str,
        'settings.admin_roles': list,
        'settings.bot_masters': list,
    }
    
    ALLOWED_DASH_PREFIX = "Dash."

    DASHBOARD_PLUGIN_KEYS = [
        'welcome', 'moderation', 'verification', 'starboard', 'forms',
        'temporary_channels', 'ticketing', 'stats', 'leveling', 
        'birthdays', 'giveaways', 'economy', 'socialAlerts', 'music'
    ]

    # Get the guild document once
    doc = Guild.get(str(guild.id)).run()
    if doc is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    audit_entries = []

    for key, val in data.items():
        # ── Special case: Reset economy ──────────────────────────────────
        if key == "EconomyUsers":
            if permission_level not in ["Owner", "Administrator"]:
                return jsonify({
                    'status': 'error',
                    'message': 'Resetting economy requires Owner or Administrator permissions'
                }), 403
            
            if val is not True and val != "true":
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid value for EconomyUsers reset'
                }), 400
            
            deleted_count = Economy.find(Economy.guild_id == str(guild.id)).delete()
            audit_entries.append(f"Reset economy: deleted {deleted_count} records")
            continue

        # ── Settings keys (saved to Guild.settings) ─────────────────────
        if key in ALLOWED_SETTINGS_KEYS:
            expected_type = ALLOWED_SETTINGS_KEYS[key]
            if not isinstance(val, expected_type):
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid type for {key}: expected {expected_type.__name__}'
                }), 400
            
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
            audit_entries.append(f"Updated {key} = {val}")
            continue

        # ── Dashboard plugin settings (saved to Guild.dashboard) ────────
        # Auto-add Dash. prefix if missing
        if not key.startswith(ALLOWED_DASH_PREFIX):
            first_part = key.split('.')[0] if '.' in key else key
            if first_part in DASHBOARD_PLUGIN_KEYS:
                key = ALLOWED_DASH_PREFIX + key
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid key: {key}. Dashboard keys must start with "{ALLOWED_DASH_PREFIX}" or be a known plugin name'
                }), 400

        dash_key = key.replace(ALLOWED_DASH_PREFIX, "")
        parts = dash_key.split('.')

        # Validate path
        if any(part in ('__', '..', 'parent') for part in parts):
            return jsonify({
                'status': 'error',
                'message': f'Invalid key path: contains disallowed pattern'
            }), 400

        # ── ✅ FIX: Navigate through the DashConfig model ──────────────
        # Start with the dashboard object
        current = doc.dashboard
        
        # Navigate through all parts except the last one
        for part in parts[:-1]:
            # Try to handle both dict and object access
            if isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]
            elif hasattr(current, part):
                # Pydantic model or object with attribute
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Cannot navigate: "{part}" not found in {type(current).__name__}'
                }), 400

        final = parts[-1]

        # ── ✅ FIX: Set the value on the final object ──────────────────
        try:
            if isinstance(current, dict):
                current[final] = val
            elif hasattr(current, final):
                # Pydantic model field - set using setattr
                setattr(current, final, val)
            elif isinstance(current, list):
                # List access
                try:
                    idx = int(final)
                    while len(current) <= idx:
                        current.append(None)
                    current[idx] = val
                except ValueError:
                    return jsonify({
                        'status': 'error',
                        'message': f'Cannot assign to list with non-integer: {final}'
                    }), 400
            else:
                # Fallback - try setattr
                try:
                    setattr(current, final, val)
                except AttributeError:
                    return jsonify({
                        'status': 'error',
                        'message': f'Cannot assign to {type(current).__name__}: {final}'
                    }), 400
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to set value: {str(e)}'
            }), 400

        audit_entries.append(f"Updated {key} = {val}")

    # ── SAVE AND AUDIT ──────────────────────────────────────────────────
    doc.updated_at = discord.utils.utcnow()
    doc.save()

    if audit_entries:
        print(f"[AUDIT] Guild {guild_id} modified by {current_user.id}: {', '.join(audit_entries)}")
    
    return jsonify({
        'status': 'success', 
        'message': 'Successfully updated data',
        'audit': audit_entries
    })