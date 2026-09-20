import re
import discord
from datetime import datetime, timezone, timedelta
from quart import Blueprint, current_app, redirect, url_for, render_template, flash, request, session, jsonify

from modules import bot as v
from modules.models import Guild, Notification, Economy, PremiumConfig, SettingsConfig
from ..config import INVITE_URL, REDIRECT_URI
from ..db import get_bell_notifications
from ..consts import langs, premium_faqs, premium_plans, tz, RESERVED_SLUGS
from ..utils import get_my_guilds, get_current_user, ensure_guild_doc, check_guild_permission as _check_guild_permission, guild_guard, login_required, is_premium, plugin_item_cap
from ..plugins import PLUGIN_LIST
from ..uploads import upload_embed_image, UploadError

dashboard_bp = Blueprint('dashboard', __name__)

# ── Guild picker ───────────────────────────────────────────────────────────
async def get_user_eligible_guilds(current_user, exclude_guild_id=None):
    """Guilds the user owns, is bot master of, or has admin in.

    Returns dicts with: id, name, icon_url, perm, is_bot_in_guild.
    Sorted Owner -> Bot Master -> Admin, then by name.
    """
    bot_guild_ids = {g.id for g in v.client.guilds}
    my_guilds = [
        g for g in await get_my_guilds()
        if not (exclude_guild_id and g.id == exclude_guild_id)
    ]

    # One query instead of one Guild.get() per guild
    configs = {
        c.id: c for c in
        await Guild.find({"_id": {"$in": [str(g.id) for g in my_guilds]}}).to_list()
    }

    eligible = []
    for guild in my_guilds:
        bot_master = False
        config = configs.get(str(guild.id))
        if config:
            bot_guild = v.client.get_guild(guild.id)
            member = bot_guild.get_member(current_user.id) if bot_guild else None
            if member:
                settings = config.settings
                bot_master = any(
                    str(role.id) in settings.admin_roles or
                    str(role.id) in settings.bot_masters
                    for role in member.roles
                )

        is_admin = int(guild.permissions) & 0x8 == 0x8
        if not (guild.is_owner or bot_master or is_admin):
            continue

        eligible.append({
            'id': guild.id,
            'name': guild.name,
            'icon_url': guild.icon_url,
            'perm': "Owner" if guild.is_owner else "Bot Master" if bot_master else "Admin",
            # "Go" (already set up) requires both: the bot is actually in the
            # Discord guild AND it has a config doc. A guild the bot left (or
            # whose doc was deleted/not yet synced) should read "Setup", not "Go".
            'is_bot_in_guild': guild.id in bot_guild_ids and str(guild.id) in configs,
        })

    perm_order = {'Owner': 0, 'Bot Master': 1, 'Admin': 2}
    eligible.sort(key=lambda x: (perm_order.get(x['perm'], 99), x['name']))
    return eligible

def _is_owner_or_admin(guild, user_id) -> bool:
    """The test a transfer target has to pass: the user owns the guild or has
    Discord Administrator there. Shared by the transfer picker and the route so
    the modal never offers a server the route will refuse."""
    if guild.owner_id == user_id:
        return True
    member = guild.get_member(user_id)
    return bool(member and member.guild_permissions.administrator)


@dashboard_bp.route("/dashboard")
@login_required
async def guilds():
    current_user = get_current_user()

    user_eligible_guilds = await get_user_eligible_guilds(current_user)

    guilds = [
        {
            **g,
            'btn_name': "Go"      if g['is_bot_in_guild'] else "Setup",
            'color':    "#5865F2" if g['is_bot_in_guild'] else "#36393f",
        }
        for g in user_eligible_guilds
    ]
    # bot-present servers first (stable sort keeps perm/name order within each group)
    guilds.sort(key=lambda x: not x['is_bot_in_guild'])

    return await render_template(
        "dashboard/guilds.html",
        user=current_user, guilds=guilds
    )


# ── Dashboard home ────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>")
@login_required
async def dashboard_home(guild_id):
    current_user = get_current_user()
    guild = v.client.get_guild(guild_id)
    session['guild_id'] = guild_id

    if guild is None:
        # Preselect this guild in Discord's bot-add picker, and send the browser back to REDIRECT_URI (the one URI actually registered
        # with Discord for this app - a one-off {URL_BASE}/dashboard here gets rejected as "Invalid OAuth2 redirect_uri"). state=guild_id
        # round-trips through the callback so it knows to send them to /dashboard/<guild_id> once the bot's been added, rather than treating this as a normal login.
        return redirect(
            f"{INVITE_URL}&guild_id={guild_id}"
            f"&response_type=code&redirect_uri={REDIRECT_URI}&state={guild_id}"
        )

    # Bot's in the guild but there's no config doc yet (never set up, or one that was deleted)
    # create it now instead of every plugin page below this 404'ing on a missing Guild.get().
    await ensure_guild_doc(guild)

    return await render_template(
        "dashboard/dashboard.html",
        user=current_user, guild=guild
    )


# ── Settings ──────────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/settings")
@guild_guard
async def settings(guild_id):
    current_user = get_current_user()
    guild = v.client.get_guild(guild_id)
    config = await Guild.get(str(guild.id))
    data = config.settings if config else SettingsConfig()
    return await render_template(
        "dashboard/settings.html",
        user=current_user, guild=guild, data=data, languages=langs, timezones=tz
    )


# ── Premium ───────────────────────────────────────────────────────────────────
@dashboard_bp.route("/dashboard/<int:guild_id>/premium")
@guild_guard
async def premium(guild_id):
    current_user = get_current_user()
    guild = v.client.get_guild(guild_id)
    config = await Guild.get(str(guild.id))
    prem_data = config.premium if config else PremiumConfig()

    # No premium yet: the plans / checkout page (index.html builds the cards from `plans`)
    if not prem_data.status:
        return await render_template(
            "dashboard/premium/index.html",
            user=current_user,
            guild=guild,
            data=prem_data,
            faqs=premium_faqs,
            plans=premium_plans,
            stripe_public_key=current_app.config.get('STRIPE_PUBLIC_KEY', '')
        )

    # Who paid for it (for a gift: who gave it)
    user = None
    if prem_data.user_id:
        try:
            user = v.client.get_user(int(prem_data.user_id))
        except (ValueError, TypeError):
            pass

    # Only the owner can transfer (transfer_premium_execute enforces it), so only they need the picker: servers the bot is in, the user owns / is Administrator of, and that don't already have premium (the route refuses those too)
    is_owner = guild.owner_id == current_user.id
    user_guilds = []
    if is_owner:
        eligible = await get_user_eligible_guilds(current_user=current_user, exclude_guild_id=guild_id)
        candidates = [
            g for g in eligible
            if (bot_guild := v.client.get_guild(g['id'])) and _is_owner_or_admin(bot_guild, current_user.id)
        ]
        target_docs = {
            d.id: d for d in
            await Guild.find({"_id": {"$in": [str(g['id']) for g in candidates]}}).to_list()
        }
        user_guilds = [
            g for g in candidates
            if (d := target_docs.get(str(g['id']))) and not d.premium.status
        ]

    # When it ends: Stripe writes period_end, the dev command writes code_expiry, and anything else falls back to subscribed_at plus the plan's length
    plan = prem_data.plan
    is_trial = plan == 'trial'
    expiry = prem_data.period_end or prem_data.code_expiry
    if not expiry and prem_data.subscribed_at:
        plan_days = {'trial': 30, 'monthly': 30, 'month': 30, 'yearly': 365, 'year': 365}.get(plan)
        if plan_days:
            expiry = prem_data.subscribed_at + timedelta(days=plan_days)

    next_bill = "Never"
    countdown = "0"
    is_expired = False

    if expiry:
        if not expiry.tzinfo:
            expiry = expiry.replace(tzinfo=timezone.utc)
        days_remaining = (expiry - datetime.now(timezone.utc)).days

        if days_remaining < 0:
            next_bill = "Expired"
            is_expired = True
            # Switch it off the first time anyone notices (this GET writes)
            if prem_data.active:
                prem_data.active = False
                prem_data.status = False
                await config.save()
        elif days_remaining == 0:
            next_bill = "Today"
        else:
            countdown = str(days_remaining)
            next_bill = expiry.strftime("%d %B %Y")
    elif is_trial:
        next_bill = "Trial (No expiry)"

    data = {
        **prem_data,
        'next_bill': next_bill,
        'countdown': countdown,
        'is_expired': is_expired,
        'is_trial': is_trial,
        'is_lifetime': plan == 'lifetime',
        'is_gifted': not prem_data.customer,
        'plan': plan,
        'user': {
            'avatar': user.avatar.url if user and hasattr(user, 'avatar') else '',
            'name': user.name if user else 'Unknown',
        },
    }

    return await render_template(
        "dashboard/premium/manage.html",
        user=current_user,
        guild=guild,
        data=data,
        plans=premium_plans,
        user_guilds=user_guilds,
        is_owner=is_owner
    )

@dashboard_bp.route("/dashboard/<int:guild_id>/premium/transfer", methods=["POST"])
@login_required
async def transfer_premium_execute(guild_id):
    """Execute premium transfer."""
    current_user = get_current_user()
    guild = v.client.get_guild(guild_id)
    
    # Authorize
    if guild.owner_id != current_user.id:
        return jsonify({'error': 'Only the guild owner can transfer premium'}), 403
    
    doc = await Guild.get(str(guild_id))
    if not doc or not doc.premium.status:
        return jsonify({'error': 'This guild does not have premium'}), 404

    # Every Stripe purchase records a customer; `/dev premium add` gifts never do
    if not doc.premium.customer:
        return jsonify({'error': "Gifted premium can't be transferred"}), 403

    data = await request.get_json()
    target_guild_id = data.get('target_guild_id')
    
    if not target_guild_id:
        return jsonify({'error': 'Target guild ID is required'}), 400
    
    target_guild = v.client.get_guild(int(target_guild_id))
    if not target_guild:
        return jsonify({'error': 'Target guild not found'}), 404
    
    # Check if user owns/has admin in target guild
    if not _is_owner_or_admin(target_guild, current_user.id):
        return jsonify({'error': 'You need Administrator permissions in the target guild'}), 403
    
    target_doc = await Guild.get(str(target_guild_id))
    if not target_doc:
        return jsonify({'error': 'Target guild config not found'}), 404
    
    if target_doc.premium.status:
        return jsonify({'error': 'Target guild already has premium'}), 400

    # Transfer the premium
    premium_data = doc.premium.copy()
    premium_data['transferred_from'] = str(guild_id)
    premium_data['transferred_at'] = datetime.now(timezone.utc)
    premium_data['original_user_id'] = premium_data.get('user_id')

    # Apply to target
    target_doc.premium = PremiumConfig(**premium_data)
    await target_doc.save()

    # Remove from source
    doc.premium = PremiumConfig()
    await doc.save()
    
    # Send notifications
    try:
        await v.push_notification(
            guild,
            'info',
            'Premium Transferred',
            f"Your premium has been transferred to **{target_guild.name}**"
        )
    except Exception as e:
        print(f"Failed to push premium-transfer notification for guild {guild_id}: {e}")
    
    try:
        await v.push_notification(
            target_guild,
            'info',
            'Premium Received! 🎉',
            f"You received a premium subscription from **{guild.name}**!"
        )
    except Exception as e:
        print(f"Failed to push premium-received notification for guild {target_doc.id}: {e}")
    
    return jsonify({'status': 'success', 'message': 'Premium transferred successfully'}), 200


# ── Notifications ─────────────────────────────────────────────────────────────
def _iso_utc(dt: datetime) -> str:
    """ISO-8601 in UTC with an explicit offset, so the browser converts it to
    the viewer's local time. Mongo can hand back naive datetimes; those are UTC."""
    dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return dt.isoformat()

@dashboard_bp.route("/dashboard/<int:guild_id>/notifications", methods=["GET", "POST", "DELETE"])
@guild_guard
async def notifications(guild_id):
    current_user = get_current_user()
    guild = v.client.get_guild(guild_id)
    guild_id_str = str(guild.id)

    def guild_notifs():
        # fresh query per use: Beanie's sort()/find() mutate the query object
        return Notification.find(Notification.guild_id == guild_id_str)

    if request.method == 'DELETE':
        res = await request.get_json()
        await guild_notifs().find(Notification.notification_id == res['id']).delete()
        return jsonify({'status': 'success', 'message': 'Successfully deleted notification'})

    if request.method == 'POST':
        res = await request.get_json()
        if res.get('mark_all_read'):
            await guild_notifs().find(Notification.read == False).update({"$set": {"read": True}})
        else:
            notif = await guild_notifs().find(Notification.notification_id == res['id']).first_or_none()
            if notif is None:
                return jsonify({'status': 'error', 'message': 'Notification not found'}), 404
            notif.read = bool(res['read'])
            await notif.save()
        return jsonify({'status': 'success', 'message': 'Successfully updated notifications'})

    # Newest first; the page groups them into days in the viewer's timezone.
    all_notifs = await guild_notifs().sort([(Notification.created_at, -1)]).to_list()
    data = [
        {
            'id': n.notification_id,
            'type': n.type,
            'title': n.title,
            'description': n.description,
            'fix': n.fix,
            'link': n.link,
            'user': n.user,
            'read': n.read,
            'created_at': _iso_utc(n.created_at),
        }
        for n in all_notifs
    ]

    return await render_template(
        "dashboard/notifications.html",
        user=current_user, guild=guild, data=data
    )

@dashboard_bp.route("/dashboard/<int:guild_id>/notifications/unread")
@guild_guard
async def notifications_unread(guild_id):
    """JSON for the navbar bell's poll: newest unread + total unread count."""
    return jsonify(await get_bell_notifications(guild_id))


@dashboard_bp.route("/dashboard/<int:guild_id>/data/post", methods=["POST"])
async def data_post(guild_id):
    """
    Catch-all endpoint for dashboard setting updates.
    JSON endpoint: every failure is a JSON error + HTTP status (no HTML login page).
    """
    if 'token' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    try:
        current_user = get_current_user()
    except Exception:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    # ── PERMISSION CHECK ──────────────────────────────────────────────────
    has_permission, permission_level = await _check_guild_permission(guild, current_user.id)
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
        'settings.moderator_roles': list,
    }
    
    ALLOWED_DASH_PREFIX = "Dash."

    DASHBOARD_PLUGIN_KEYS = [
        'welcome', 'moderation', 'verification', 'starboard', 'forms',
        'temporary_channels', 'ticketing', 'stats', 'leveling', 
        'birthdays', 'giveaways', 'economy',
    ]

    # Get the guild document once
    doc = await Guild.get(str(guild.id))
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
            
            deleted_count = (await Economy.find(Economy.guild_id == str(guild.id)).delete()).deleted_count
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

        # Reject writes into a disabled plugin - except its own status toggle,
        # which is how it gets turned back on.
        plugin_name = parts[0]
        is_status_toggle = len(parts) == 2 and parts[1] == 'status'
        if plugin_name in DASHBOARD_PLUGIN_KEYS and not is_status_toggle:
            plug_cfg = getattr(doc.dashboard, plugin_name, None)
            plug_status = (plug_cfg.get('status') if isinstance(plug_cfg, dict)
                           else getattr(plug_cfg, 'status', False))
            if not plug_status:
                return jsonify({
                    'status': 'error',
                    'message': f'The {plugin_name} plugin is disabled. Enable it first.',
                    'code': 'plugin_disabled',
                }), 409

        # Cap the economy shop by the guild's free / premium limit. The dashboard
        # writes either the whole array ("economy.shop") or one slot
        # ("economy.shop.<idx>") - guard both.
        if parts[:2] == ['economy', 'shop']:
            guild_premium = await is_premium(guild)
            cap = plugin_item_cap('economy', guild_premium)

            resulting_count = None
            if len(parts) == 2 and isinstance(val, list):
                resulting_count = len(val)
            elif len(parts) == 3 and parts[2].isdigit():
                existing = doc.dashboard.economy.shop
                resulting_count = max(len(existing), int(parts[2]) + 1)

            if resulting_count is not None and resulting_count > cap:
                msg = f"You've reached your limit of {cap} shop items."
                if not guild_premium:
                    msg += f" Upgrade to premium for up to {plugin_item_cap('economy', True)}."
                return jsonify({'status': 'error', 'message': msg, 'code': 'shop_cap'}), 409

        # Custom leaderboard URL: premium-only, must be a URL-safe slug that
        # isn't all digits (those collide with the /leaderboard/<guild_id> form)
        # and isn't already claimed by another guild. Empty or the guild's own
        # id is the "no custom URL" state and skips every check.
        if parts == ['leveling', 'leaderboard', 'url']:
            slug = str(val or '').strip().lower()
            if slug and slug != str(guild.id):
                if not await is_premium(guild):
                    return jsonify({
                        'status': 'error',
                        'message': 'Custom leaderboard URLs are a premium feature.',
                        'code': 'premium_only',
                    }), 403
                if slug.isdigit() or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,31}', slug):
                    return jsonify({
                        'status': 'error',
                        'message': 'URL must be 2-32 characters: lowercase letters, numbers and hyphens, and cannot be all numbers.',
                        'code': 'bad_slug',
                    }), 400
                if slug in RESERVED_SLUGS:
                    return jsonify({
                        'status': 'error',
                        'message': 'That leaderboard URL is reserved. Pick another.',
                        'code': 'slug_reserved',
                    }), 400
                clash = await Guild.find_one({
                    'dashboard.leveling.leaderboard.url': slug,
                    '_id': {'$ne': str(guild.id)},
                })
                if clash is not None:
                    return jsonify({
                        'status': 'error',
                        'message': 'That leaderboard URL is already taken.',
                        'code': 'slug_taken',
                    }), 409
            val = slug  # store the normalised value

        # ── ✅ FIX: Navigate through the DashConfig model ──────────────
        # Start with the dashboard object
        current = doc.dashboard
        
        # Navigate through all parts except the last one
        for part in parts[:-1]:
            if isinstance(current, list):
                try:
                    index = int(part)
                except ValueError:
                    return jsonify({
                        'status': 'error',
                        'message': f'Cannot navigate list with non-integer index: "{part}"'
                    }), 400

                if index < 0 or index >= len(current):
                    return jsonify({
                        'status': 'error',
                        'message': f'List index out of range: {index}'
                    }), 400

                current = current[index]

            elif isinstance(current, dict):
                if part not in current:
                    current[part] = {}
                current = current[part]

            elif hasattr(current, part):
                current = getattr(current, part)

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
    await doc.save()

    if audit_entries:
        print(f"[AUDIT] Guild {guild_id} modified by {current_user.id}: {', '.join(audit_entries)}")
    
    return jsonify({
        'status': 'success', 
        'message': 'Successfully updated data',
        'audit': audit_entries
    })


@dashboard_bp.route("/dashboard/<int:guild_id>/upload-image", methods=["POST"])
async def embed_upload_image(guild_id):
    """
    Uploads an embed image/thumbnail/icon to Cloudinary and returns its URL.
    The caller still has to save that URL onto the guild doc via /data/post -
    this route only handles turning a file into a hosted URL.
    """
    if 'token' not in session:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    try:
        current_user = get_current_user()
    except Exception:
        return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

    has_permission, permission_level = await _check_guild_permission(guild, current_user.id)
    if not has_permission:
        return jsonify({
            'status': 'error',
            'message': f'Permission denied: {permission_level}'
        }), 403

    files = await request.files
    file_storage = files.get('image')

    try:
        url = await upload_embed_image(file_storage, guild_id)
    except UploadError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        print(f"[embed_upload_image] Cloudinary upload failed for guild {guild_id}: {e}")
        return jsonify({'status': 'error', 'message': 'Upload failed. Try again.'}), 502

    return jsonify({'status': 'success', 'url': url})