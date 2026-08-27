import os
import json
import discord
import speedtest
import time, asyncio, humanize, datetime
from discord.ext import commands, pages
from modules import bot as v
from modules.models import Guild

TRIAL_DAYS = {
    "1 Month": 31,
    "2 Months": 62,
    "3 Months": 93,
}

devs = json.load(open("modules/devs.json"))
def is_dev():
    async def predicate(ctx: discord.ApplicationContext):
        for dev in devs["team"]:
            if int(ctx.author.id) == int(dev['id']):
                return True
        
        await ctx.respond("You are not a developer")
        return False
    return commands.check(predicate)

class Owner(commands.Cog):
    def __init__(self, client):
        self.client = client

    dev_command = discord.SlashCommandGroup(name="dev", description="Developer only commands", guild_ids=v.guild_ids, checks=[is_dev().predicate])
    
    @dev_command.command(name="guilds", description="Gets all the guilds the bot is in")
    async def guilds(self, ctx):
        embed1 = discord.Embed(
            colour=0xed5757, 
            title="⌛ Getting all the Guilds",
            timestamp=discord.utils.utcnow()
        )
        msg: discord.Interaction = await ctx.respond(embed=embed1)

        emby = discord.Embed(title=f"{v.client.user.name}'s Guilds", colour=0x5865f2)
        for guild in v.client.guilds[:20]:
            emby.add_field(name=guild.name, value=guild.id, inline=False)
        emby.set_footer(text=f"{len(v.client.guilds)} guilds joined")

        await msg.edit(embed=emby)

    @dev_command.command(name="guild", description="Gets a guilds info")
    async def guild(self, ctx, guild: str):
        server = self.client.get_guild(int(guild))
        if not server:
            return await ctx.respond("Guild not found")
        
        members = server.members
        human_members = [m for m in members if not m.bot]
        bot_members = [m for m in members if m.bot]
        
        embed = discord.Embed(title=f"Guild Information: {server.name}", colour=0x5865f2)
        embed.add_field(name="Server ID", value=f"```{server.id}```", inline=False)
        embed.add_field(name="Server Owner", value=f"```{server.owner}```", inline=False)
        embed.add_field(name="Server Members", value=f"```{len(human_members)}```", inline=False)
        embed.add_field(name="Server Bot Count", value=f"```{len(bot_members)}```", inline=False)
        embed.set_footer(text=f"{len(self.client.guilds)} guilds joined")
        await ctx.respond(embed=embed)
    
    @dev_command.command(name="ping", description="Gets the currant ping of the bot")
    async def ping(self, ctx):
        ws_ping = f'{(self.client.latency * 1000):.0f}'

        start = time.perf_counter()
        await asyncio.sleep(0)
        end = time.perf_counter()
        trip = end - start
        rt_ping = f'{(trip*1000):.0f}'
        
        embedCMD = discord.Embed(
            color=0x5865F2,
            title="Bot's Latency",
            description=(
                f"<:blurpledot:1178837842936483890> **Ping:** `{ws_ping}ms` ({humanize.precisedelta(datetime.timedelta(seconds=self.client.latency))}) "
                f"\n<:blurpledot:1178837842936483890> **API:** `{rt_ping}ms` ({humanize.precisedelta(datetime.timedelta(seconds=trip))})"
            )
        )
        await ctx.respond(embed=embedCMD)
    
    @dev_command.command(name="reload", description="Reloads all the cogs")
    async def _reboot(self, ctx):
        rl_ac = discord.Embed(title="Reloading all cogs", colour=0xed5757)
        msg = await ctx.respond(embed=rl_ac)

        try:
            for foldername in os.listdir('./cogs'):
                if foldername == "__pycache__":
                    continue
                for filename in os.listdir(f"./cogs/{foldername}"):
                    if filename.endswith('.py'):
                        self.client.reload_extension(f'cogs.{foldername}.{filename[:-3]}')
        except Exception as e:
            emError = discord.Embed(title="❎ Reload Failed!", colour=0xed5757)
            emError.add_field(name=f"Failed to reload: `{filename}`", value=f"{e}")
            return await msg.edit(embed=emError)

        await asyncio.sleep(1)
        rl_com = discord.Embed(title="✅ Reload Complete!", colour=0x57f287)
        await msg.edit(embed=rl_com)

    @dev_command.command(name="uptime", description="Gets the bots uptime")
    async def uptime(self, ctx):
        embed = discord.Embed(
            color=0x5865f2,
            title="Uptime", 
            description=self.get_bot_uptime()
        )
        await ctx.respond(embed=embed)
        
    @dev_command.command(name="speedtest", description="Runs a speedtest")
    async def speedtest(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        servers = []
        threads = None
        s = speedtest.Speedtest()
        s.get_servers(servers)
        s.get_best_server()
        s.download(threads=threads)
        s.upload(threads=threads)

        ping = s.results.ping
        down = s.results.download
        up = s.results.upload

        embed=discord.Embed(color=0x5865f2)
        embed.add_field(name="Ping", value=f"{ping :.2f} ms", inline=True)
        embed.add_field(name="Download", value=f"{down / 1024 / 1024:.2f} Mbps", inline=True)
        embed.add_field(name="Upload", value=f"{up / 1024 / 1024:.2f} Mbps", inline=True)
        await ctx.respond(embed=embed)

    ## Status ##
    status = dev_command.create_subgroup(name="status", description="Bots status")

    @status.command(name="list", description="Lists all the status' in the bot")
    async def _list(self, ctx):
        with open("modules/status.json", "r") as f:
            statuses = json.load(f)
        
        my_pages = []
        for idx, status in enumerate(statuses["status"], 1):
            em = discord.Embed(
                color=v.blurple,
                title=f"Status {idx}",
                description=f"{status['name']}"
            )
            em.add_field(name="Type", value=f"{status['type']}", inline=False)
            em.add_field(name="ID", value=f"{status['id']}", inline=False)
            my_pages.append(pages.Page(embeds=[em]))

        page_buttons = [
            pages.PaginatorButton("first", label="<<-", style=discord.ButtonStyle.gray),
            pages.PaginatorButton("prev", label="<-", style=discord.ButtonStyle.gray),
            pages.PaginatorButton("next", label="->", style=discord.ButtonStyle.gray),
            pages.PaginatorButton("last", label="->>", style=discord.ButtonStyle.gray),
        ]
        paginator = pages.Paginator(
            pages=my_pages, custom_buttons=page_buttons,
            show_disabled=True, show_indicator=False, use_default_buttons=False, loop_pages=True,
        )
        await paginator.respond(ctx.interaction, ephemeral=False)
    
    types = ["Watching", "Listening", "Playing", "Streaming", "Competing"]
    @status.command(name="add", description="Adds a status to the bot")
    @discord.option("name", description="The name to add", required=True)
    @discord.option("type", description="The type of name", required=True, choices=types)
    async def _add(self, ctx, name, type):
        _id = v.uuid(8, strCase="upper/lower/nums/special")

        with open("modules/status.json", "r") as f:
            status = json.load(f)
        status["status"].append({
            "id": _id,
            "name": name,
            "type": type
        })
        with open("modules/status.json", "w") as f:
            json.dump(status, f, indent=2)

        emb = discord.Embed(
            color=v.success,
            title="Added new status to the status loop",
            description=f"> **Name:** {name} \n> **Type:** {type} \n> **ID:** {_id}"
        )
        await ctx.respond(embed=emb)

    @status.command(name="remove", description="Removes a status from the bot")
    @discord.option("id", description="The id of the status to remove", required=True)
    async def _remove(self, ctx, id):
        with open("modules/status.json", "r") as f:
            status = json.load(f)
        status["status"].remove(next(x for x in status["status"] if x["id"] == id))
        with open("modules/status.json", "w") as f:
            json.dump(status, f, indent=2)

        emb = discord.Embed(
            color=v.success,
            title="Removed status from the status loop",
            description=f"> **ID:** {id}"
        )
        await ctx.respond(embed=emb)

    ## Premium ##
    premium = dev_command.create_subgroup(name="premium", description="Premium commands")
    
    @premium.command(name="add", description="Adds a guild to premium")
    @discord.option("guild", discord.Guild, description="The guild to add", required=True)
    @discord.option("plan", description="The plan to give", required=False, choices=['lifetime', 'trial'])
    @discord.option("trail_length", description="The length of the trial", required=False, choices=list(TRIAL_DAYS.keys()))
    @is_dev()
    async def premium_add(self, ctx: discord.ApplicationContext, guild: discord.Guild, plan: str="trial", trail_length: str="1 Month"):
        doc = await Guild.get(str(guild.id))
        if doc is None:
            return await ctx.respond("That guild has no config yet — has the bot fully initialized it?", ephemeral=True)

        code = v.uuid(length=16, strCase="upper/lower/nums")

        now = datetime.datetime.now()
        period_end = None
        if plan == "trial":
            period_end = now + datetime.timedelta(days=TRIAL_DAYS[trail_length])

        premium = {
            "id": code,
            "status": True,
            "active": True,
            "plan": plan,
            "user_id": ctx.author.id,
            "subscribed_at": now,
            "period_end": period_end,  # ✅ Use period_end instead of code_expiry
            "code_expiry": period_end,  # Keep for backwards compatibility
        }

        doc.premium = premium
        await doc.save()

        emb = discord.Embed(
            color=v.success,
            title="Gifted a Premium subscription",
            description=(
                f"> **Guild:** {guild.name}"
                f"\n> **Code:** {premium['id']}"
                f"\n> **Plan:** {premium['plan']}"
                if plan == "lifetime" else
                f"\n> **Plan:** {premium['plan']} for {trail_length}"
                f"\n> **Expires:** {period_end.strftime('%Y-%m-%d %H:%M:%S') if period_end else 'Never'}"
            )
        )
        await ctx.respond(embed=emb)

        await v.push_notification(guild, 'info', 'You have been given premium!', "🎁 Surprise! Someone just gifted you Premium! Unlock exclusive perks and level up your experience")

    @premium.command(name="remove", description="Removes a guild from premium")
    @discord.option("guild", discord.Guild, description="The guild to remove", required=True)
    async def premium_remove(self, ctx: discord.ApplicationContext, guild):
        doc = await Guild.get(str(guild.id))
        if doc is None:
            return await ctx.respond("That guild has no config yet.", ephemeral=True)

        doc.premium['status'] = False
        doc.premium['active'] = False
        await doc.save()

        emb = discord.Embed(
            color=v.success,
            timestamp=datetime.datetime.utcnow(),
            title="Removed Premium",
            description=f"> **Guild:** {guild.name}"
        )
        await ctx.respond(embed=emb)
    
def setup(client):
    client.add_cog(Owner(client))