import io
import hmac
import time
import hashlib
import string
import asyncio
import random
import discord
from discord.ext import commands, tasks
from captcha.image import ImageCaptcha
from cogs.mod._helpers import audit_log
from modules import bot as v
from modules.models import Guild
from datetime import datetime, timedelta

class Verification(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
        # Cache for active verifications to prevent duplicate attempts
        self.active_verifications = {}  # {user_id: timestamp}
        # Rate limit for verification button clicks
        self.button_cooldowns = {}  # {user_id: timestamp}
        
        # Config
        self.MAX_ATTEMPTS = 5
        self.TIMEOUT_SECONDS = 120
        self.COOLDOWN_SECONDS = 30
        self.CAPTCHA_LENGTH = 6

        # ✅ Start cleanup task
        self.cleanup_verifications.start()

    # ── Helper ───────────────────────────────────────────────────────────
    def _build_verification_log(self, interaction: discord.Interaction, passed: bool, fail_action: str = None) -> discord.Embed:
        """Builds the audit log embed for a verification result."""
        avatar = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
        logs = discord.Embed(
            title=v.t.msg(interaction.guild, "verification.log.title", user=interaction.user),
            color=v.style(interaction.guild.id)
        )
        logs.set_thumbnail(url=avatar)
        logs.add_field(name=v.t.msg(interaction.guild, "verification.log.user_field"), value=interaction.user.mention, inline=True)
        logs.add_field(
            name=v.t.msg(interaction.guild, "verification.log.created_field"),
            value=f"<t:{int(interaction.user.created_at.timestamp())}:R>",
            inline=True
        )
        if passed:
            logs.add_field(name=v.t.msg(interaction.guild, "verification.log.status_field"), value=v.t.msg(interaction.guild, "verification.log.passed_status", user=interaction.user.name), inline=False)
        else:
            action_label = v.t.table(interaction.guild, "verification.log.fail_actions").get(fail_action, v.t.msg(interaction.guild, "verification.log.fail_actions.unverified"))
            logs.add_field(name=v.t.msg(interaction.guild, "verification.log.status_field"), value=v.t.msg(interaction.guild, "verification.log.failed_status", user=interaction.user.name), inline=False)
            logs.add_field(name=v.t.msg(interaction.guild, "verification.log.reason_field"), value=v.t.msg(interaction.guild, "verification.log.reason_value", label=action_label), inline=False)
        logs.timestamp = datetime.now()
        return logs

    def _build_captcha(self, guild, captcha_text: str) -> tuple[discord.Embed, discord.File, io.BytesIO]:
        """Generates the captcha image and embed using BytesIO (no file collision!)."""
        image = ImageCaptcha(width=280, height=90)

        # Use BytesIO instead of writing to disk
        image_buffer = io.BytesIO()
        image.write(captcha_text, image_buffer)
        image_buffer.seek(0)

        embed = discord.Embed(
            title=v.t.msg(guild, "verification.captcha_embed.title"),
            description=v.t.msg(guild, "verification.captcha_embed.description", max_attempts=self.MAX_ATTEMPTS, timeout=self.TIMEOUT_SECONDS),
            color=discord.Color.blue()
        )
        embed.set_image(url="attachment://captcha.png")
        embed.set_footer(text=v.t.msg(guild, "verification.captcha_embed.footer", time=datetime.now().strftime('%H:%M')))
        file = discord.File(image_buffer, filename="captcha.png")
        return embed, file, image_buffer

    async def _apply_fail_action(self, interaction: discord.Interaction, fail_action: str):
        """Kicks, bans, or times out the user depending on the configured fail action."""
        if fail_action == "kick":
            try:
                await interaction.user.kick(reason="Failed to verify")
            except discord.Forbidden:
                pass
        elif fail_action == "ban":
            try:
                await interaction.user.ban(reason="Failed to verify")
            except discord.Forbidden:
                pass
        elif fail_action == "timeout":
            try:
                await interaction.user.timeout_for(
                    timedelta(minutes=5),
                    reason="Failed to verify"
                )
            except discord.Forbidden:
                pass

    def _get_fail_action_label(self, guild, action: str) -> str:
        """Get human-readable label for fail action."""
        return v.t.table(guild, "verification.fail_action_labels").get(action, v.t.msg(guild, "verification.fail_action_labels.unverified"))

    def _verify_signature(self, guild_id: str, user_id: str, exp: str) -> str:
        """HMAC over the fields carried by a captcha_web verify link. Shared by
        the bot (to sign) and the dashboard (to verify) so the two never drift."""
        payload = f"{guild_id}:{user_id}:{exp}".encode()
        return hmac.new(v.verify_secret, payload, hashlib.sha256).hexdigest()

    def build_verify_url(self, guild_id, user_id, ttl_seconds: int = 600) -> str:
        """Builds a signed, stateless captcha_web verification link — no token
        storage/cleanup needed, the link itself carries and proves its claims."""
        guild_id, user_id = str(guild_id), str(user_id)
        exp = str(int(time.time()) + ttl_seconds)
        sig = self._verify_signature(guild_id, user_id, exp)
        return f"{v.web_url}/verify?guild={guild_id}&user={user_id}&exp={exp}&hash={sig}"

    def verify_link_reason(self, guild_id: str, user_id: str, exp: str, sig: str) -> str:
        """Validates a captcha_web link, distinguishing *why* it failed —
        'ok' / 'expired' / 'invalid'. Used by the dashboard route; kept here
        so bot and dashboard share one implementation."""
        if not exp or not str(exp).isdigit():
            return "invalid"
        if int(exp) < int(time.time()):
            return "expired"
        expected = self._verify_signature(str(guild_id), str(user_id), str(exp))
        return "ok" if hmac.compare_digest(expected, sig or "") else "invalid"

    def check_verify_signature(self, guild_id: str, user_id: str, exp: str, sig: str) -> bool:
        """Validates a captcha_web link's signature and expiry. Used by the
        dashboard route; kept here so bot and dashboard share one implementation."""
        return self.verify_link_reason(guild_id, user_id, exp, sig) == "ok"

    # ── ✅ CLEANUP TASK ────────────────────────────────────────────────────────
    @tasks.loop(minutes=5)
    async def cleanup_verifications(self):
        """Clean up expired verification sessions to prevent memory leaks."""
        now = datetime.now()
        expired = []
        
        for user_id, ts in list(self.active_verifications.items()):
            if (now - ts).seconds > self.TIMEOUT_SECONDS + 60:  # Extra 60s grace
                expired.append(user_id)
        
        for user_id in expired:
            self.active_verifications.pop(user_id, None)
            self.button_cooldowns.pop(user_id, None)
        
        if expired:
            print(f"[Verification] Cleaned up {len(expired)} expired sessions")

    @cleanup_verifications.before_loop
    async def before_cleanup(self):
        await self.client.wait_until_ready()

    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.cleanup_verifications.cancel()

    # ── Interaction ───────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") != "Verification":
            return

        # ALWAYS defer first to prevent interaction expiration
        await interaction.response.defer(ephemeral=True)

        # Rate limit button clicks
        if interaction.user.id in self.button_cooldowns:
            elapsed = (datetime.now() - self.button_cooldowns[interaction.user.id]).total_seconds()
            if elapsed < 5:  # 5 second cooldown on button
                return await interaction.followup.send(
                    v.t.msg(interaction.guild, "verification.cooldown"),
                    ephemeral=True
                )
        self.button_cooldowns[interaction.user.id] = datetime.now()

        # Check if user already has an active verification
        if interaction.user.id in self.active_verifications:
            elapsed = (datetime.now() - self.active_verifications[interaction.user.id]).total_seconds()
            if elapsed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - elapsed)
                return await interaction.followup.send(
                    v.t.msg(interaction.guild, "verification.already_active", remaining=remaining),
                    ephemeral=True
                )

        # Mark as active
        self.active_verifications[interaction.user.id] = datetime.now()

        # Fetch config
        guild_doc = await Guild.get(str(interaction.guild.id))
        if guild_doc is None:
            return await interaction.followup.send(
                v.t.msg(interaction.guild, "verification.guild_not_found"),
                ephemeral=True
            )
            
        verify_data = guild_doc.dashboard.verification
        status = verify_data.status
        chan = verify_data.channel
        verify_role = verify_data.role
        mode = verify_data.mode or 'captcha_dm'
        fail_action = verify_data.failAction or 'unverified'
        log_channel = verify_data.get('logChannel')  # not a declared field yet - unused below

        # Status check before anything else
        if not status:
            return await interaction.followup.send(
                v.t.msg(interaction.guild, "verification.service_disabled"),
                ephemeral=True
            )

        # Role ID guard — if not configured yet, bail cleanly
        if not verify_role:
            return await interaction.followup.send(
                v.t.msg(interaction.guild, "verification.not_configured"),
                ephemeral=True
            )

        try:
            role = await interaction.guild.fetch_role(int(verify_role))
        except discord.NotFound:
            return await interaction.followup.send(
                v.t.msg(interaction.guild, "verification.role_missing"),
                ephemeral=True
            )

        if interaction.user.id == interaction.guild.owner_id:
            return await interaction.followup.send(
                embed=discord.Embed(description=v.t.msg(interaction.guild, "verification.owner_exempt"), color=v.success),
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.followup.send(
                v.t.msg(interaction.guild, "verification.already_verified", user=interaction.user.display_name),
                ephemeral=True
            )

        # ── Generate captcha ──
        captcha_text = "".join(random.sample(string.ascii_letters + string.digits, self.CAPTCHA_LENGTH))
        captcha_embed, captcha_file, _ = self._build_captcha(interaction.guild, captcha_text)

        # ── Instant ───────────────────────────────────────────────────────────
        if mode == "instant":
            try:
                await interaction.user.add_roles(role, reason="Instant verification")
            except discord.Forbidden:
                return await interaction.followup.send(
                    v.t.msg(interaction.guild, "verification.instant.no_role_perms"),
                    ephemeral=True
                )

            await interaction.followup.send(
                v.t.msg(interaction.guild, "verification.instant.success"),
                ephemeral=True
            )
            logs = self._build_verification_log(interaction, passed=True)
            await audit_log(interaction, "Verification", logs)
            
            # Clean up
            self.active_verifications.pop(interaction.user.id, None)
            return

        # ── Captcha DM ────────────────────────────────────────────────────────
        if mode == "captcha_dm":
            try:
                dm = await interaction.user.create_dm()
            except discord.HTTPException:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        description=v.t.msg(interaction.guild, "verification.dm.dm_failed"),
                        color=v.error
                    ),
                    ephemeral=True
                )

            # Hint button
            hint_view = discord.ui.View()
            hint_btn = discord.ui.Button(label=v.t.msg(interaction.guild, "verification.dm.hint_button"), style=discord.ButtonStyle.blurple)
            async def hint_callback(i: discord.Interaction):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message(v.t.msg(interaction.guild, "verification.helpers.not_your_verification"), ephemeral=True)
                await i.response.send_message(v.t.msg(interaction.guild, "verification.dm.hint_text", captcha=captcha_text), ephemeral=True, delete_after=10)
            hint_btn.callback = hint_callback
            hint_view.add_item(hint_btn)

            # Cancel button
            cancel_btn = discord.ui.Button(label=v.t.msg(interaction.guild, "verification.dm.cancel_button"), style=discord.ButtonStyle.red)
            async def cancel_callback(i: discord.Interaction):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message(v.t.msg(interaction.guild, "verification.helpers.not_your_verification"), ephemeral=True)
                self.active_verifications.pop(interaction.user.id, None)
                await i.response.send_message(v.t.msg(interaction.guild, "verification.dm.cancel_confirm"), ephemeral=True)
                await dm.send(v.t.msg(interaction.guild, "verification.helpers.cancelled"))
            cancel_btn.callback = cancel_callback
            hint_view.add_item(cancel_btn)

            captcha_embed.set_footer(text=v.t.msg(interaction.guild, "verification.dm.footer", seconds=self.TIMEOUT_SECONDS))
            await dm.send(embed=captcha_embed, view=hint_view, file=captcha_file)

            # Tell user to check DMs
            notify_view = discord.ui.View()
            notify_view.add_item(discord.ui.Button(label=v.t.msg(interaction.guild, "verification.dm.check_dms_button"), url=dm.jump_url))
            await interaction.followup.send(
                embed=discord.Embed(
                    description=v.t.msg(interaction.guild, "verification.dm.starting_description"),
                    color=v.style(interaction.guild.id)
                ),
                view=notify_view,
                ephemeral=True
            )

            attempts_left = self.MAX_ATTEMPTS
            while attempts_left > 0:
                try:
                    msg = await self.client.wait_for(
                        "message",
                        check=lambda m: m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel),
                        timeout=self.TIMEOUT_SECONDS
                    )
                except asyncio.TimeoutError:
                    await dm.send(embed=discord.Embed(
                        title=v.t.msg(interaction.guild, "verification.dm.timeout_title"),
                        description=v.t.msg(interaction.guild, "verification.dm.timeout_description"),
                        color=v.error
                    ))
                    self.active_verifications.pop(interaction.user.id, None)
                    return

                # Check if user typed "cancel"
                if msg.content.lower() in ["cancel", "stop", "quit"]:
                    await dm.send(v.t.msg(interaction.guild, "verification.helpers.cancelled"))
                    self.active_verifications.pop(interaction.user.id, None)
                    return

                if msg.content.lower() == captcha_text.lower():
                    try:
                        await interaction.user.add_roles(role, reason="Passed captcha verification")
                    except discord.Forbidden:
                        await dm.send(v.t.msg(interaction.guild, "verification.helpers.cannot_assign_role"))
                        self.active_verifications.pop(interaction.user.id, None)
                        return

                    await dm.send(embed=discord.Embed(
                        title=v.t.msg(interaction.guild, "verification.helpers.verified_title"),
                        description=v.t.msg(interaction.guild, "verification.helpers.verified_description", server=interaction.guild.name),
                        color=discord.Color.green()
                    ))
                    logs = self._build_verification_log(interaction, passed=True)
                    await audit_log(interaction, "Verification", logs)
                    self.active_verifications.pop(interaction.user.id, None)
                    return

                attempts_left -= 1
                if attempts_left > 0:
                    await dm.send(embed=discord.Embed(
                        title=v.t.msg(interaction.guild, "verification.helpers.incorrect_title"),
                        description=v.t.msg(interaction.guild, "verification.helpers.wrong_answer", count=attempts_left, plural='s' if attempts_left != 1 else ''),
                        color=v.error
                    ))

            # Out of attempts
            fail_label = self._get_fail_action_label(interaction.guild, fail_action)
            retry_msg = v.t.msg(interaction.guild, "verification.helpers.retry_hint", channel=chan) if fail_action == "unverified" else ""

            await dm.send(embed=discord.Embed(
                title=v.t.msg(interaction.guild, "verification.helpers.failed_title"),
                description=v.t.msg(interaction.guild, "verification.dm.failed_description", server=interaction.guild.name, answer=captcha_text, retry_msg=retry_msg),
                color=v.error
            ))
            await self._apply_fail_action(interaction, fail_action)
            logs = self._build_verification_log(interaction, passed=False, fail_action=fail_action)
            await audit_log(interaction, "Verification", logs)
            self.active_verifications.pop(interaction.user.id, None)
            return

        # ── Captcha Channel ───────────────────────────────────────────────────
        if mode == "captcha_channel":
            attempt_state = {"attempts_left": self.MAX_ATTEMPTS}

            _role        = role
            _fail_action = fail_action
            _chan        = chan
            _guild_name  = interaction.guild.name
            _user        = interaction.user

            class CaptchaModal(discord.ui.Modal):
                def __init__(self):
                    super().__init__(
                        discord.ui.InputText(
                            label=v.t.msg(interaction.guild, "verification.channel.modal_input_label"),
                            placeholder=v.t.msg(interaction.guild, "verification.channel.modal_placeholder"),
                            style=discord.InputTextStyle.short,
                            max_length=self.CAPTCHA_LENGTH + 5
                        ),
                        title=v.t.msg(interaction.guild, "verification.channel.modal_title"),
                    )

                async def callback(self, modal_interaction: discord.Interaction):
                    if modal_interaction.user.id != _user.id:
                        return await modal_interaction.response.send_message(
                            v.t.msg(interaction.guild, "verification.helpers.not_your_verification"),
                            ephemeral=True
                        )

                    answer = self.children[0].value.strip()

                    # Check for cancel
                    if answer.lower() in ["cancel", "stop", "quit"]:
                        await modal_interaction.response.send_message(
                            v.t.msg(interaction.guild, "verification.helpers.cancelled"),
                            ephemeral=True
                        )
                        self.active_verifications.pop(interaction.user.id, None)
                        return

                    if answer.lower() == captcha_text.lower():
                        try:
                            await _user.add_roles(_role, reason="Passed captcha verification")
                        except discord.Forbidden:
                            await modal_interaction.response.send_message(
                                v.t.msg(interaction.guild, "verification.helpers.cannot_assign_role"),
                                ephemeral=True
                            )
                            return

                        await modal_interaction.response.send_message(
                            embed=discord.Embed(
                                title=v.t.msg(interaction.guild, "verification.helpers.verified_title"),
                                description=v.t.msg(interaction.guild, "verification.helpers.verified_description", server=_guild_name),
                                color=discord.Color.green()
                            ),
                            ephemeral=True
                        )
                        logs = self._build_verification_log(interaction, passed=True)
                        await audit_log(interaction, "Verification", logs)
                        self.active_verifications.pop(interaction.user.id, None)
                        return

                    attempt_state["attempts_left"] -= 1
                    remaining = attempt_state["attempts_left"]

                    if remaining > 0:
                        await modal_interaction.response.send_message(
                            embed=discord.Embed(
                                title=v.t.msg(interaction.guild, "verification.helpers.incorrect_title"),
                                description=v.t.msg(interaction.guild, "verification.helpers.wrong_answer", count=remaining, plural='s' if remaining != 1 else '') + v.t.msg(interaction.guild, "verification.channel.wrong_answer_suffix"),
                                color=v.error
                            ),
                            ephemeral=True
                        )
                        return

                    # Out of attempts
                    fail_label = self._get_fail_action_label(interaction.guild, _fail_action)
                    retry_msg = v.t.msg(interaction.guild, "verification.helpers.retry_hint", channel=_chan) if _fail_action == "unverified" else ""

                    failed_embed = discord.Embed(
                        title=v.t.msg(interaction.guild, "verification.helpers.failed_title"),
                        description=v.t.msg(interaction.guild, "verification.channel.failed_description", server=_guild_name, answer=captcha_text, retry_msg=retry_msg),
                        color=v.error
                    )
                    await modal_interaction.response.send_message(embed=failed_embed, ephemeral=True)
                    await self._apply_fail_action(interaction, _fail_action)
                    logs = self._build_verification_log(interaction, passed=False, fail_action=_fail_action)
                    await audit_log(interaction, "Verification", logs)
                    self.active_verifications.pop(interaction.user.id, None)

            class CaptchaButton(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=self.TIMEOUT_SECONDS)

                @discord.ui.button(label=v.t.msg(interaction.guild, "verification.channel.answer_button"), style=discord.ButtonStyle.green)
                async def answer(self, button: discord.ui.Button, btn_interaction: discord.Interaction):
                    if btn_interaction.user.id != _user.id:
                        return await btn_interaction.response.send_message(
                            v.t.msg(interaction.guild, "verification.helpers.not_your_verification"),
                            ephemeral=True
                        )
                    await btn_interaction.response.send_modal(CaptchaModal())

                @discord.ui.button(label=v.t.msg(interaction.guild, "verification.channel.cancel_button"), style=discord.ButtonStyle.red)
                async def cancel(self, button: discord.ui.Button, btn_interaction: discord.Interaction):
                    if btn_interaction.user.id != _user.id:
                        return await btn_interaction.response.send_message(
                            v.t.msg(interaction.guild, "verification.helpers.not_your_verification"),
                            ephemeral=True
                        )
                    self.active_verifications.pop(interaction.user.id, None)
                    await btn_interaction.response.send_message(v.t.msg(interaction.guild, "verification.helpers.cancelled"), ephemeral=True)

            await interaction.followup.send(
                embed=captcha_embed,
                view=CaptchaButton(),
                file=captcha_file,
                ephemeral=True
            )

        # ── Captcha Web ───────────────────────────────────────────────────────
        if mode == "captcha_web":
            # Stateless: the link itself carries a signed guild/user/expiry,
            # so there's no pending state to babysit on this side — the
            # dashboard verifies the signature, gates on Discord OAuth login
            # matching this user, then runs Turnstile before adding the role.
            verify_url = self.build_verify_url(interaction.guild.id, interaction.user.id)

            view = discord.ui.View()
            view.add_item(discord.ui.Button(label=v.t.msg(interaction.guild, "verification.web.verify_button"), url=verify_url, style=discord.ButtonStyle.link))

            await interaction.followup.send(
                embed=discord.Embed(
                    title=v.t.msg(interaction.guild, "verification.web.title"),
                    description=v.t.msg(interaction.guild, "verification.web.description"),
                    color=v.style(interaction.guild.id)
                ),
                view=view,
                ephemeral=True
            )
            self.active_verifications.pop(interaction.user.id, None)
            return

def setup(client):
    client.add_cog(Verification(client))