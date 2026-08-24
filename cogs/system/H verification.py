import string
import asyncio
import random
import io
import discord
from discord.ext import commands, tasks
from captcha.image import ImageCaptcha
from cogs.mod.mod_utils.utils import audit_log
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
            title=f"{interaction.user} Verification Result",
            color=v.style(interaction.guild.id)
        )
        logs.set_thumbnail(url=avatar)
        logs.add_field(name="User", value=interaction.user.mention, inline=True)
        logs.add_field(
            name="Account Created",
            value=f"<t:{int(interaction.user.created_at.timestamp())}:R>",
            inline=True
        )
        if passed:
            logs.add_field(name="Status", value=f"✅ `{interaction.user.name}` has successfully passed verification.", inline=False)
        else:
            action_label = {"kick": "Kicked", "ban": "Banned", "timeout": "Timed Out", "unverified": "Kept Unverified"}.get(fail_action, "Kept Unverified")
            logs.add_field(name="Status", value=f"❌ `{interaction.user.name}` has failed to pass verification.", inline=False)
            logs.add_field(name="Reason", value=f"Too many failed attempts. This user has been `{action_label}`.", inline=False)
        logs.timestamp = datetime.now()
        return logs

    def _build_captcha(self, captcha_text: str) -> tuple[discord.Embed, discord.File, io.BytesIO]:
        """Generates the captcha image and embed using BytesIO (no file collision!)."""
        image = ImageCaptcha(width=280, height=90)
        
        # Use BytesIO instead of writing to disk
        image_buffer = io.BytesIO()
        image.write(captcha_text, image_buffer)
        image_buffer.seek(0)

        embed = discord.Embed(
            title="🔐 Human Verification Required",
            description=(
                "**Please type the captcha below to access this server!**"
                "\n\n**Instructions:**"
                "\n• Type the traced colored characters from left to right"
                "\n• Ignore the decoy characters spread around"
                "\n• Case doesn't matter (upper/lower both work)"
                f"\n• You have **{self.MAX_ATTEMPTS}** attempts"
                f"\n• You have **{self.TIMEOUT_SECONDS}** seconds"
            ),
            color=discord.Color.blue()
        )
        embed.set_image(url="attachment://captcha.png")
        embed.set_footer(text=f"Verification • {datetime.now().strftime('%H:%M')}")
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
                await interaction.user.timeout(
                    timedelta(minutes=5),
                    reason="Failed to verify"
                )
            except discord.Forbidden:
                pass

    def _get_fail_action_label(self, action: str) -> str:
        """Get human-readable label for fail action."""
        return {
            "kick": "Kicked",
            "ban": "Banned",
            "timeout": "Timed Out (5m)",
            "unverified": "Kept Unverified"
        }.get(action, "Kept Unverified")

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
                    "⏳ Please wait a moment before clicking again.",
                    ephemeral=True
                )
        self.button_cooldowns[interaction.user.id] = datetime.now()

        # Check if user already has an active verification
        if interaction.user.id in self.active_verifications:
            elapsed = (datetime.now() - self.active_verifications[interaction.user.id]).total_seconds()
            if elapsed < self.COOLDOWN_SECONDS:
                remaining = int(self.COOLDOWN_SECONDS - elapsed)
                return await interaction.followup.send(
                    f"⏳ You already have an active verification. Please wait **{remaining}s** or check your DMs.",
                    ephemeral=True
                )
        
        # Mark as active
        self.active_verifications[interaction.user.id] = datetime.now()

        # Fetch config
        guild_doc = Guild.get(str(interaction.guild.id)).run()
        if guild_doc is None:
            return await interaction.followup.send(
                "❌ Guild configuration not found. Please contact an admin.",
                ephemeral=True
            )
            
        verify_data = guild_doc.dashboard.verification
        status = verify_data.get('status', False)
        chan = verify_data.get('channel')
        verify_role = verify_data.get('role')
        mode = verify_data.get('mode', 'captcha_dm')
        fail_action = verify_data.get('failAction', 'unverified')
        log_channel = verify_data.get('logChannel')

        # Status check before anything else
        if not status:
            return await interaction.followup.send(
                "❌ The verification service has been disabled. Please contact your server owner.",
                ephemeral=True
            )

        # Role ID guard — if not configured yet, bail cleanly
        if not verify_role:
            return await interaction.followup.send(
                "❌ Verification is not fully configured. Please contact your server owner.",
                ephemeral=True
            )

        try:
            role = await interaction.guild.fetch_role(int(verify_role))
        except discord.NotFound:
            return await interaction.followup.send(
                "❌ The verification role no longer exists. Please contact your server owner.",
                ephemeral=True
            )

        if interaction.user.id == interaction.guild.owner_id:
            return await interaction.followup.send(
                embed=discord.Embed(description="👑 You are the server owner — you don't need to verify.", color=v.success),
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.followup.send(
                f"✅ {interaction.user.display_name}, you are already verified.",
                ephemeral=True
            )

        # ── Generate captcha ──
        captcha_text = "".join(random.sample(string.ascii_letters + string.digits, self.CAPTCHA_LENGTH))
        captcha_embed, captcha_file, _ = self._build_captcha(captcha_text)

        # ── Instant ───────────────────────────────────────────────────────────
        if mode == "instant":
            try:
                await interaction.user.add_roles(role, reason="Instant verification")
            except discord.Forbidden:
                return await interaction.followup.send(
                    "❌ I don't have permission to assign roles. Please contact an admin.",
                    ephemeral=True
                )
            
            await interaction.followup.send(
                "✅ You have been verified! You can now access the server channels.",
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
                        description="❌ I wasn't able to DM you. Please open your DMs and try again.",
                        color=v.error
                    ),
                    ephemeral=True
                )

            # Hint button
            hint_view = discord.ui.View()
            hint_btn = discord.ui.Button(label="💡 Hint", style=discord.ButtonStyle.blurple)
            async def hint_callback(i: discord.Interaction):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message("This isn't your verification!", ephemeral=True)
                await i.response.send_message(f"**Hint:** `{captcha_text}`", ephemeral=True, delete_after=10)
            hint_btn.callback = hint_callback
            hint_view.add_item(hint_btn)

            # Cancel button
            cancel_btn = discord.ui.Button(label="❌ Cancel", style=discord.ButtonStyle.red)
            async def cancel_callback(i: discord.Interaction):
                if i.user.id != interaction.user.id:
                    return await i.response.send_message("This isn't your verification!", ephemeral=True)
                self.active_verifications.pop(interaction.user.id, None)
                await i.response.send_message("Verification cancelled.", ephemeral=True)
                await dm.send("❌ Verification cancelled.")
            cancel_btn.callback = cancel_callback
            hint_view.add_item(cancel_btn)

            captcha_embed.set_footer(text=f"Verification period: {self.TIMEOUT_SECONDS} seconds")
            await dm.send(embed=captcha_embed, view=hint_view, file=captcha_file)

            # Tell user to check DMs
            notify_view = discord.ui.View()
            notify_view.add_item(discord.ui.Button(label="📬 Check DMs", url=dm.jump_url))
            await interaction.followup.send(
                embed=discord.Embed(
                    description="📬 **Starting verification... Check your DMs!**",
                    color=v.style(interaction.guild.id)
                ),
                view=notify_view,
                ephemeral=True
            )

            attempts_left = self.MAX_ATTEMPTS
            while attempts_left > 0:
                try:
                    msg = await v.client.wait_for(
                        "message",
                        check=lambda m: m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel),
                        timeout=self.TIMEOUT_SECONDS
                    )
                except asyncio.TimeoutError:
                    await dm.send(embed=discord.Embed(
                        title="⏰ Verification Timed Out",
                        description=f"You took too long to respond. Please start verification again.",
                        color=v.error
                    ))
                    self.active_verifications.pop(interaction.user.id, None)
                    return

                # Check if user typed "cancel"
                if msg.content.lower() in ["cancel", "stop", "quit"]:
                    await dm.send("❌ Verification cancelled.")
                    self.active_verifications.pop(interaction.user.id, None)
                    return

                if msg.content.lower() == captcha_text.lower():
                    try:
                        await interaction.user.add_roles(role, reason="Passed captcha verification")
                    except discord.Forbidden:
                        await dm.send("❌ I couldn't assign the verification role. Please contact an admin.")
                        self.active_verifications.pop(interaction.user.id, None)
                        return
                    
                    await dm.send(embed=discord.Embed(
                        title="✅ You have been verified!",
                        description=f"You passed verification and can now access **{interaction.guild.name}**.",
                        color=discord.Color.green()
                    ))
                    logs = self._build_verification_log(interaction, passed=True)
                    await audit_log(interaction, "Verification", logs)
                    self.active_verifications.pop(interaction.user.id, None)
                    return

                attempts_left -= 1
                if attempts_left > 0:
                    await dm.send(embed=discord.Embed(
                        title="❌ Incorrect",
                        description=f"Wrong answer. You have **{attempts_left}** attempt{'s' if attempts_left != 1 else ''} left.",
                        color=v.error
                    ))

            # Out of attempts
            fail_label = self._get_fail_action_label(fail_action)
            retry_msg = f"🔄 You can return to <#{chan}> and click Verify to try again." if fail_action == "unverified" else ""

            await dm.send(embed=discord.Embed(
                title="❌ Verification Failed",
                description=(
                    f"You failed verification in **{interaction.guild.name}**.\n"
                    f"**Reason:** Too many failed attempts.\n"
                    f"**Correct answer:** `{captcha_text}`\n\n"
                    f"{retry_msg}"
                ),
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
                            label="Enter the captcha code",
                            placeholder="Type the characters you see...",
                            style=discord.InputTextStyle.short,
                            max_length=self.CAPTCHA_LENGTH + 5
                        ),
                        title="🔐 Captcha Verification",
                    )

                async def callback(self, modal_interaction: discord.Interaction):
                    if modal_interaction.user.id != _user.id:
                        return await modal_interaction.response.send_message(
                            "This isn't your verification!",
                            ephemeral=True
                        )
                    
                    answer = self.children[0].value.strip()

                    # Check for cancel
                    if answer.lower() in ["cancel", "stop", "quit"]:
                        await modal_interaction.response.send_message(
                            "❌ Verification cancelled.",
                            ephemeral=True
                        )
                        self.active_verifications.pop(interaction.user.id, None)
                        return

                    if answer.lower() == captcha_text.lower():
                        try:
                            await _user.add_roles(_role, reason="Passed captcha verification")
                        except discord.Forbidden:
                            await modal_interaction.response.send_message(
                                "❌ I couldn't assign the verification role. Please contact an admin.",
                                ephemeral=True
                            )
                            return
                        
                        await modal_interaction.response.send_message(
                            embed=discord.Embed(
                                title="✅ You have been verified!",
                                description=f"You passed verification and can now access **{_guild_name}**.",
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
                                title="❌ Incorrect",
                                description=f"Wrong answer. You have **{remaining}** attempt{'s' if remaining != 1 else ''} left.\nClick **Answer** to try again.",
                                color=v.error
                            ),
                            ephemeral=True
                        )
                        return

                    # Out of attempts
                    fail_label = self._get_fail_action_label(_fail_action)
                    retry_msg = f"🔄 You can return to <#{_chan}> and click Verify to try again." if _fail_action == "unverified" else ""

                    failed_embed = discord.Embed(
                        title="❌ Verification Failed",
                        description=(
                            f"You failed verification in **{_guild_name}**.\n"
                            f"**Reason:** Too many failed attempts.\n"
                            f"**Correct answer:** `{captcha_text}`\n"
                            f"{retry_msg}"
                        ),
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

                @discord.ui.button(label="🔑 Answer", style=discord.ButtonStyle.green)
                async def answer(self, button: discord.ui.Button, btn_interaction: discord.Interaction):
                    if btn_interaction.user.id != _user.id:
                        return await btn_interaction.response.send_message(
                            "This isn't your verification!",
                            ephemeral=True
                        )
                    await btn_interaction.response.send_modal(CaptchaModal())

                @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
                async def cancel(self, button: discord.ui.Button, btn_interaction: discord.Interaction):
                    if btn_interaction.user.id != _user.id:
                        return await btn_interaction.response.send_message(
                            "This isn't your verification!",
                            ephemeral=True
                        )
                    self.active_verifications.pop(interaction.user.id, None)
                    await btn_interaction.response.send_message("❌ Verification cancelled.", ephemeral=True)

            await interaction.followup.send(
                embed=captcha_embed,
                view=CaptchaButton(),
                file=captcha_file,
                ephemeral=True
            )

def setup(client):
    client.add_cog(Verification(client))