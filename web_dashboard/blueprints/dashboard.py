import discord
from datetime import datetime, timezone, timedelta
from quart import Blueprint, current_app, redirect, url_for, render_template, flash, request, session, jsonify

from modules import bot as v
from modules.models import Guild, Notification, Economy
from ..config import CLIENT_ID, URL_BASE
from ..consts import langs, premium_faqs, premium_types, tz
from ..utils import bearer_client, check_guild_permission as _check_guild_permission, login_required

dashboard_bp = Blueprint('dashboard', __name__)

# ── Guild picker ──────────────────────────────────────────────────────────────
def get_user_eligible_guilds(current_user, exclude_guild_id=None):
    """Get all guilds the user owns, is bot master of, or has admin in."""
    guild_ids = [g.id for g in v.client.guilds]
    eligible_guilds = []

    for guild in bearer_client().get_my_guilds():
        # Skip the guild we're transferring from
        if exclude_guild_id and guild.id == exclude_guild_id:
            continue
            
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

        # Check if user has permission (Owner, Bot Master, or Admin)
        if guild.is_owner or bot_master or int(guild.permissions) & 0x8 == 0x8:
            perm = (
                "Owner" if guild.is_owner else
                "Bot Master" if bot_master else
                "Admin" if int(guild.permissions) & 0x8 == 0x8 else
                "Member"
            )
            
            # Check if bot is in the guild
            is_bot_in_guild = guild.id in guild_ids
            
            eligible_guilds.append({
                'id': guild.id,
                'name': guild.name,
                'icon_url': guild.icon_url,
                'perm': perm,
                'is_bot_in_guild': is_bot_in_guild,
            })

    # Sort: Owner first, then Bot Master, then Admin
    perm_order = {'Owner': 0, 'Bot Master': 1, 'Admin': 2}
    eligible_guilds.sort(key=lambda x: (perm_order.get(x['perm'], 99), x['name']))
    
    return eligible_guilds

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

    # ✅ Build dynamic plans list with all needed data
    plans = []
    for plan_key, plan_data in premium_types.items():
        plans.append({
            'key': plan_key,
            'name': plan_key.title(),  # Monthly, Yearly, Lifetime
            'price': plan_data.get('price', '$0.00'),
            'mode': plan_data.get('mode', 'subscription'),
            'price_id': plan_data.get('price_id'),
            'features': plan_data.get('features', [
                "Access to our premium plugins & features",
                "Early access"
            ]),
        })

    # ✅ Get Stripe publishable key from config
    stripe_public_key = current_app.config.get('STRIPE_PUBLIC_KEY', '')

    if not prem_data.get('status', False):
        return await render_template(
            "dashboard/premium/index.html",
            user=current_user,
            guild=guild,
            data=prem_data,
            faqs=premium_faqs,
            types=premium_types,
            plans=plans,
            stripe_public_key=stripe_public_key
        )

    # Get the user who purchased premium
    user = None
    user_id = prem_data.get('user_id')
    if user_id:
        try:
            user = v.client.get_user(int(user_id))
        except:
            pass

    # ✅ Get all guilds the user owns or has admin in
    user_guilds = get_user_eligible_guilds(current_user=current_user, exclude_guild_id=guild_id)

    # ✅ Get the expiry date - try period_end first, then code_expiry
    expiry_date = None
    
    # Try period_end (from Stripe)
    if prem_data.get('period_end'):
        expiry_date = prem_data['period_end']
    # Try code_expiry (from dev command)
    elif prem_data.get('code_expiry'):
        expiry_date = prem_data['code_expiry']
    # Fallback: calculate from subscribed_at
    elif prem_data.get('subscribed_at') and prem_data.get('plan'):
        subscribed_at = prem_data['subscribed_at']
        plan = prem_data['plan']
        
        if isinstance(subscribed_at, datetime):
            if plan == 'trial':
                expiry_date = subscribed_at + timedelta(days=30)
            elif plan in ('monthly', 'month'):
                expiry_date = subscribed_at + timedelta(days=30)
            elif plan in ('yearly', 'year'):
                expiry_date = subscribed_at + timedelta(days=365)

    # ✅ Calculate days remaining
    next_bill_date = None
    days_countdown = "0"
    next_bill_formatted = "Never"
    is_expired = False
    is_trial = prem_data.get('plan') == 'trial'
    
    if expiry_date:
        # Convert to datetime if needed
        if isinstance(expiry_date, (int, float)):
            next_bill_date = datetime.fromtimestamp(expiry_date)
        elif isinstance(expiry_date, str):
            try:
                next_bill_date = datetime.fromisoformat(expiry_date)
            except:
                pass
        elif isinstance(expiry_date, datetime):
            next_bill_date = expiry_date
        
        if next_bill_date:
            # Make sure timezone is set
            if not next_bill_date.tzinfo:
                next_bill_date = next_bill_date.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            days_remaining = (next_bill_date - now).days
            
            if days_remaining < 0:
                days_countdown = "0"
                next_bill_formatted = "Expired"
                is_expired = True
                # Auto-deactivate if expired
                if prem_data.get('active', True):
                    prem_data['active'] = False
                    prem_data['status'] = False
                    config.save()
            elif days_remaining == 0:
                days_countdown = "0"
                next_bill_formatted = "Today"
            else:
                days_countdown = str(days_remaining)
                next_bill_formatted = next_bill_date.strftime("%d %B %Y")

    # ✅ For trials with no expiry, show "Trial (No expiry)" or "Never"
    if is_trial and not expiry_date:
        next_bill_formatted = "Trial (No expiry)"

    # Build data for template
    data = {
        'next_bill': next_bill_formatted,
        'countdown': days_countdown,
        'is_expired': is_expired,
        'is_trial': is_trial,
        'is_lifetime': prem_data.get('plan') == 'lifetime',
        'plan': prem_data.get('plan'),
        'user': {
            'avatar': user.avatar.url if user and hasattr(user, 'avatar') else '',
            'name': user.name if user else 'Unknown',
        },
    }
    # Merge with existing premium data
    data = {**prem_data, **data}

    return await render_template(
        "dashboard/premium/manage.html",
        user=current_user,
        guild=guild,
        data=data,
        types=premium_types,
        user_guilds=user_guilds
    )

@dashboard_bp.route("/dashboard/<int:guild_id>/premium/transfer", methods=["GET"])
@login_required
async def transfer_premium_page(guild_id):
    """Show the premium transfer page."""
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    
    if not guild:
        await flash("Guild not found", "danger")
        return redirect(url_for('dashboard.dashboard_home'))
    
    # Check if user has permission (guild owner)
    if guild.owner_id != current_user.id:
        await flash("Only the guild owner can transfer premium", "danger")
        return redirect(url_for('dashboard.premium', guild_id=guild_id))
    
    doc = Guild.get(str(guild_id)).run()
    if not doc or not doc.premium.get('status', False):
        await flash("This guild doesn't have premium", "warning")
        return redirect(url_for('dashboard.premium', guild_id=guild_id))
    
    # Get all guilds the user owns where they have admin
    user_guilds = []
    for g in v.client.guilds:
        if g.owner_id == current_user.id or g.get_member(current_user.id).guild_permissions.administrator:
            if g.id != guild_id:  # Exclude current guild
                user_guilds.append(g)
    
    return await render_template(
        "dashboard/premium/transfer.html",
        user=current_user,
        guild=guild,
        data=doc.premium,
        user_guilds=user_guilds
    )

@dashboard_bp.route("/dashboard/<int:guild_id>/premium/transfer", methods=["POST"])
@login_required
async def transfer_premium_execute(guild_id):
    """Execute premium transfer."""
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    
    # Authorize
    if guild.owner_id != current_user.id:
        return jsonify({'error': 'Only the guild owner can transfer premium'}), 403
    
    doc = Guild.get(str(guild_id)).run()
    if not doc or not doc.premium.get('status', False):
        return jsonify({'error': 'This guild does not have premium'}), 404
    
    data = await request.get_json()
    target_guild_id = data.get('target_guild_id')
    
    if not target_guild_id:
        return jsonify({'error': 'Target guild ID is required'}), 400
    
    target_guild = v.client.get_guild(int(target_guild_id))
    if not target_guild:
        return jsonify({'error': 'Target guild not found'}), 404
    
    # Check if user owns/has admin in target guild
    if target_guild.owner_id != current_user.id:
        target_member = target_guild.get_member(current_user.id)
        if not target_member or not target_member.guild_permissions.administrator:
            return jsonify({'error': 'You need Administrator permissions in the target guild'}), 403
    
    target_doc = Guild.get(str(target_guild_id)).run()
    if not target_doc:
        return jsonify({'error': 'Target guild config not found'}), 404
    
    if target_doc.premium.get('status', False):
        return jsonify({'error': 'Target guild already has premium'}), 400
    
    # Transfer the premium
    premium_data = doc.premium.copy()
    premium_data['transferred_from'] = str(guild_id)
    premium_data['transferred_at'] = datetime.now(timezone.utc)
    premium_data['original_user_id'] = premium_data.get('user_id')
    
    # Apply to target
    target_doc.premium = premium_data
    target_doc.save()
    
    # Remove from source
    doc.premium = {}
    doc.save()
    
    # Send notifications
    try:
        v.push_notification(
            guild,
            'info',
            'Premium Transferred',
            f"Your premium has been transferred to **{target_guild.name}**"
        )
    except:
        pass
    
    try:
        v.push_notification(
            target_guild,
            'info',
            'Premium Received! 🎉',
            f"You received a premium subscription from **{guild.name}**!"
        )
    except:
        pass
    
    return jsonify({'status': 'success', 'message': 'Premium transferred successfully'}), 200

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