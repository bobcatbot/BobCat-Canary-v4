import asyncio
import discord
import random, string
from modules import bot as v
from discord.ext import commands
from cogs.mod._utils.audit_log import audit_log
from captcha.image import ImageCaptcha

class Verification(commands.Cog):
    def __init__(self, client):
        self.client: discord.Client = client
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") == "Verification":
            verify_data = v.db.get_dash(interaction.guild.id)['verification']
            status = verify_data['status']
            chan = verify_data['channel']
            verifyRole = verify_data['role']
            mode = verify_data['mode']
            failAction = verify_data['failAction']

            role = await interaction.guild.fetch_role((int(verifyRole)))

            if not status:
                return await interaction.response.send_message("❌ The verification service has been disabled. Please contact your server owner.", ephemeral=True)
            
            if interaction.user.id == interaction.guild.owner_id:
                error = discord.Embed(description="❌ You are the owner, why would an owner try to verify?", color=v.error)
                return await interaction.response.send_message(embed=error, ephemeral=True)
            
            if role in interaction.user.roles:
                return await interaction.response.send_message(f"{interaction.user.display_name} you aleady have verified", ephemeral=True)
        
            if mode == "instant":
                await interaction.user.add_roles(role)
                await interaction.response.send_message("You have been verified. You now can access the server channels.", ephemeral=True)

                logs = discord.Embed(title=f"{interaction.user} Verification Result", color=v.style(interaction.guild.id))
                try:
                    logs.set_thumbnail(url=interaction.user.avatar.url)
                except AttributeError:
                    logs.set_thumbnail(url=interaction.user.default_avatar.url)
                logs.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
                logs.add_field(name="Creation", value=f"<t:{f'{interaction.user.created_at.timestamp()}'.split('.')[0]}:R>", inline=True)
                logs.add_field(name="Status", value=f"`{interaction.user.name}` has successfully passed verification.", inline=False)
                await audit_log(v.client, interaction, "Verification", logs)
                return
            ###
            
            # Captcha
            text = string.ascii_letters + string.digits
            author = interaction.user
            code = "".join(random.sample(text, 6))
            
            image = ImageCaptcha(width=280, height=90)
            captcha_text = code
            image.write(captcha_text, "databases/CAPTCHA.png")
            
            captchaEmbed = discord.Embed(
                title="Hello! Are you human? Let's find out!",
                description=(
                    "**Please type the captcha below to be able to access this server!**"
                    "\n\n**Additional Notes:**"
                    "\nType out the traced colored characters from left to right."
                    "\nIgnore the decoy characters spread-around."
                    "\nYou don't have to respect characters cases (upper/lower case)!"
                    "\nYou have 5 attempts to get it correct."                
                )
            )
            captchaEmbed.set_image(url="attachment://captcha.png")
                    
            file = discord.File("databases/CAPTCHA.png", filename="captcha.png")

            if mode == "captcha_dm":
                try:
                    dm = await interaction.user.create_dm()
                    
                    captchaEmbed.set_footer(text="Verification Period: 2 minutes")
                    view = discord.ui.View()
                    hint_button = discord.ui.Button(label="Hint", style=discord.ButtonStyle.blurple, custom_id="hint")
                    async def hint_callback(interaction: discord.Interaction):
                        await interaction.response.send_message(f"**Hint:** {captcha_text}", ephemeral=True, delete_after=1)
                    hint_button.callback = hint_callback
                    view.add_item(hint_button)

                    await dm.send(embed=captchaEmbed, view=view, file=file)
                    
                    em = discord.Embed(description='**Starting verification... Check your dms!**', color=v.style(interaction.guild.id))
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Verification Message", url=f"{dm.jump_url}"))
                    await interaction.response.send_message(embed=em, view=view, ephemeral=True)

                    attempts_left = 5
                    while attempts_left > 0:
                        try:
                            msg = await v.client.wait_for(
                                "message", 
                                check=lambda user: user.author.id == interaction.user.id, 
                                timeout=120
                            )
                        except asyncio.TimeoutError:
                            await dm.send(
                                embed=discord.Embed(
                                    title="Verification Timed Out",
                                    description="You took too long to respond. Please start verification again.",
                                    color=v.error
                                )
                            )
                            await dm.close()
                            return  # ✅ STOP after timeout
                        
                        if f"{msg.content}".lower() == f"{captcha_text}".lower():
                            await author.add_roles(role)
                            
                            captchaCorrect = discord.Embed(
                                title="You have been verified!",
                                description=f"You passed the verification successfully. You can now access {interaction.guild.name}"
                            )
                            await dm.send(embed=captchaCorrect)
                            
                            logs = discord.Embed(title=f"{interaction.user} Verification Result", color=v.style(interaction.guild.id))
                            try:
                                logs.set_thumbnail(url=interaction.user.avatar.url)
                            except AttributeError:
                                logs.set_thumbnail(url=interaction.user.default_avatar.url)
                            logs.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
                            logs.add_field(name="Creation", value=f"{interaction.user.created_at.strftime('%m/%d/%Y')} (MM/DD/YYYY)", inline=True)
                            logs.add_field(name="Status", value=f"`{interaction.user.name}` has successfully passed verification.", inline=False)
                            await audit_log(v.client, interaction, "Verification", logs)
                        else:
                            attempts_left -= 1
                            if attempts_left != 0:
                                embed = discord.Embed(title="Incorrect", description=f"**You have {attempts_left} attempts left.**", color=v.error)
                                await dm.send(embed=embed)
                    else:
                        if attempts_left == 0:
                            if failAction == "unverified":
                                failedAction = "Kept Unverified"
                                action = f"You can go back to <#{chan}> to start a new verification process by clicking on the Verify button again."
                            elif failAction == "kick":
                                failedAction = "Kicked"
                                action = ""
                            elif failAction == "ban":
                                failedAction = "Banned"
                                action = ""
                            
                            captchaFailed = discord.Embed(
                                title="You have failed verification!",
                                description=(
                                    f"You have unfortunately failed to pass the verification in {interaction.guild.name}"
                                    "\n**Reason:** Too many failed attempts."
                                    f"\n**Correct answer:** `{captcha_text}`"
                                    f"\n{action}"
                                )
                            )
                            await author.send(embed=captchaFailed)

                            if failAction == "kick":
                                await interaction.user.kick(reason="Failed to verify")
                            elif failAction == "ban":
                                await interaction.user.ban(reason="Failed to verify")

                            # LOGGING
                            logs = discord.Embed(title=f"{interaction.user} Verification Result", color=v.style(interaction.guild.id))
                            try:
                                logs.set_thumbnail(url=interaction.user.avatar.url)
                            except AttributeError:
                                logs.set_thumbnail(url=interaction.user.default_avatar.url)
                            logs.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
                            logs.add_field(name="Creation", value=f"{interaction.user.created_at.strftime('%m/%d/%Y')} (MM/DD/YYYY)", inline=True)
                            logs.add_field(name="Status", value=f"`{interaction.user.name}` has failed to pass verification.", inline=False)
                            logs.add_field(name="Reason", value=f"Failed to verify! Too many failed attempts. \nThis user has been `{failedAction}`", inline=True)
                            await audit_log(v.client, interaction, "Verification", logs)
                except discord.HTTPException:
                    error = discord.Embed(description="**I wasn't able to DM you.. Open your DMs and try to reverify.**", color=v.error)
                    return await interaction.response.send_message(embed=error, ephemeral=True)
                return
            ###
            if mode == "captcha_channel":
                class CaptchaModal(discord.ui.Modal):
                    def __init__(self):
                        super().__init__(
                            discord.ui.InputText(label="Code", placeholder=captcha_text.lower(), style=discord.InputTextStyle.short),
                            title="Captcha Answer",
                        )
                    async def callback(self, interaction: discord.Interaction):
                        answer = self.children[0].value
                        
                        attempts_left = 5
                        while attempts_left > 0:
                            if f"{answer}".lower() == f"{captcha_text}".lower():
                                await author.add_roles(role)
                                
                                captchaCorrect = discord.Embed(
                                    title="You have been verified!",
                                    description=f"You passed the verification successfully. You can now access {interaction.guild.name}"
                                )
                                await dm.send(embed=captchaCorrect)
                                
                                logs = discord.Embed(title=f"{interaction.user} Verification Result", color=v.style(interaction.guild.id))
                                try:
                                    logs.set_thumbnail(url=interaction.user.avatar.url)
                                except AttributeError:
                                    logs.set_thumbnail(url=interaction.user.default_avatar.url)
                                logs.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
                                logs.add_field(name="Creation", value=f"{interaction.user.created_at.strftime('%m/%d/%Y')} (MM/DD/YYYY)", inline=True)
                                logs.add_field(name="Status", value=f"`{interaction.user.name}` has successfully passed verification.", inline=False)
                                await audit_log(v.client, interaction, "Verification", logs)
                            else:
                                attempts_left -= 1
                                if attempts_left != 0:
                                    embed = discord.Embed(title="Incorrect", description=f"**You have {attempts_left} attempts left.**", color=v.error)
                                    await dm.send(embed=embed)
                            return
                        else:
                            if attempts_left == 0:
                                if failAction == "unverified":
                                    failedAction = "Kept Unverified"
                                    action = f"You can go back to <#{chan}> to start a new verification process by clicking on the Verify button again."
                                elif failAction == "kick":
                                    failedAction = "Kicked"
                                    action = ""
                                elif failAction == "ban":
                                    failedAction = "Banned"
                                    action = ""
                                
                                captchaFailed = discord.Embed(
                                    title="You have failed verification!",
                                    description=(
                                        f"You have unfortunately failed to pass the verification in {interaction.guild.name}"
                                        "\n**Reason:** Too many failed attempts."
                                        f"\n**Correct answer:** `{captcha_text}`"
                                        f"\n{action}"
                                    )
                                )
                                await author.send(embed=captchaFailed)

                                if failAction == "kick":
                                    await interaction.user.kick(reason="Failed to verify")
                                elif failAction == "ban":
                                    await interaction.user.ban(reason="Failed to verify")

                                # LOGGING
                                logs = discord.Embed(title=f"{interaction.user} Verification Result", color=v.style(interaction.guild.id))
                                try:
                                    logs.set_thumbnail(url=interaction.user.avatar.url)
                                except AttributeError:
                                    logs.set_thumbnail(url=interaction.user.default_avatar.url)
                                logs.add_field(name="User", value=f"{interaction.user.mention}", inline=True)
                                logs.add_field(name="Creation", value=f"{interaction.user.created_at.strftime('%m/%d/%Y')} (MM/DD/YYYY)", inline=True)
                                logs.add_field(name="Status", value=f"`{interaction.user.name}` has failed to pass verification.", inline=False)
                                logs.add_field(name="Reason", value=f"Failed to verify! Too many failed attempts. \nThis user has been `{failedAction}`", inline=True)
                                await audit_log(v.client, interaction, "Verification", logs)
                                await interaction.response.send_message(embed=captchaFailed, ephemeral=True)
                            return
                
                class CaptchaButton(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=None)
                    @discord.ui.button(label="Answer", style=discord.ButtonStyle.green)
                    async def button(self, button: discord.ui.Button, interaction: discord.Interaction):
                        await interaction.response.send_modal(CaptchaModal())
                await interaction.response.send_message(embed=captchaEmbed, view=CaptchaButton(), file=file, ephemeral=True)
            ###
        ##
    ##

def setup(client):
    client.add_cog(Verification(client))