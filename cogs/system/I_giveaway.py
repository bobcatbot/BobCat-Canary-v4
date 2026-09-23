import random
import discord
import time as pyTime
import humanfriendly
from datetime import datetime
from discord.ext import commands, tasks
from beanie.operators import Or
from modules import bot as v
from modules.models import Giveaway, Guild, EmbedConfig

async def giveaways_fetchall() -> list[Giveaway]:
    return await Giveaway.find_all().to_list()

class GiveawayCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False

    def _build_giveaway_embed(self, data: Giveaway, ended: bool = False) -> discord.Embed:
        """Build a giveaway embed."""
        guild = data.guild_id
        if ended:
            embed = discord.Embed(
                color=v.style(int(data.guild_id)),
                title=v.t.msg(guild, "giveaways.embed.title_ended", prize=data.prize),
                description=data.embed.description or "",
            )
            embed.add_field(name=v.t.msg(guild, "giveaways.embed.ended_field"), value=f"<t:{int(pyTime.time())}:R>", inline=False)
            embed.add_field(name=v.t.msg(guild, "giveaways.embed.hosted_by_field"), value=f"<@{data.author_id}>", inline=False)
            embed.add_field(name=v.t.msg(guild, "giveaways.embed.participants_field"), value=f"**{len(data.participants)}**", inline=False)
            if data.winners:
                winners = " ".join(f"<@{w}>" for w in data.winners)
                embed.add_field(name=v.t.msg(guild, "giveaways.embed.winners_field_ended", count=len(data.winners)), value=winners, inline=False)

            # Show what was actually awarded - without this, winners have no
            # way to see what they won once the giveaway embed updates to ENDED.
            rewards = []
            if data.give_coins.get('enabled'):
                rewards.append(v.t.msg(guild, "giveaways.embed.reward_coins", amount=data.give_coins['amount']))
            if data.give_xp.get('enabled'):
                rewards.append(v.t.msg(guild, "giveaways.embed.reward_xp", amount=data.give_xp['amount']))
            if rewards:
                embed.add_field(name=v.t.msg(guild, "giveaways.embed.rewards_field"), value="\n".join(rewards), inline=False)

            return embed

        embed = discord.Embed(
            color=v.style(int(data.guild_id)),
            title=v.t.msg(guild, "giveaways.embed.title", prize=data.prize),
            description=data.embed.description or "",
        )
        embed.add_field(name=v.t.msg(guild, "giveaways.embed.ends_field"), value=f"<t:{int(data.end_epoch)}:R> (<t:{int(data.end_epoch)}:f>)", inline=False)
        embed.add_field(name=v.t.msg(guild, "giveaways.embed.hosted_by_field"), value=f"<@{data.author_id}>", inline=False)
        embed.add_field(name=v.t.msg(guild, "giveaways.embed.winners_field"), value=f"**{data.winner_count}**", inline=False)
        embed.add_field(name=v.t.msg(guild, "giveaways.embed.participants_field"), value=f"**{len(data.participants)}**", inline=False)

        # Show rewards if any
        rewards = []
        if data.give_coins.get('enabled'):
            rewards.append(v.t.msg(guild, "giveaways.embed.reward_coins", amount=data.give_coins['amount']))
        if data.give_xp.get('enabled'):
            rewards.append(v.t.msg(guild, "giveaways.embed.reward_xp", amount=data.give_xp['amount']))
        if rewards:
            embed.add_field(name=v.t.msg(guild, "giveaways.embed.rewards_field"), value="\n".join(rewards), inline=False)

        embed.set_footer(text=v.t.msg(guild, "giveaways.embed.footer", id=data.id))
        return embed

    @tasks.loop(minutes=1)
    async def giveawayCheck(self):
        """Check for expired giveaways every minute."""
        giveaways = await giveaways_fetchall()

        for data in giveaways:
            if data.status != "Ongoing" or pyTime.time() < data.end_epoch:
                continue

            try:
                guild = await self.client.fetch_guild(int(data.guild_id))
                channel = await guild.fetch_channel(int(data.channel_id))
                msg = await channel.fetch_message(int(data.message_id))
            except (discord.NotFound, discord.Forbidden):
                # Channel or message deleted - mark as ended
                data.status = "Ended"
                await data.save()
                continue

            # Determine winners
            if data.participants:
                if len(data.participants) < data.winner_count:
                    winners = []
                    await msg.reply(content=v.t.msg(guild, "giveaways.check.not_enough_participants"))
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
                                from cogs.money._shop import open_account, update_bank
                                await open_account(guild, member)
                                await update_bank(guild, member, 'bank', data.give_coins['amount'])
                            # Award XP
                            if data.give_xp.get('enabled'):
                                from modules.models import Leveling
                                level_data = await Leveling.get(f"{guild.id}_{member.id}")
                                if level_data:
                                    level_data.exp += data.give_xp['amount']
                                    await level_data.save()
                        except Exception:
                            pass  # Skip if member left

                    await msg.reply(content=v.t.msg(guild, "giveaways.end.congratulations", text=', '.join(mentions), prize=data.prize))
                    await self._log_giveaway_result(guild, data, winners)

                data.winners = winners
            else:
                await msg.reply(content=v.t.msg(guild, "giveaways.end.no_valid_entrants"))

            # Update embed
            embed = self._build_giveaway_embed(data, ended=True)
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label=v.t.msg(guild, "giveaways.helpers.giveaway_summary_btn"),
                style=discord.ButtonStyle.gray,
                custom_id=f"GiveawaySummary_{data.message_id}"
            ))
            await msg.edit(embed=embed, view=view)

            data.status = "Ended"
            await data.save()

    async def _log_giveaway_result(self, guild, data, winners):
        """Log giveaway results to audit channel."""
        try:
            guild_data = await Guild.get(str(guild.id))
            if guild_data and guild_data.dashboard.giveaways.logChannel:
                log_channel_id = guild_data.dashboard.giveaways.logChannel
                log_channel = guild.get_channel(int(log_channel_id))
                if log_channel:
                    embed = discord.Embed(
                        title=v.t.msg(guild, "giveaways.log.title"),
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name=v.t.msg(guild, "giveaways.log.prize_field"), value=data.prize, inline=True)
                    embed.add_field(name=v.t.msg(guild, "giveaways.log.winners_field"), value=", ".join(f"<@{w}>" for w in winners), inline=True)
                    embed.add_field(name=v.t.msg(guild, "giveaways.log.participants_field"), value=len(data.participants), inline=True)
                    embed.set_footer(text=v.t.msg(guild, "giveaways.log.footer", id=data.id))
                    await log_channel.send(embed=embed)
        except Exception:
            pass

    giveaway = discord.SlashCommandGroup(
        name=v.t.msg(None, "giveaways.cmd.name"),
        description=v.t.msg(None, "giveaways.cmd.description"),
        name_localizations=v.t.localizations("giveaways.cmd.name"),
        description_localizations=v.t.localizations("giveaways.cmd.description"),
    )

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            # Register persistent view for all giveaways
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label=v.t.msg(None, "giveaways.helpers.giveaway_summary_btn"),
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

            data = await Giveaway.find_one(
                Giveaway.guild_id == str(interaction.guild.id),
                Giveaway.message_id == str(interaction.message.id),
            )

            if data is None or data.status != "Ongoing":
                return await interaction.followup.send(
                    v.t.msg(interaction.guild, "giveaways.join.ended"),
                    ephemeral=True
                )

            user_id = str(interaction.user.id)

            if user_id not in data.participants:
                data.participants.append(user_id)
                response = v.t.msg(interaction.guild, "giveaways.join.joined")
            else:
                data.participants.remove(user_id)
                response = v.t.msg(interaction.guild, "giveaways.join.left")

            await data.save()

            # Update embed with new participant count
            if interaction.message.embeds:
                embed = interaction.message.embeds[0].to_dict()
                participants_field = v.t.msg(interaction.guild, "giveaways.embed.participants_field")
                for i, field in enumerate(embed.get("fields", [])):
                    if participants_field in field["name"]:
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

            data = await Giveaway.find_one(
                Giveaway.guild_id == str(interaction.guild.id),
                Giveaway.message_id == message_id,
            )

            if data is None:
                return await interaction.followup.send(
                    v.t.msg(interaction.guild, "giveaways.summary.not_found"),
                    ephemeral=True
                )

            date = datetime.fromtimestamp(int(data.end_epoch))
            date_str = date.strftime("%x, %X %p")

            winners = " ".join(f"<@{user_id}>" for user_id in data.winners) or v.t.msg(interaction.guild, "giveaways.end.no_winners")
            participants_list = "\n".join(
                f"<@{user_id}>" for user_id in data.participants[:20]
            )
            if len(data.participants) > 20:
                participants_list += "\n" + v.t.msg(interaction.guild, "giveaways.summary.more_participants", count=len(data.participants) - 20)

            embed = discord.Embed(
                title=v.t.msg(interaction.guild, "giveaways.helpers.giveaway_summary_btn"),
                color=v.style(interaction.guild.id),
                timestamp=datetime.now()
            )
            embed.add_field(name=v.t.msg(interaction.guild, "giveaways.log.prize_field"), value=data.prize, inline=False)
            embed.add_field(name=v.t.msg(interaction.guild, "giveaways.embed.ended_field"), value=date_str, inline=True)
            embed.add_field(name=v.t.msg(interaction.guild, "giveaways.summary.host_field"), value=f"<@{data.author_id}>", inline=True)
            embed.add_field(name=v.t.msg(interaction.guild, "giveaways.log.winners_field"), value=data.winner_count, inline=True)
            embed.add_field(name=v.t.msg(interaction.guild, "giveaways.summary.winners_field", count=len(data.winners)), value=winners, inline=False)
            embed.add_field(name=v.t.msg(interaction.guild, "giveaways.summary.participants_field", count=len(data.participants)), value=participants_list or v.t.msg(interaction.guild, "giveaways.summary.no_participants"), inline=False)

            rewards = []
            if data.give_coins.get('enabled'):
                rewards.append(v.t.msg(interaction.guild, "giveaways.embed.reward_coins", amount=data.give_coins['amount']))
            if data.give_xp.get('enabled'):
                rewards.append(v.t.msg(interaction.guild, "giveaways.embed.reward_xp", amount=data.give_xp['amount']))
            if rewards:
                embed.add_field(name=v.t.msg(interaction.guild, "giveaways.embed.rewards_field"), value="\n".join(rewards), inline=False)

            embed.set_footer(text=v.t.msg(interaction.guild, "giveaways.log.footer", id=data.id))

            return await interaction.followup.send(embed=embed, ephemeral=True)

    @giveaway.command(
        description=v.t.msg(None, "giveaways.create.cmd.description"),
        name_localizations=v.t.localizations("giveaways.create.cmd.name"),
        description_localizations=v.t.localizations("giveaways.create.cmd.description"),
    )
    @discord.option("prize", str, description=v.t.msg(None, "giveaways.create.cmd.options.prize.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.prize.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.prize.description"), required=True)
    @discord.option("time", str, description=v.t.msg(None, "giveaways.create.cmd.options.time.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.time.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.time.description"), required=True)
    @discord.option("winners", str, description=v.t.msg(None, "giveaways.create.cmd.options.winners.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.winners.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.winners.description"), required=False)
    @discord.option("description", str, description=v.t.msg(None, "giveaways.create.cmd.options.description.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.description.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.description.description"), required=False)
    @discord.option("channel", discord.TextChannel, description=v.t.msg(None, "giveaways.create.cmd.options.channel.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.channel.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.channel.description"), required=False)
    @discord.option("ping_role", discord.Role, description=v.t.msg(None, "giveaways.create.cmd.options.ping_role.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.ping_role.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.ping_role.description"), required=False)
    @discord.option("coins", int, description=v.t.msg(None, "giveaways.create.cmd.options.coins.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.coins.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.coins.description"), required=False)
    @discord.option("xp", int, description=v.t.msg(None, "giveaways.create.cmd.options.xp.description"), name_localizations=v.t.localizations("giveaways.create.cmd.options.xp.name"), description_localizations=v.t.localizations("giveaways.create.cmd.options.xp.description"), required=False)
    async def create(self, ctx, prize, time, winners=None, description=None, channel=None, ping_role=None, coins=None, xp=None):
        chan = channel or ctx.channel

        # Permission checks
        if not chan.permissions_for(ctx.author).send_messages:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.no_perm_user", channel=chan.mention), ephemeral=True)

        if not chan.permissions_for(ctx.me).send_messages:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.no_perm_bot_send"), ephemeral=True)

        if not chan.permissions_for(ctx.me).add_reactions:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.no_perm_bot_reactions"), ephemeral=True)

        dashboard = (await Guild.get(str(ctx.guild.id))).dashboard

        if coins and not dashboard.economy.status:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.economy_disabled"), ephemeral=True)

        if xp and not dashboard.leveling.status:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.leveling_disabled"), ephemeral=True)

        winner_count = int(winners or 1)
        description = description or ""
        ping = ping_role.mention if ping_role else ""

        try:
            duration = humanfriendly.parse_timespan(time)
        except humanfriendly.InvalidTimespan:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.invalid_time"), ephemeral=True)

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
            embed=EmbedConfig(title=f"🎉 {prize} 🎉", description=description, color=0x5865f2),
        )

        embed = self._build_giveaway_embed(data)

        try:
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(
                label=v.t.msg(ctx.guild, "giveaways.helpers.join_button"),
                style=discord.ButtonStyle.blurple,
                custom_id="JoinGiveaway"
            ))
            msg = await chan.send(content=ping, embed=embed, view=view)

            data.message_id = str(msg.id)
            await data.insert()

            await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.success"), ephemeral=True)
        except discord.Forbidden:
            await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.forbidden"), ephemeral=True)
        except Exception as e:
            await ctx.respond(v.t.msg(ctx.guild, "giveaways.create.failed", error=str(e)), ephemeral=True)

    @giveaway.command(
        description=v.t.msg(None, "giveaways.list.cmd.description"),
        name_localizations=v.t.localizations("giveaways.list.cmd.name"),
        description_localizations=v.t.localizations("giveaways.list.cmd.description"),
    )
    async def list(self, ctx):
        data = await Giveaway.find(
            Giveaway.guild_id == str(ctx.guild.id),
            Giveaway.status == "Ongoing",
        ).to_list()

        if not data:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.list.no_active"), ephemeral=True)

        jump_label = v.t.msg(ctx.guild, "giveaways.list.jump")
        prize_label = v.t.msg(ctx.guild, "giveaways.list.prize")
        end_label = v.t.msg(ctx.guild, "giveaways.list.end")

        active = []
        for item in data:
            try:
                guild = self.client.get_guild(int(item.guild_id)) or await self.client.fetch_guild(int(item.guild_id))
                channel = guild.get_channel(int(item.channel_id)) or await guild.fetch_channel(int(item.channel_id))
                msg = await channel.fetch_message(int(item.message_id))
                jump_url = msg.jump_url
            except discord.HTTPException:
                jump_url = "#"

            winner_word = v.t.msg(ctx.guild, "giveaways.list.winner") if item.winner_count == 1 else v.t.msg(ctx.guild, "giveaways.list.winners")
            active.append(
                f"`{item.id}` | [{jump_label}]({jump_url}) | **{item.winner_count}** {winner_word} | "
                f"{prize_label} {item.prize} | {end_label} <t:{int(item.end_epoch)}:R>"
            )

        embed = discord.Embed(
            title=v.t.msg(ctx.guild, "giveaways.list.embed_title", g=ctx.guild.name),
            description="\n".join(active) if active else v.t.msg(ctx.guild, "giveaways.list.embed_description_none"),
            color=v.style(ctx.guild.id)
        )
        embed.set_footer(text=v.t.msg(ctx.guild, "giveaways.list.embed_footer", count=len(active)))
        await ctx.respond(embed=embed)

    @giveaway.command(
        description=v.t.msg(None, "giveaways.reroll.cmd.description"),
        name_localizations=v.t.localizations("giveaways.reroll.cmd.name"),
        description_localizations=v.t.localizations("giveaways.reroll.cmd.description"),
    )
    @discord.option(
        "giveaway_id", str,
        description=v.t.msg(None, "giveaways.reroll.cmd.options.giveaway_id.description"),
        name_localizations=v.t.localizations("giveaways.reroll.cmd.options.giveaway_id.name"),
        description_localizations=v.t.localizations("giveaways.reroll.cmd.options.giveaway_id.description"),
        required=True,
    )
    async def reroll(self, ctx, giveaway_id):
        data = await Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Or(
                Giveaway.id == str(giveaway_id),
                Giveaway.message_id == str(giveaway_id),
            ),
        )

        if data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.reroll.failed", id=giveaway_id), ephemeral=True)

        if not data.participants:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.reroll.no_winners"), ephemeral=True)

        available_participants = [p for p in data.participants if p not in data.winners]
        if not available_participants:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.reroll.all_winners"), ephemeral=True)

        user_id = random.choice(available_participants)
        try:
            user = ctx.guild.get_member(int(user_id)) or await ctx.guild.fetch_member(int(user_id))
            mention = user.mention
        except discord.HTTPException:
            mention = f"<@{user_id}>"

        data.winners.append(user_id)
        await data.save()

        embed = discord.Embed(
            title=v.t.msg(ctx.guild, "giveaways.reroll.embed_title"),
            description=v.t.msg(ctx.guild, "giveaways.reroll.rerolled", author=ctx.author.mention, winner=mention),
            color=discord.Color.gold()
        )
        await ctx.respond(embed=embed)

    @giveaway.command(
        description=v.t.msg(None, "giveaways.end.cmd.description"),
        name_localizations=v.t.localizations("giveaways.end.cmd.name"),
        description_localizations=v.t.localizations("giveaways.end.cmd.description"),
    )
    @discord.option(
        "giveaway_id", str,
        description=v.t.msg(None, "giveaways.end.cmd.options.giveaway_id.description"),
        name_localizations=v.t.localizations("giveaways.end.cmd.options.giveaway_id.name"),
        description_localizations=v.t.localizations("giveaways.end.cmd.options.giveaway_id.description"),
        required=True,
    )
    async def end(self, ctx, giveaway_id):
        data = await Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Or(
                Giveaway.id == str(giveaway_id),
                Giveaway.message_id == str(giveaway_id),
            ),
        )

        if data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.end.failed", id=giveaway_id), ephemeral=True)

        if data.status == "Ended":
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.end.already_ended"), ephemeral=True)

        try:
            channel = await ctx.guild.fetch_channel(int(data.channel_id))
            message = await channel.fetch_message(int(data.message_id))
        except discord.HTTPException:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.end.giveaway_not_found"), ephemeral=True)

        if data.participants:
            user_id = random.choice(data.participants)
            try:
                user = ctx.guild.get_member(int(user_id)) or await ctx.guild.fetch_member(int(user_id))
                winner_text = user.mention
            except discord.HTTPException:
                winner_text = f"<@{user_id}>"
            data.winners = [user_id]
            await message.reply(content=v.t.msg(ctx.guild, "giveaways.end.congratulations", text=winner_text, prize=data.prize))
        else:
            data.winners = []
            winner_text = v.t.msg(ctx.guild, "giveaways.end.no_winners")
            await message.reply(content=v.t.msg(ctx.guild, "giveaways.end.no_valid_entrants"))

        data.status = "Ended"
        await data.save()

        embed = self._build_giveaway_embed(data, ended=True)
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(
            label=v.t.msg(ctx.guild, "giveaways.helpers.giveaway_summary_btn"),
            style=discord.ButtonStyle.gray,
            custom_id=f"GiveawaySummary_{data.message_id}"
        ))
        await message.edit(embed=embed, view=view)

        await ctx.respond(v.t.msg(ctx.guild, "giveaways.end.success", id=giveaway_id), ephemeral=True)

    @giveaway.command(
        description=v.t.msg(None, "giveaways.delete.cmd.description"),
        name_localizations=v.t.localizations("giveaways.delete.cmd.name"),
        description_localizations=v.t.localizations("giveaways.delete.cmd.description"),
    )
    @discord.option(
        "giveaway_id",
        description=v.t.msg(None, "giveaways.delete.cmd.options.giveaway_id.description"),
        name_localizations=v.t.localizations("giveaways.delete.cmd.options.giveaway_id.name"),
        description_localizations=v.t.localizations("giveaways.delete.cmd.options.giveaway_id.description"),
        required=True,
    )
    async def delete(self, ctx, giveaway_id):
        data = await Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Giveaway.id == giveaway_id
        )

        if data is None:
            return await ctx.respond(v.t.msg(ctx.guild, "giveaways.delete.failed"), ephemeral=True)
        
        # Delete the Discord message
        try:
            channel = await ctx.guild.fetch_channel(int(data.channel_id))
            message = await channel.fetch_message(int(data.message_id))
            await message.delete()
        except discord.HTTPException:
            pass  # Message may already be deleted
        
        await data.delete()
        await ctx.respond(v.t.msg(ctx.guild, "giveaways.delete.deleted", id=giveaway_id), ephemeral=True)

def setup(client):
    client.add_cog(GiveawayCog(client))