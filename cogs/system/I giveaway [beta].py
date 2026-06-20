import discord, random, humanfriendly
import time as pyTime
from datetime import datetime
from modules import bot as v
from discord.ext import commands
from discord.ext import tasks


class Giveaway(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False

    @tasks.loop(minutes=1)
    async def giveawayCheck(self):
        giveaways = giveaways_fetchall()
        for idx, data in enumerate(giveaways):
            if not data:
                continue
        
            guilds = data['guild']
            channels = data['channel']['id']
            messages = data['message']
            time = data['time']['epoch']
            prize = data['prize']
            winnerss = data['winners']
            status = data['status']
            participants = data['participants']

            # if status == "Ended" or status == "Draft":
            #     return
            if status == "Ongoing" and pyTime.time() >= time:
                guild = await v.client.fetch_guild(int(guilds))
                channel = await guild.fetch_channel(channels)
                msg = await channel.fetch_message(messages)
                
                if guild is None or channel is None:
                    return
                
                if participants:
                    winners = random.choices(participants, k=int(winnerss))
                    
                    wins = []
                    gwinners = []
                    for user in winners:
                        member = await guild.fetch_member(int(user))
                        wins.append(member.mention)
                        gwinners.append(member.id)

                    for em in msg.embeds:
                        embed = em.to_dict()
                        embed["title"] = f"{data['embed_title'].format(prize=prize)} [ENDED]"
                        embed["fields"][0]["name"] = f"Ended"
                    emby = discord.Embed().from_dict(embed)

                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))
                    await msg.edit(embed=emby, view=view)

                    if len(participants) < int(winnerss):
                        await msg.reply(content="There were not enough participants to draw winners.")
                    else:
                        await msg.reply(content=f"Congratulations {', '.join(wins)}! You won **{prize}**")
                    
                    v.db.update_server_config(
                        guild=guild, 
                        key=f'giveaways.{idx}.gwinners',
                        value=gwinners
                    )
                else:
                    for em in msg.embeds:
                        embed = em.to_dict()
                        embed["title"] = f"{data['embed_title'].format(prize=prize)} [ENDED]"
                        embed["fields"][0]["name"] = f"Ended"
                    emby = discord.Embed().from_dict(embed)

                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))
                    await msg.edit(embed=emby, view=view)
                    await msg.reply(content="No valid entrants, so a winner could not be determined!")

                v.db.update_server_config(
                    guild=guild, 
                    key=f'giveaways.{idx}.status',
                    value="Ended"
                )
    ###

    giveaway = discord.SlashCommandGroup("giveaway", "Giveaway Commands")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.persistent_views_added:
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))
            self.client.add_view(view)

            # giveaways = giveaways_fetchall()
            # for table in giveaways:
            #     self.client.add_view(JoinGiveaway(self.client, table.get('time'), table.get('prize')))
            
            self.persistent_views_added = True

        if not self.giveawayCheck.is_running():
            self.giveawayCheck.start()

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.data.get("custom_id") == "JoinGiveaway":
            gway_data = v.db.get_server_config(interaction.guild)
            for index, gway in enumerate(gway_data['giveaways']):
                if gway['message'] == interaction.message.id:
                    idx, data = index, gway
                    break

            if not data:
                return await interaction.response.send_message("You cannot enter or leave this giveaway because it has already ended!", ephemeral=True)
            
            guilds = data.get('guild')
            channels = data.get('channel').get('id')
            messages = data.get('message')
            time = data.get('time')
            prize = data.get('prize')
            participants = data.get('participants')
            
            guild = await v.client.fetch_guild(int(guilds))
            channel = await guild.fetch_channel(int(channels))
            msg = await channel.fetch_message(int(messages))

            if not f"{interaction.user.id}" in participants:
                participants.append(f"{interaction.user.id}")

                v.db.update_server_config(
                    guild=interaction.guild, 
                    key=f'giveaways.{idx}.participants',
                    value=participants
                )
                
                for em in msg.embeds:
                    embed = em.to_dict()
                    embed["fields"][3]["value"] = f"**{len(participants)}**"
                await msg.edit(embed=discord.Embed().from_dict(embed))

                await interaction.response.send_message(content=":white_check_mark: You're now participating in this giveaway!", view=None, ephemeral=True)
            else:
                participants.remove(f"{interaction.user.id}")
                
                v.db.update_server_config(
                    guild=interaction.guild, 
                    key=f'giveaways.{idx}.participants',
                    value=participants
                )

                for em in msg.embeds:
                    embed = em.to_dict()
                    embed["fields"][3]["value"] = f"**{len(participants)}**"
                await msg.edit(embed=discord.Embed().from_dict(embed))

                await interaction.response.send_message(content=":negative_squared_cross_mark: You're not participating in this giveaway anymore!", view=None, ephemeral=True)
            return
        
        if interaction.data.get("custom_id") == "GiveawaySummary":
            data = v.db.get_server_config(interaction.guild)
            for index, gway in enumerate(data['giveaways']):
                if gway['message'] == interaction.message.id:
                    idx, data = index, gway
                    break

            if not data:
                return await interaction.response.send_message("You cannot enter or leave this giveaway because it has already ended!", ephemeral=True)
            
            guilds = data['guild']
            channels = data['channel']['id']
            messages = data['message']
            time = data['time']['epoch']
            prize = data['prize']
            winner = data['winners']
            author = data['author']
            gwinners = data['gwinners']
            participants = data['participants']

            guild = await v.client.fetch_guild(int(guilds))
            channel = await guild.fetch_channel(int(channels))
            msg = await channel.fetch_message(int(messages))

            date = datetime.fromtimestamp(int(time), v.datetimes(interaction.guild.id))
            date = date.strftime("%x, %X %p")

            Winners = ""
            if gwinners != "[]":
                for item in gwinners:
                    Winners += f"<@{item}> "
            else:
                Winners = "No winners"
            
            Participants = ""
            if participants != "[]":
                for user in participants:
                    Participants += f"<@{user}> ({user})" + "\n"
            else:
                Participants = "No Participants"

            w = f'{Winners}' if Winners != '' else '** **'
            e = f'{Participants}' if Participants != '' else '** **'

            embed = discord.Embed(title="Giveaway Summary")
            embed.add_field(name="Ended", value=f"{date}", inline=False)
            embed.add_field(name="Host", value=f"<@{author}> ({author})", inline=False)
            embed.add_field(name="Prize", value=f"{prize}", inline=False)
            embed.add_field(name="Winners", value=f"{winner}", inline=False)
            embed.add_field(name="Giveaway ID", value=f"{msg.id}", inline=False)
            embed.add_field(name=f"Winners [{len(gwinners)}]", value=f"{w}", inline=False)
            embed.add_field(name=f"Participants [{len(participants)}]", value=f"{e}", inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    
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
        chan: discord.TextChannel = channel if channel else ctx.channel
        if not chan.permissions_for(ctx.author).send_messages:
            return await ctx.respond(f"You dont have the perms to send messages in {channel.mention}")
        if not chan.permissions_for(ctx.me).send_messages:
            return await ctx.respond("It seems that the BobCat permissions for the message you are trying to send are missing!")
        
        # Ecoinomy coins
        coins = v.db.get_dash(ctx.guild.id)['economy']['status']
        if coins == False:
            return await ctx.respond("Oh no! it seems that Economy is currently disabled!")

        # Leveling xp
        xp = v.db.get_dash(ctx.guild.id)['leveling']['status']
        if xp == False:
            return await ctx.respond("Oh no! it seems that Leveling is currently disabled!")
        
        winners = "1" if not winners else winners
        channel = ctx.channel if not channel else channel
        description = "" if not description else description
        ping_role = "" if not ping_role else ping_role.mention

        time = humanfriendly.parse_timespan(time)
        epochEnd = pyTime.time() + time
        end_time = datetime.fromtimestamp(epochEnd).strftime('%m.%d.%Y %H:%M')

        uuid = v.uuid(length=12, strCase="upper/lower/nums")

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"🎉 {prize} 🎉",
            description=f"{description}",
        )
        embed.add_field(name="Ends", value=f"<t:{int(epochEnd)}:R> (<t:{int(epochEnd)}:f>)", inline=False)
        embed.add_field(name="Hosted by", value=f"{ctx.author.mention}", inline=False)
        embed.add_field(name="Winners", value=f"**{winners}**", inline=False)
        embed.add_field(name="Participants", value="**0**", inline=False)
        embed.set_footer(text=f"Click on the button below to participate! - Giveaway ID: {uuid}")

        try:
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Join Giveaway", style=discord.ButtonStyle.blurple, custom_id="JoinGiveaway"))
            msg = await channel.send(content=ping_role, embed=embed, view=view)
            view.message = msg

            data = v.db.get_server_config(ctx.guild)['giveaways']
            data.append({
                'id': uuid, 'guild': ctx.guild.id, 'name': 'giveaway', 'channel': { 'id': channel.id, 'name': channel.name }, 'message': msg.id, 'author': ctx.author.id, 'time': { 'epoch': epochEnd, 'timestamp': end_time }, 'prize': prize, 
                'winners': winners, 'status': 'Ongoing', 'gwinners': [], 'participants': [],
                'givexp': { 'enabled': True if coins else False, 'amount': coins },
                'givecoins': { 'enabled': True if xp else False, 'amount': xp },
                'embed_title': embed.title, 'embed_desc': embed.description
            })
            v.db.update_server_config(ctx.guild, key='giveaways', value=data)

            await ctx.respond("The giveaway was successfully created", ephemeral=True)
        except Exception as e:
            await ctx.respond("Giveaway creation failed", ephemeral=True)

    @giveaway.command(description="Shows active giveaways")
    async def list(self, ctx):
        data = giveaways_fetchall()

        active = []

        for item in data:
            gid = item.get("id")
            guild_id = int(item.get("guild"))
            channel_id = int(item.get("channel").get("id"))
            message_id = int(item.get("message"))
            time = int(item.get("time").get("epoch"))
            prize = item.get("prize")
            winners = item.get("winners")

            status = item.get('status')
            
            if status in ("Ended", "Draft"): # Skip ended or draft giveaways
                continue

            guild = self.client.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            
            msg = await channel.fetch_message(message_id)
            
            winner_word = "winner" if winners == "1" else "winners"

            active.append(
                f"{gid} | [`{msg.id}`]({msg.jump_url}) | **{winners}** {winner_word} | "
                f"**Prize:** {prize} | **Ends at:** <t:{time}:f>"
            )

        # If no active giveaways exist
        if not active:
            return await ctx.respond("There are **no active giveaways** running.")

        items = "\n".join(active)

        return await ctx.respond((
            f"**Active Giveaways**"
            f"\n\n"
            f"{items}"
        ))
    
    @giveaway.command(description="Rerolls a new winner from a giveaway")
    @discord.option("giveaway_id", str, description="ID of giveaway to reroll", required=True)
    async def reroll(self, ctx, giveaway_id):
        data = v.db.get_server_config(ctx.guild)['giveaways']
        for index, gway in enumerate(data):
            if str(gway['message']) == giveaway_id:
                idx, data = index, gway
                break

        if not data:
            return await ctx.respond(f"I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)
        
        guild = self.client.get_guild(data.get('guild'))
        channel = guild.get_channel(data.get('channel').get('id'))
        message = await channel.fetch_message(data.get('message'))

        participants = data.get('participants')
        if participants != "[]":
            member = random.choice(participants)
            user = guild.get_member(int(member))

            await ctx.respond(f"{ctx.author.mention} rerolled the giveaway! Congratulations {user.mention}!")
            return
        else:
            return await message.reply(content="No valid entrants, so a winner could not be determined!")
    
    @giveaway.command(description="End a giveaway")
    @discord.option("giveaway_id", str, description="ID of giveaway to end", required=True)
    async def end(self, ctx, giveaway_id):
        gway_data = v.db.get_server_config(ctx.guild)['giveaways']
        for index, gway in enumerate(gway_data):
            if str(gway['message']) == giveaway_id:
                idx, data = index, gway
                break
        
        if data is None:
            return await ctx.respond(f"I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True)
        
        times = humanfriendly.parse_timespan(str(data.get('time').get("epoch")))
        epochEnd = pyTime.time() + times

        guild = ctx.guild
        channel = await guild.fetch_channel(data.get('channel').get('id'))
        message = await channel.fetch_message(data.get('message'))

        participants = data.get('participants')
        if participants:
            member = random.choice(participants)
            user = guild.get_member(int(member))

            winners = f"{user.mention}"
            await message.reply(content=f"Congratulations {user.mention}! You won **{data.get('prize')}**")
        else:
            winners = ""
            await message.reply(content="No valid entrants, so a winner could not be determined!")

        v.db.update_server_config(
            guild=ctx.guild,
            key=f'giveaways.{idx}.status',
            value='Ended'
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Giveaway Summary", style=discord.ButtonStyle.gray, custom_id="GiveawaySummary"))

        embed = discord.Embed(
            title=f"🎉 {data.get('prize')} 🎉 [ENDED]",
            description=(
                f"Ended: <t:{int(epochEnd)}:R> (<t:{int(epochEnd)}:f>)"
                f"\nHosted by: {ctx.author.mention}"
                f"\nParticipants: **{len(data.get('participants'))}**"
                f"\nWinners: {winners}"
            )
        )
        await message.edit(embed=embed, view=view)
        await ctx.respond(f"Successfully ended giveaway `{giveaway_id}`", ephemeral=True)

    # @giveaway.command(description="Delete a giveaway")
    @discord.option("giveaway_id", description="ID of giveaway to end", required=True)
    async def delete(self, ctx, giveaway_id):
        gway_data = v.db.get_server_config(ctx.guild)
        for index, gway in enumerate(gway_data['giveaways']):
            if gway['message'] == int(giveaway_id):
                idx, data = index, gway
                break

        if not data:
            return await ctx.respond(f"I could not find a giveaway with the ID `{giveaway_id}`", ephemeral=True) 

        guild = await v.client.fetch_guild(int(data.get('guild')))
        channel = await guild.fetch_channel(int(data.get('channel').get('id')))
        message = await channel.fetch_message(int(data.get('message')))

        await message.delete()

        gway_data['giveaways'].pop(idx)

        v.db.update_server_config(
            guild=ctx.guild,
            key='giveaways',
            value=gway_data['giveaways']
        )
        
        await ctx.respond(f"Successfully deleted giveaway `{giveaway_id}`", ephemeral=True)

def setup(client):
    client.add_cog(Giveaway(client))

def giveaways_fetchall() -> list:
    gways = []
    for data in v.db.db.find({}):
        for giveaways in data['Bot'].get('giveaways'):
            gways.append(giveaways)
    return gways