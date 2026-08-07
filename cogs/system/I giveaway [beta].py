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

    @tasks.loop(minutes=1)
    async def giveawayCheck(self):
        giveaways = giveaways_fetchall()

        for data in giveaways:
            if data.status != "Ongoing" or pyTime.time() < data.end_epoch:
                continue

            guild = await v.client.fetch_guild(int(data.guild_id))
            channel = await guild.fetch_channel(int(data.channel_id))
            msg = await channel.fetch_message(int(data.message_id))

            if data.participants:
                if len(data.participants) < data.winner_count:
                    winners = []
                    await msg.reply(content="There were not enough participants to draw winners.")
                else:
                    winners = random.sample(data.participants, k=data.winner_count)
                    mentions = []

                    for user_id in winners:
                        member = await guild.fetch_member(int(user_id))
                        mentions.append(member.mention)

                    await msg.reply(content=f"Congratulations {', '.join(mentions)}! You won **{data.prize}**")

                data.winners = winners
            else:
                await msg.reply(content="No valid entrants, so a winner could not be determined!")

            if msg.embeds:
                embed = msg.embeds[0].to_dict()
                embed["title"] = f"{data.embed_title.format(prize=data.prize)} [ENDED]"

                if embed.get("fields"):
                    embed["fields"][0]["name"] = "Ended"

                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))
                await msg.edit(embed=discord.Embed.from_dict(embed), view=view)

            data.status = "Ended"
            data.save()

    giveaway = discord.SlashCommandGroup("giveaway", "Giveaway Commands")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))
            self.client.add_view(view)
            self.persistent_views_added = True

        if not self.giveawayCheck.is_running():
            self.giveawayCheck.start()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id")

        if custom_id == "JoinGiveaway":
            data = Giveaway.find_one(
                Giveaway.guild_id == str(interaction.guild.id),
                Giveaway.message_id == str(interaction.message.id),
            ).run()

            if data is None or data.status != "Ongoing":
                return await interaction.response.send_message(
                    "You cannot enter or leave this giveaway because it has already ended!",
                    ephemeral=True
                )

            user_id = str(interaction.user.id)

            if user_id not in data.participants:
                data.participants.append(user_id)
                response = ":white_check_mark: You're now participating in this giveaway!"
            else:
                data.participants.remove(user_id)
                response = ":negative_squared_cross_mark: You're not participating in this giveaway anymore!"

            data.save()

            if interaction.message.embeds:
                embed = interaction.message.embeds[0].to_dict()
                embed["fields"][3]["value"] = f"**{len(data.participants)}**"
                await interaction.message.edit(embed=discord.Embed.from_dict(embed))

            return await interaction.response.send_message(response, ephemeral=True)

        if custom_id == "GiveawaySummary":
            data = Giveaway.find_one(
                Giveaway.guild_id == str(interaction.guild.id),
                Giveaway.message_id == str(interaction.message.id),
            ).run()

            if data is None:
                return await interaction.response.send_message(
                    "I could not find this giveaway.",
                    ephemeral=True
                )

            date = datetime.fromtimestamp(int(data.end_epoch), v.datetimes(interaction.guild.id))
            date = date.strftime("%x, %X %p")

            winners = " ".join(f"<@{user_id}>" for user_id in data.winners) or "No winners"
            participants = "\\n".join(
                f"<@{user_id}> ({user_id})" for user_id in data.participants
            ) or "No Participants"

            embed = discord.Embed(title="Giveaway Summary")
            embed.add_field(name="Ended", value=date, inline=False)
            embed.add_field(name="Host", value=f"<@{data.author_id}> ({data.author_id})", inline=False)
            embed.add_field(name="Prize", value=data.prize, inline=False)
            embed.add_field(name="Winners", value=data.winner_count, inline=False)
            embed.add_field(name="Giveaway ID", value=data.message_id, inline=False)
            embed.add_field(name=f"Winners [{len(data.winners)}]", value=winners, inline=False)
            embed.add_field(name=f"Participants [{len(data.participants)}]", value=participants, inline=False)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

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

        if not chan.permissions_for(ctx.author).send_messages:
            return await ctx.respond(f"You dont have the perms to send messages in {chan.mention}")

        if not chan.permissions_for(ctx.me).send_messages:
            return await ctx.respond("It seems that the BobCat permissions for the message you are trying to send are missing!")

        dashboard = Guild.get(str(ctx.guild.id)).run().dashboard

        if coins and not dashboard.economy["status"]:
            return await ctx.respond("Oh no! it seems that Economy is currently disabled!")

        if xp and not dashboard.leveling["status"]:
            return await ctx.respond("Oh no! it seems that Leveling is currently disabled!")

        winner_count = int(winners or 1)
        description = description or ""
        ping = ping_role.mention if ping_role else ""

        duration = humanfriendly.parse_timespan(time)
        epochEnd = pyTime.time() + duration
        end_time = datetime.fromtimestamp(epochEnd).strftime("%m.%d.%Y %H:%M")
        giveaway_id = v.uuid(length=12, strCase="upper/lower/nums")

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"🎉 {prize} 🎉",
            description=description,
        )
        embed.add_field(name="Ends", value=f"<t:{int(epochEnd)}:R> (<t:{int(epochEnd)}:f>)", inline=False)
        embed.add_field(name="Hosted by", value=ctx.author.mention, inline=False)
        embed.add_field(name="Winners", value=f"**{winner_count}**", inline=False)
        embed.add_field(name="Participants", value="**0**", inline=False)
        embed.set_footer(text=f"Click on the button below to participate! - Giveaway ID: {giveaway_id}")

        try:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Join Giveaway", style=discord.ButtonStyle.blurple, custom_id="JoinGiveaway"))
            msg = await chan.send(content=ping, embed=embed, view=view)

            Giveaway(
                id=giveaway_id,
                guild_id=str(ctx.guild.id),
                channel_id=str(chan.id),
                channel_name=chan.name,
                message_id=str(msg.id),
                author_id=str(ctx.author.id),
                end_epoch=epochEnd,
                end_timestamp=end_time,
                prize=prize,
                winner_count=winner_count,
                status="Ongoing",
                participants=[],
                winners=[],
                give_xp={"enabled": bool(xp), "amount": xp or 0},
                give_coins={"enabled": bool(coins), "amount": coins or 0},
                embed_title=embed.title,
                embed_desc=embed.description or "",
            ).insert()

            await ctx.respond("The giveaway was successfully created", ephemeral=True)
        except Exception:
            await ctx.respond("Giveaway creation failed", ephemeral=True)

    @giveaway.command(description="Shows active giveaways")
    async def list(self, ctx):
        data = Giveaway.find(
            Giveaway.guild_id == str(ctx.guild.id),
            Giveaway.status == "Ongoing",
        ).run()

        active = []

        for item in data:
            guild = self.client.get_guild(int(item.guild_id))
            channel = guild.get_channel(int(item.channel_id))
            msg = await channel.fetch_message(int(item.message_id))
            winner_word = "winner" if item.winner_count == 1 else "winners"

            active.append(
                f"{item.id} | [`{msg.id}`]({msg.jump_url}) | **{item.winner_count}** {winner_word} | "
                f"**Prize:** {item.prize} | **Ends at:** <t:{int(item.end_epoch)}:f>"
            )

        if not active:
            return await ctx.respond("There are **no active giveaways** running.")

        await ctx.respond(f"**Active Giveaways**\n" + "\n".join(active))

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
            return await ctx.respond(f"I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)

        if not data.participants:
            return await ctx.respond("No valid entrants, so a winner could not be determined!")

        user_id = random.choice(data.participants)
        user = ctx.guild.get_member(int(user_id)) or await ctx.guild.fetch_member(int(user_id))
        await ctx.respond(f"{ctx.author.mention} rerolled the giveaway! Congratulations {user.mention}!")

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
            return await ctx.respond(f"I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)

        channel = await ctx.guild.fetch_channel(int(data.channel_id))
        message = await channel.fetch_message(int(data.message_id))

        if data.participants:
            user_id = random.choice(data.participants)
            user = ctx.guild.get_member(int(user_id)) or await ctx.guild.fetch_member(int(user_id))
            data.winners = [user_id]
            winner_text = user.mention
            await message.reply(content=f"Congratulations {user.mention}! You won **{data.prize}**")
        else:
            data.winners = []
            winner_text = ""
            await message.reply(content="No valid entrants, so a winner could not be determined!")

        data.status = "Ended"
        data.save()

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))

        embed = discord.Embed(
            title=f"🎉 {data.prize} 🎉 [ENDED]",
            description=(
                f"Ended: <t:{int(pyTime.time())}:R> (<t:{int(pyTime.time())}:f>)"
                f"\nHosted by: <@{data.author_id}>"
                f"\nParticipants: **{len(data.participants)}**"
                f"\nWinners: {winner_text}"
            )
        )
        await message.edit(embed=embed, view=view)
        await ctx.respond(f"Successfully ended giveaway `{giveaway_id}`", ephemeral=True)

    @giveaway.command(description="Delete a giveaway")
    @discord.option("giveaway_id", description="ID of giveaway to delete", required=True)
    async def delete(self, ctx, giveaway_id):
        data = Giveaway.find_one(
            Giveaway.guild_id == str(ctx.guild.id),
            Or(
                Giveaway.id == str(giveaway_id),
                Giveaway.message_id == str(giveaway_id),
            ),
        ).run()

        if data is None:
            return await ctx.respond(f"I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)

        channel = await ctx.guild.fetch_channel(int(data.channel_id))
        message = await channel.fetch_message(int(data.message_id))
        await message.delete()

        data.delete()
        await ctx.respond(f"Successfully deleted giveaway `{giveaway_id}`", ephemeral=True)

def setup(client):
    client.add_cog(GiveawayCog(client))