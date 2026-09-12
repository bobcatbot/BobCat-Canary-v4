import copy
import traceback
import aiohttp
import discord
from quart import Blueprint, jsonify, render_template, request, session, url_for

from modules import bot as v
from modules.models import Guild, VerificationConfig
from cogs.mod._helpers import audit_log
from ...utils import bearer_client, plugin_guard
from ...config import OAUTH_URL, TURNSTILE_SITE_KEY, TURNSTILE_SECRET_KEY

verification_bp = Blueprint('verification', __name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

@verification_bp.route("/dashboard/<int:guild_id>/verification", methods=['GET'])
@plugin_guard('verification')
async def verify(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return await render_template("error/404.html"), 404

    guild_doc = await Guild.get(str(guild.id))
    config = guild_doc.dashboard.verification if guild_doc else None

    return await render_template(
        "dashboard/plugins/verification.html",
        user=current_user,
        guild=guild,
        data=config
    )


@verification_bp.route("/dashboard/<int:guild_id>/verification/publish", methods=['POST'])
@plugin_guard('verification')
async def verify_publish(guild_id):
    """Publish or update the verification message."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    data = await request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    # Validate required data
    if not data.get('embed'):
        return jsonify({'status': 'error', 'message': 'Embed data is required'}), 400

    # Get the guild document
    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    verification_config = config.dashboard.verification

    async def publish():
        try:
            embed = discord.Embed.from_dict(data.get('embed', {}))
            btn_data = data.get('btn', {})
            
            style_map = {
                'secondary': discord.ButtonStyle.gray,
                'blurple': discord.ButtonStyle.blurple,
                'danger': discord.ButtonStyle.red,
                'success': discord.ButtonStyle.green,
            }
            style = style_map.get(btn_data.get('color', 'blurple'), discord.ButtonStyle.blurple)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(
                emoji=btn_data.get('emoji') or None,
                label=btn_data.get('title', 'Verify'),
                style=style,
                custom_id='Verification'
            ))

            # Check if already published
            if verification_config.message_published:
                channel_id = verification_config.channel
                message_id = verification_config.message_id
                if channel_id and message_id:
                    channel = guild.get_channel(int(channel_id))
                    if channel:
                        try:
                            msg = await channel.fetch_message(int(message_id))
                            await msg.edit(embed=embed, view=view)
                            print(f"Updated verification message for guild {guild_id}")
                            return
                        except discord.NotFound:
                            print(f"Verification message not found for guild {guild_id}, recreating...")
                        except discord.Forbidden:
                            print(f"No permissions to edit message in guild {guild_id}")
                            return
                        except Exception as e:
                            print(f"Error editing verification message: {e}")
                            return

            # Get or create verification role
            role_id = verification_config.role
            role = guild.get_role(int(role_id)) if role_id else None
            if role is None:
                try:
                    role = await guild.create_role(
                        name='Verified',
                        reason='Enabled verification system'
                    )
                    config.dashboard.verification.role = str(role.id)
                    await config.save()
                    print(f"Created Verified role for guild {guild_id}")
                except discord.Forbidden:
                    print(f"No permissions to create role in guild {guild_id}")
                    return
                except Exception as e:
                    print(f"Error creating role: {e}")
                    return

            # Get or create verification channel
            channel_id = verification_config.channel
            channel = guild.get_channel(int(channel_id)) if channel_id else None
            if channel is None:
                try:
                    channel = await guild.create_text_channel(
                        'verification',
                        reason='Enabled verification system',
                        overwrites={
                            guild.default_role: discord.PermissionOverwrite(
                                read_messages=True,
                                send_messages=False,
                                read_message_history=True
                            ),
                            role: discord.PermissionOverwrite(
                                read_messages=True,
                                send_messages=False,
                                read_message_history=True
                            ),
                        }
                    )
                    config.dashboard.verification.channel = str(channel.id)
                    await config.save()
                    print(f"Created verification channel for guild {guild_id}")
                except discord.Forbidden:
                    print(f"No permissions to create channel in guild {guild_id}")
                    return
                except Exception as e:
                    print(f"Error creating channel: {e}")
                    return

            # Set permissions
            try:
                await channel.set_permissions(
                    guild.default_role,
                    overwrite=discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=False
                    )
                )
                await channel.set_permissions(
                    role,
                    overwrite=discord.PermissionOverwrite(
                        read_messages=False,
                        send_messages=False
                    )
                )
            except discord.Forbidden:
                print(f"Could not set permissions in guild {guild_id}")
            except Exception as e:
                print(f"Error setting permissions: {e}")
            
            try:
                await guild.default_role.edit(
                    reason="Verification system enabled",
                    permissions=discord.Permissions(read_messages=False)
                )
            except discord.Forbidden:
                print(f"Could not edit default role in guild {guild_id}")
            except Exception as e:
                print(f"Error editing default role: {e}")

            if role.id == int(verification_config.role or 0):
                try:
                    await role.edit(
                        reason="Verification system enabled",
                        permissions=discord.Permissions(read_messages=True)
                    )
                except discord.Forbidden:
                    print(f"Could not edit Verified role in guild {guild_id}")
                except Exception as e:
                    print(f"Error editing Verified role: {e}")

            # Send the verification message
            try:
                msg = await channel.send(embed=embed, view=view)
                
                # Save message ID and published status
                config.dashboard.verification.message_id = str(msg.id)
                config.dashboard.verification.message_published = True
                config.updated_at = discord.utils.utcnow()
                await config.save()
                print(f"Published verification message for guild {guild_id}")
            except discord.Forbidden:
                print(f"No permissions to send message in guild {guild_id}")
            except Exception as e:
                print(f"Error sending verification message: {e}")

        except Exception as e:
            print(f"Error in publish task for guild {guild_id}: {e}")
            traceback.print_exc()

    v.client.loop.create_task(publish())
    return jsonify({'status': 'success', 'message': 'Publishing verification message in background...'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/unpublish", methods=['POST'])
@plugin_guard('verification')
async def verify_unpublish(guild_id):
    """Delete the verification message."""
    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    verification_config = config.dashboard.verification

    async def unpublish():
        try:
            channel_id = verification_config.channel
            message_id = verification_config.message_id
            
            if channel_id and message_id:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        msg = await channel.fetch_message(int(message_id))
                        await msg.delete()
                        print(f"Deleted verification message for guild {guild_id}")
                    except discord.NotFound:
                        print(f"Verification message not found for guild {guild_id}")
                    except discord.Forbidden:
                        print(f"No permissions to delete message in guild {guild_id}")
                    except Exception as e:
                        print(f"Error deleting verification message: {e}")

            # Update dashboard
            config.dashboard.verification.message_published = False
            config.dashboard.verification.message_id = None
            config.updated_at = discord.utils.utcnow()
            await config.save()
            print(f"Unpublished verification for guild {guild_id}")
        
        except Exception as e:
            print(f"Error in unpublish task for guild {guild_id}: {e}")
            traceback.print_exc()

    v.client.loop.create_task(unpublish())
    return jsonify({'status': 'success', 'message': 'Unpublishing verification message in background...'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/update", methods=['POST'])
@plugin_guard('verification')
async def verify_update(guild_id):
    """Update a specific verification setting."""
    data = await request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No data provided'}), 400

    guild = v.client.get_guild(guild_id)
    if guild is None:
        return jsonify({'status': 'error', 'message': 'Guild not found'}), 404

    config = await Guild.get(str(guild.id))
    if config is None:
        return jsonify({'status': 'error', 'message': 'Guild config not found'}), 404

    key = data.get('key')
    value = data.get('value')

    if not key:
        return jsonify({'status': 'error', 'message': 'No key provided'}), 400

    # Handle nested keys like "message.embed.title"
    parts = key.split('.')
    current = config.dashboard.verification
    
    for part in parts[:-1]:
        if isinstance(current, dict):
            if part not in current:
                current[part] = {}
            current = current[part]
        else:
            current = getattr(current, part, {})
    
    final = parts[-1]
    if isinstance(current, dict):
        current[final] = value
    else:
        setattr(current, final, value)
    
    config.updated_at = discord.utils.utcnow()
    await config.save()

    print(f"Updated verification setting {key} for guild {guild_id}")
    return jsonify({'status': 'success', 'message': 'Successfully updated verification settings'})

# ── Public captcha_web verification page ────────────────────────────────────
# End-user facing (no login/plugin_guard on entry — the point of this route
# IS to log an arbitrary Discord user in), reached via the signed link the
# Verification cog hands out for the captcha_web mode.

class _LogShim:
    """Minimal ctx-like object so the Verification cog's own embed builder
    and the shared audit_log helper (both written for a discord.Interaction)
    can be reused as-is from this HTTP route."""
    def __init__(self, guild, user):
        self.guild = guild
        self.user = user


async def _verify_turnstile(token: str, remote_ip: str | None) -> bool:
    if not TURNSTILE_SECRET_KEY or not token:
        return False
    payload = {"secret": TURNSTILE_SECRET_KEY, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(TURNSTILE_VERIFY_URL, data=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                return bool(data.get("success"))
    except Exception:
        return False

def _verify_link_params(source):
    return source.get('guild'), source.get('user'), source.get('exp'), source.get('hash')

async def _resolve_verify_link(guild_id, user_id, exp, sig):
    """Shared validation for GET and POST: signature/expiry, guild/member
    existence, and that verification is actually configured for this guild.

    Returns (state, context) where state is None on success and context
    carries whatever the caller needs (error message, or the resolved
    guild/member/role for a successful resolution).
    """
    verification_cog = v.client.get_cog('Verification')
    if not verification_cog or not (guild_id and user_id and exp and sig):
        return "invalid", {}

    reason = verification_cog.verify_link_reason(guild_id, user_id, exp, sig)
    if reason != "ok":
        return reason, {}  # 'expired' or 'invalid'

    guild = v.client.get_guild(int(guild_id))
    if guild is None:
        return "invalid", {}

    member = guild.get_member(int(user_id))
    if member is None:
        return "invalid", {"message": "You're no longer a member of this server."}

    guild_doc = await Guild.get(str(guild_id))
    verify_data = guild_doc.dashboard.verification if guild_doc else VerificationConfig()

    if not verify_data.status or verify_data.mode != 'captcha_web':
        return "disabled", {}

    role_id = verify_data.role
    role = guild.get_role(int(role_id)) if role_id else None
    if role is None:
        return "invalid", {"message": "Verification isn't fully configured for this server. Please contact a server admin."}

    if role in member.roles:
        return "already", {"guild": guild}

    return None, {"guild": guild, "member": member, "role": role}

@verification_bp.route("/verify", methods=["GET", "POST"])
async def public_verify():
    guild_id, user_id, exp, sig = _verify_link_params(request.args if request.method == "GET" else await request.form)

    state, ctx = await _resolve_verify_link(guild_id, user_id, exp, sig)
    if state:
        return await render_template("verify.html", state=state, logInWithDiscord=OAUTH_URL, **ctx)

    guild, member = ctx["guild"], ctx["member"]

    # ── Not logged in — send them to Discord OAuth, then straight back here ──
    if "token" not in session:
        session['redirect'] = request.url
        return await render_template(
            "verify.html", state="login", guild=guild,
            login_url=url_for('auth.login'), logInWithDiscord=OAUTH_URL,
        )

    # ── Logged in as the wrong account for this link ──
    # Navbar.html expects the logged-in user under "user" — reused as-is
    # (Zenora User object: .id/.username/.avatar_url, not dict-subscriptable).
    user = bearer_client().get_current_user()
    if str(user.id) != str(user_id):
        return await render_template(
            "verify.html", state="mismatch", user=user, guild=guild,
            logout_url=url_for('auth.logout'), logInWithDiscord=OAUTH_URL,
        )

    if request.method == "GET":
        return await render_template(
            "verify.html", state="challenge", user=user, guild=guild,
            site_key=TURNSTILE_SITE_KEY, verify_url=url_for('verification.public_verify'),
            guild_id=guild_id, user_id=user_id, exp=exp, sig=sig, logInWithDiscord=OAUTH_URL,
        )

    # ── POST: Turnstile round-trip ──
    form = await request.form
    turnstile_token = form.get("cf-turnstile-response")
    passed = await _verify_turnstile(turnstile_token, request.remote_addr)

    if not passed:
        return await render_template(
            "verify.html", state="challenge", user=user, guild=guild,
            site_key=TURNSTILE_SITE_KEY, verify_url=url_for('verification.public_verify'),
            error="That check didn't pass — please try again.",
            guild_id=guild_id, user_id=user_id, exp=exp, sig=sig, logInWithDiscord=OAUTH_URL,
        )

    role = ctx["role"]
    try:
        await member.add_roles(role, reason="Passed web verification")
    except discord.Forbidden:
        return await render_template(
            "verify.html", state="invalid", user=user, guild=guild, logInWithDiscord=OAUTH_URL,
            message="I couldn't assign the verification role. Please contact a server admin.",
        )

    shim = _LogShim(guild, member)
    verification_cog = v.client.get_cog('Verification')
    if verification_cog:
        logs = verification_cog._build_verification_log(shim, passed=True)
        await audit_log(shim, "Verification", logs)

    return await render_template("verify.html", state="success", user=user, guild=guild, logInWithDiscord=OAUTH_URL)