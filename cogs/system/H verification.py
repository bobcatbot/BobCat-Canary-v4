import string
import asyncio
import random
import discord
from discord.ext import commands
from captcha.image import ImageCaptcha
from cogs.mod._utils.audit_log import audit_log
from modules import bot as v

class Verification(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client

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
            logs.add_field(name="Status", value=f"`{interaction.user.name}` has successfully passed verification.", inline=False)
        else:
            action_label = {"kick": "Kicked", "ban": "Banned"}.get(fail_action, "Kept Unverified")
            logs.add_field(name="Status", value=f"`{interaction.user.name}` has failed to pass verification.", inline=False)
            logs.add_field(name="Reason", value=f"Too many failed attempts. This user has been `{action_label}`.", inline=False)
        return logs

    def _build_captcha(self, captcha_text: str) -> tuple[discord.Embed, discord.File]:
        """Generates the captcha image and embed."""
        image = ImageCaptcha(width=280, height=90)
        image.write(captcha_text, "databases/CAPTCHA.png")

        embed = discord.Embed(
            title="Hello! Are you human? Let's find out!",
            description=(
                "**Please type the captcha below to be able to access this server!**"
                "\n\n**Additional Notes:**"
                "\nType out the traced colored characters from left to right."
                "\nIgnore the decoy characters spread around."
                "\nYou don't have to worry about upper/lower case."
                "\nYou have **5 attempts** to get it correct."
            )
        )
        embed.set_image(url="attachment://captcha.png")
        file = discord.File("databases/CAPTCHA.png", filename="captcha.png")
        return embed, file

    async def _apply_fail_action(self, interaction: discord.Interaction, fail_action: str):
        """Kicks or bans the user depending on the configured fail action."""
        if fail_action == "kick":
            await interaction.user.kick(reason="Failed to verify")
        elif fail_action == "ban":
            await interaction.user.ban(reason="Failed to verify")

    # ── Interaction ───────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") != "Verification":
            return

        verify_data = v.db.get_dash(interaction.guild.id)['verification']
        status = verify_data['status']
        chan = verify_data['channel']
        verify_role = verify_data['role']
        mode = verify_data['mode']
        fail_action = verify_data['failAction']

        # Status check before anything else
        if not status:
            return await interaction.response.send_message(
                "❌ The verification service has been disabled. Please contact your server owner.",
                ephemeral=True
            )

        # Role ID guard — if not configured yet, bail cleanly
        if not verify_role:
            return await interaction.response.send_message(
                "❌ Verification is not fully configured. Please contact your server owner.",
                ephemeral=True
            )

        role = await interaction.guild.fetch_role(int(verify_role))

        if interaction.user.id == interaction.guild.owner_id:
            return await interaction.response.send_message(
                embed=discord.Embed(description="❌ You are the server owner — you don't need to verify.", color=v.error),
                ephemeral=True
            )

        if role in interaction.user.roles:
            return await interaction.response.send_message(
                f"❌ {interaction.user.display_name}, you are already verified.",  # fixed typo
                ephemeral=True
            )

        # ── Generate captcha (shared by both dm and channel captcha modes) ───────────────────
        captcha_text = "".join(random.sample(string.ascii_letters + string.digits, 6))
        captcha_embed, captcha_file = self._build_captcha(captcha_text)

        # ── Instant ───────────────────────────────────────────────────────────
        if mode == "instant":
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "✅ You have been verified! You can now access the server channels.",
                ephemeral=True
            )
            logs = self._build_verification_log(interaction, passed=True)
            await audit_log(v.client, interaction, "Verification", logs)
            return

        # ── Captcha DM ────────────────────────────────────────────────────────
        if mode == "captcha_dm":
            try:
                dm = await interaction.user.create_dm()
            except discord.HTTPException:
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        description="❌ I wasn't able to DM you. Please open your DMs and try again.",
                        color=v.error
                    ),
                    ephemeral=True
                )

            # Hint button
            hint_view = discord.ui.View()
            hint_btn = discord.ui.Button(label="Hint", style=discord.ButtonStyle.blurple)
            async def hint_callback(i: discord.Interaction):
                await i.response.send_message(f"**Hint:** `{captcha_text}`", ephemeral=True, delete_after=5)
            hint_btn.callback = hint_callback
            hint_view.add_item(hint_btn)

            captcha_embed.set_footer(text="Verification period: 2 minutes")
            await dm.send(embed=captcha_embed, view=hint_view, file=captcha_file)

            # Tell user to check DMs
            notify_view = discord.ui.View()
            notify_view.add_item(discord.ui.Button(label="Verification Message", url=dm.jump_url))
            await interaction.response.send_message(
                embed=discord.Embed(description="**Starting verification... Check your DMs!**", color=v.style(interaction.guild.id)),
                view=notify_view,
                ephemeral=True
            )

            attempts_left = 5
            while attempts_left > 0:
                try:
                    msg = await v.client.wait_for(
                        "message",
                        # fixed: also filter to the DM channel so messages elsewhere don't trigger this
                        check=lambda m: m.author.id == interaction.user.id and isinstance(m.channel, discord.DMChannel),
                        timeout=120
                    )
                except asyncio.TimeoutError:
                    await dm.send(embed=discord.Embed(
                        title="Verification Timed Out",
                        description="You took too long to respond. Please start verification again.",
                        color=v.error
                    ))
                    return

                if msg.content.lower() == captcha_text.lower():
                    await interaction.user.add_roles(role)
                    await dm.send(embed=discord.Embed(
                        title="✅ You have been verified!",
                        description=f"You passed verification and can now access **{interaction.guild.name}**.",
                        color=v.success
                    ))
                    logs = self._build_verification_log(interaction, passed=True)
                    await audit_log(v.client, interaction, "Verification", logs)
                    return

                attempts_left -= 1
                if attempts_left > 0:
                    await dm.send(embed=discord.Embed(
                        title="❌ Incorrect",
                        description=f"Wrong answer. You have **{attempts_left}** attempt{'s' if attempts_left != 1 else ''} left.",
                        color=v.error
                    ))

            # Out of attempts
            fail_action_label = {"kick": "Kicked", "ban": "Banned"}.get(fail_action, "Kept Unverified")
            retry_msg = f"You can return to <#{chan}> and click Verify to try again." if fail_action == "unverified" else ""

            await dm.send(embed=discord.Embed(
                title="❌ Verification Failed",
                description=(
                    f"You failed verification in **{interaction.guild.name}**.\n"
                    f"**Reason:** Too many failed attempts.\n"
                    f"**Correct answer:** `{captcha_text}`\n"
                    f"{retry_msg}"
                ),
                color=v.error
            ))
            await self._apply_fail_action(interaction, fail_action)
            logs = self._build_verification_log(interaction, passed=False, fail_action=fail_action)
            await audit_log(v.client, interaction, "Verification", logs)
            return

        # ── Captcha Channel ───────────────────────────────────────────────────
        if mode == "captcha_channel":
            # State tracked outside the modal since modals are one-shot
            attempt_state = {"attempts_left": 5}

            # Capture needed vars for the modal closure
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
                            style=discord.InputTextStyle.short
                        ),
                        title="Captcha Verification",
                    )

                async def callback(self, modal_interaction: discord.Interaction):
                    answer = self.children[0].value.strip()

                    if answer.lower() == captcha_text.lower():
                        await _user.add_roles(_role)
                        await modal_interaction.response.send_message(
                            embed=discord.Embed(
                                title="✅ You have been verified!",
                                description=f"You passed verification and can now access **{_guild_name}**.",
                                color=v.success
                            ),
                            ephemeral=True
                        )
                        logs = self._build_verification_log(interaction, passed=True)
                        await audit_log(v.client, interaction, "Verification", logs)
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
                    fail_label = {"kick": "Kicked", "ban": "Banned"}.get(_fail_action, "Kept Unverified")
                    retry_msg  = f"You can return to <#{_chan}> and click Verify to try again." if _fail_action == "unverified" else ""

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
                    await audit_log(v.client, interaction, "Verification", logs)

            class CaptchaButton(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=None)

                @discord.ui.button(label="Answer", style=discord.ButtonStyle.green)
                async def answer(self, button: discord.ui.Button, btn_interaction: discord.Interaction):
                    await btn_interaction.response.send_modal(CaptchaModal())

            await interaction.response.send_message(
                embed=captcha_embed,
                view=CaptchaButton(),
                file=captcha_file,
                ephemeral=True
            )

def setup(client):
    client.add_cog(Verification(client))