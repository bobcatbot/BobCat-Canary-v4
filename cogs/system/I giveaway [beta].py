import random
import discord
import time as pyTime
import humanfriendly
from datetime import datetime
from discord.ext import commands, tasks
from bunnet.operators import Or
from modules import bot as v
from modules.models import Giveaway, Guild

def giveaways_fetchall() -> list[Giveaway]:
    return Giveaway.find_all().run()

class GiveawayCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False

    def _build_giveaway_embed(self, data: Giveaway, ended: bool = False) -> discord.Embed:
        """Build a giveaway embed."""
        if ended:
            embed = discord.Embed(
                color=v.style(int(data.guild_id)),
                title=f"🎉 {data.prize} 🎉 [ENDED]",
                description=data.embed_desc or "",
            )
            embed.add_field(name="Ended", value=f"<t:{int(pyTime.time())}:R>", inline=False)
            embed.add_field(name="Hosted by", value=f"<@{data.author_id}>", inline=False)
            embed.add_field(name="Participants", value=f"**{len(data.participants)}**", inline=False)
            if data.winners:
                winners = " ".join(f"<@{w}>" for w in data.winners)
                embed.add_field(name=f"Winners [{len(data.winners)}]", value=winners, inline=False)
            return embed

        embed = discord.Embed(
            color=v.style(int(data.guild_id)),
            title=f"🎉 {data.prize} 🎉",
            description=data.embed_desc or "",
        )
        embed.add_field(name="Ends", value=f"<t:{int(data.end_epoch)}:R> (<t:{int(data.end_epoch)}:f>)", inline=False)
        embed.add_field(name="Hosted by", value=f"<@{data.author_id}>", inline=False)
        embed.add_field(name="Winners", value=f"**{data.winner_count}**", inline=False)
        embed.add_field(name="Participants", value=f"**{len(data.participants)}**", inline=False)
        
        # Show rewards if any
        rewards = []
        if data.give_coins.get('enabled'):
            rewards.append(f"💰 {data.give_coins['amount']} coins")
        if data.give_xp.get('enabled'):
            rewards.append(f"⭐ {data.give_xp['amount']} XP")
        if rewards:
            embed.add_field(name="🎁 Rewards", value="\n".join(rewards), inline=False)
        
        embed.set_footer(text=f"Giveaway ID: {data.id}")
        return embed

    @tasks.loop(minutes=1)
    async def giveawayCheck(self):
        """Check for expired giveaways every minute."""
        giveaways = giveaways_fetchall()

        for data in giveaways:
            if data.status != "Ongoing" or pyTime.time() < data.end_epoch:
                continue

            try:
                guild = await v.client.fetch_guild(int(data.guild_id))
                channel = await guild.fetch_channel(int(data.channel_id))
                msg = await channel.fetch_message(int(data.message_id))
            except (discord.NotFound, discord.Forbidden):
                # Channel or message deleted - mark as ended
                data.status = "Ended"
                data.save()
                continue

            # Determine winners
            if data.participants:
                if len(data.participants) < data.winner_count:
                    winners = []
                    await msg.reply(content="❌ There were not enough participants to draw winners.")
                else:
                    winners = random.sample(data.participants, k=data.winner_count)
                    mentions = []
                    for user_id in winners:
                        try:
                            member = await guild.fetch_member(int(user_id))
                            mentions.append(member.mention)
                        except discord.NotFound:
                            mentions.append(f"<@{user_id}> (left server)")

                    # Award prizes (coins/XP) if enabled
                    for user_id in winners:
                        try:
                            member = await guild.fetch_member(int(user_id))
                            # Award coins
                            if data.give_coins.get('enabled'):
                                from cogs.money.tools.utils import open_account, update_bank
                                await open_account(guild, member)
                                await update_bank(guild, member, 'bank', data.give_coins['amount'])
                            # Award XP
                            if data.give_xp.get('enabled'):
                                from modules.models import Leveling
                                level_data = Leveling.get(f"{guild.id}_{member.id}").run()
                                if level_data:
                                    level_data.exp += data.give_xp['amount']
                                    level_data.save()
                        except Exception:
                            pass  # Skip if member left

                    await msg.reply(content=f"🎉 Congratulations {', '.join(mentions)}! You won **{data.prize}**!")
                    await self._log_giveaway_result(guild, data, winners)

                data.winners = winners
            else:
                await msg.reply(content="❌ No valid entrants, so a winner could not be determined!")

            # Update embed
            embed = self._build_giveaway_embed(data, ended=True)
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label="📋 Giveaway Summary",
                style=discord.ButtonStyle.gray,
                custom_id=f"GiveawaySummary_{data.message_id}"
            ))
            await msg.edit(embed=embed, view=view)

            data.status = "Ended"
            data.save()

    async def _log_giveaway_result(self, guild, data, winners):
        """Log giveaway results to audit channel."""
        try:
            guild_data = Guild.get(str(guild.id)).run()
            if guild_data and guild_data.dashboard.giveaways.get('logChannel'):
                log_channel_id = guild_data.dashboard.giveaways['logChannel']
                log_channel = guild.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="Prize", value=data.prize, inline=True)
                    embed.add_field(name="Winners", value=", ".join(f"<@{w}>" for w in winners), inline=True)
                    embed.add_field(name="Total Participants", value=len(data.participants), inline=True)
                    embed.set_footer(text=f"ID: {data.id}")
                    await log_channel.send(embed=embed)
        except Exception:
            pass

    giveaway = discord.SlashCommandGroup("giveaway", "Giveaway Commands")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            # Register persistent view for all giveaways
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label="📋 Giveaway Summary",
                style=discord.ButtonStyle.gray,
                custom_id="GiveawaySummary"
            ))
            self.client.add_view(view)
            self.persistent_views_added = True

        if not self.giveawayCheck.is_running():
            self.giveawayCheck.start()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")

        # Handle join/leave
        if custom_id == "JoinGiveaway":
            await interaction.response.defer(ephemeral=True)

            data = Giveaway.find_one(
                Giveaway.guild_id == str(interaction.guild.id),
                Giveaway.message_id == str(interaction.message.id),
            ).run()

            if data is None or data.status != "Ongoing":
                return await interaction.followup.send(
                    "❌ You cannot enter or leave this giveaway because it has already ended!",
                    ephemeral=True
                )

            user_id = str(interaction.user.id)

            if user_id not in data.participants:
                data.participants.append(user_id)
                response = "✅ You're now participating in this giveaway!"
            else:
                data.participants.remove(user_id)
                response = "❌ You're not participating in this giveaway anymore!"

            data.save()

            # Update embed with new participant count
            if interaction.message.embeds:
                embed = interaction.message.embeds[0].to_dict()
                for i, field in enumerate(embed.get("fields", [])):
                    if "Participants" in field["name"]:
                        embed["fields"][i]["value"] = f"**{len(data.participants)}**"
                        break
                await interaction.message.edit(embed=discord.Embed.from_dict(embed))

            return await interaction.followup.send(response, ephemeral=True)

        # Handle giveaway summary
        if custom_id.startswith("GiveawaySummary") or custom_id == "GiveawaySummary":
            await interaction.response.defer(ephemeral=True)

            if "_" in custom_id:
                message_id = custom_id.split("_")[1]
            else:
                message_id = str(interaction.message.id)

            data = Giveaway.find_one(
                Giveaway.guild_id == str(interaction.guild.id),
                Giveaway.message_id == message_id,
            ).run()

            if data is None:
                return await interaction.followup.send(
                    "❌ I could not find this giveaway.",
                    ephemeral=True
                )

            date = datetime.fromtimestamp(int(data.end_epoch))
            date_str = date.strftime("%x, %X %p")

            winners = " ".join(f"<@{user_id}>" for user_id in data.winners) or "No winners"
            participants_list = "\n".join(
                f"<@{user_id}>" for user_id in data.participants[:20]
            )
            if len(data.participants) > 20:
                participants_list += f"\n... and {len(data.participants) - 20} more"

            embed = discord.Embed(
                title="📋 Giveaway Summary",
                color=v.style(interaction.guild.id),
                timestamp=datetime.now()
            )
            embed.add_field(name="Prize", value=data.prize, inline=False)
            embed.add_field(name="Ended", value=date_str, inline=True)
            embed.add_field(name="Host", value=f"<@{data.author_id}>", inline=True)
            embed.add_field(name="Winners", value=data.winner_count, inline=True)
            embed.add_field(name=f"🏆 Winners [{len(data.winners)}]", value=winners, inline=False)
            embed.add_field(name=f"👥 Participants [{len(data.participants)}]", value=participants_list or "No participants", inline=False)
            embed.set_footer(text=f"ID: {data.id}")

            return await interaction.followup.send(embed=embed, ephemeral=True)

    @giveaway.command(description="Start a giveaway")
    @discord.option("prize", str, description="The prize for the giveaway", required=True)
    @discord.option("time", str, description="The amount of time the giveaway should go on for i.e 5d, 6h, 30m", required=True)
    @discord.option("winners", str, description="The amount of winners for the giveaway. Default: 1", required=False)
    @discord.option("description", str, description="Giveaway embed description", required=False)
    @discord.option("channel", discord.TextChannel, description="What text channel should the giveaway be in?", required=False)
    @discord.option("ping_role", discord.Role, description="The role to ping for the giveaway", required=False)
    @discord.option("coins", int, description="The amount of economy coins to give when the user wins the giveaway", required=False)
    @discord.option("xp", int, description="The amount of leveling xp to give when the user wins the giveaway", required=False)
    async def create(self, ctx, prize, time, winners=None, description=None, channel=None, ping_role=None, coins=None, xp=None):
        chan = channel or ctx.channel

        # Permission checks
        if not chan.permissions_for(ctx.author).send_messages:
            return await ctx.respond(f"❌ You don't have permission to send messages in {chan.mention}", ephemeral=True)

        if not chan.permissions_for(ctx.me).send_messages:
            return await ctx.respond("❌ I don't have permission to send messages in that channel!", ephemeral=True)

        if not chan.permissions_for(ctx.me).add_reactions:
            return await ctx.respond("❌ I need the `Add Reactions` permission to run giveaways!", ephemeral=True)

        dashboard = Guild.get(str(ctx.guild.id)).run().dashboard

        if coins and not dashboard.economy.get("status", False):
            return await ctx.respond("❌ Economy is currently disabled!", ephemeral=True)

        if xp and not dashboard.leveling.get("status", False):
            return await ctx.respond("❌ Leveling is currently disabled!", ephemeral=True)

        winner_count = int(winners or 1)
        description = description or ""
        ping = ping_role.mention if ping_role else ""

        try:
            duration = humanfriendly.parse_timespan(time)
        except humanfriendly.InvalidTimespan:
            return await ctx.respond("❌ Invalid time format! Use formats like `5d`, `6h`, `30m`", ephemeral=True)

        epochEnd = pyTime.time() + duration
        giveaway_id = v.uuid(length=12, strCase="upper/lower/nums")

        # Create giveaway data
        data = Giveaway(
            id=giveaway_id,
            guild_id=str(ctx.guild.id),
            channel_id=str(chan.id),
            channel_name=chan.name,
            message_id="",
            author_id=str(ctx.author.id),
            end_epoch=epochEnd,
            end_timestamp=datetime.fromtimestamp(epochEnd).strftime("%m.%d.%Y %H:%M"),
            prize=prize,
            winner_count=winner_count,
            status="Ongoing",
            participants=[],
            winners=[],
            give_xp={"enabled": bool(xp), "amount": xp or 0},
            give_coins={"enabled": bool(coins), "amount": coins or 0},
            embed_title=f"🎉 {prize} 🎉",
            embed_desc=description,
        )

        embed = self._build_giveaway_embed(data)

        try:
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label="🎯 Join Giveaway",
                style=discord.ButtonStyle.blurple,
                custom_id="JoinGiveaway"
            ))
            msg = await chan.send(content=ping, embed=embed, view=view)

            data.message_id = str(msg.id)
            data.insert()

            await ctx.respond("✅ Giveaway created successfully!", ephemeral=True)
        except discord.Forbidden:
            await ctx.respond("❌ I don't have permission to send messages or embed links in that channel!", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"❌ Giveaway creation failed: {str(e)}", ephemeral=True)

    @giveaway.command(description="Shows active giveaways")
    async def list(self, ctx):
        data = Giveaway.find(
            Giveaway.guild_id == str(ctx.guild.id),
            Giveaway.status == "Ongoing",
        ).run()

        if not data:
            return await ctx.respond("📭 There are **no active giveaways** running.", ephemeral=True)

        active = []
        for item in data:
            try:
                guild = self.client.get_guild(int(item.guild_id)) or await self.client.fetch_guild(int(item.guild_id))
                channel = guild.get_channel(int(item.channel_id)) or await guild.fetch_channel(int(item.channel_id))
                msg = await channel.fetch_message(int(item.message_id))
                jump_url = msg.jump_url
            except:
                jump_url = "#"

            winner_word = "winner" if item.winner_count == 1 else "winners"
            active.append(
                f"`{item.id}` | [Jump]({jump_url}) | **{item.winner_count}** {winner_word} | "
                f"**Prize:** {item.prize} | **Ends:** <t:{int(item.end_epoch)}:R>"
            )

        embed = discord.Embed(
            title=f"🎁 Active Giveaways in {ctx.guild.name}",
            description="\n".join(active) if active else "No active giveaways.",
            color=v.style(ctx.guild.id)
        )
        embed.set_footer(text=f"Total: {len(active)} active giveaways")
        await ctx.respond(embed=embed)

    @giveaway.command(description="Rerolls a new winner from a giveaway")
    @discord.option("giveaway_id", str, description="ID of giveaway to reroll", required=True)
    async def reroll(self, ctx, giveaway_id):
        data = Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Or(
                Giveaway.id == str(giveaway_id),
                Giveaway.message_id == str(giveaway_id),
            ),
        ).run()

        if data is None:
            return await ctx.respond(f"❌ I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)

        if not data.participants:
            return await ctx.respond("❌ No valid entrants, so a winner could not be determined!", ephemeral=True)

        available_participants = [p for p in data.participants if p not in data.winners]
        if not available_participants:
            return await ctx.respond("❌ All participants have already won! No one left to reroll.", ephemeral=True)

        user_id = random.choice(available_participants)
        try:
            user = ctx.guild.get_member(int(user_id)) or await ctx.guild.fetch_member(int(user_id))
            mention = user.mention
        except:
            mention = f"<@{user_id}>"

        data.winners.append(user_id)
        data.save()

        embed = discord.Embed(
            title="🎉 Giveaway Rerolled!",
            description=f"{ctx.author.mention} rerolled the giveaway!\n\n🏆 New winner: {mention}",
            color=discord.Color.gold()
        )
        await ctx.respond(embed=embed)

    @giveaway.command(description="End a giveaway")
    @discord.option("giveaway_id", str, description="ID of giveaway to end", required=True)
    async def end(self, ctx, giveaway_id):
        data = Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Or(
                Giveaway.id == str(giveaway_id),
                Giveaway.message_id == str(giveaway_id),
            ),
        ).run()

        if data is None:
            return await ctx.respond(f"❌ I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)

        if data.status == "Ended":
            return await ctx.respond("❌ This giveaway has already ended!", ephemeral=True)

        try:
            channel = await ctx.guild.fetch_channel(int(data.channel_id))
            message = await channel.fetch_message(int(data.message_id))
        except:
            return await ctx.respond("❌ Could not find the giveaway message!", ephemeral=True)

        if data.participants:
            user_id = random.choice(data.participants)
            try:
                user = ctx.guild.get_member(int(user_id)) or await ctx.guild.fetch_member(int(user_id))
                winner_text = user.mention
            except:
                winner_text = f"<@{user_id}>"
            data.winners = [user_id]
            await message.reply(content=f"🎉 Congratulations {winner_text}! You won **{data.prize}**!")
        else:
            data.winners = []
            winner_text = "No winners"
            await message.reply(content="❌ No valid entrants, so a winner could not be determined!")

        data.status = "Ended"
        data.save()

        embed = self._build_giveaway_embed(data, ended=True)
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label="📋 Giveaway Summary",
            style=discord.ButtonStyle.gray,
            custom_id=f"GiveawaySummary_{data.message_id}"
        ))
        await message.edit(embed=embed, view=view)

        await ctx.respond(f"✅ Successfully ended giveaway `{giveaway_id}`", ephemeral=True)

    @giveaway.command(description="Delete a giveaway")
    @discord.option("giveaway_id", description="ID of giveaway to delete", required=True)
    async def delete(self, ctx, giveaway_id):
        data = Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Giveaway.id == giveaway_id
        ).run()
        
        if data is None:
            return await ctx.respond(f"❌ Giveaway not found", ephemeral=True)
        
        # Delete the Discord message
        try:
            channel = await ctx.guild.fetch_channel(int(data.channel_id))
            message = await channel.fetch_message(int(data.message_id))
            await message.delete()
        except:
            pass  # Message may already be deleted
        
        data.delete()
        await ctx.respond(f"✅ Deleted giveaway `{giveaway_id}`", ephemeral=True)

def setup(client):
    client.add_cog(GiveawayCog(client))