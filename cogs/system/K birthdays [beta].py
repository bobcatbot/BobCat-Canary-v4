import discord
import datetime
from discord.ext import commands, tasks
from modules import bot as v
from modules.models import Birthday as Birthday, Guild

def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def next_birthday(date: datetime.datetime) -> datetime.datetime:
    """Returns the next occurrence of a birthday from today."""
    now = datetime.datetime.now()
    next_bd = date.replace(year=now.year)
    if next_bd < now:
        next_bd = next_bd.replace(year=now.year + 1)
    return next_bd

def get_bdays(guild_id) -> list[Birthday]:
    return Birthday.find(Birthday.guild_id == str(guild_id)).run()

class BirthdayTimers(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.birthday_check.start()
        self.role_reset.start()

    def cog_unload(self):
        self.birthday_check.cancel()
        self.role_reset.cancel()

    @tasks.loop(minutes=1)
    async def birthday_check(self):
        now = datetime.datetime.now()

        for guild in self.client.guilds:
            config = Guild.get(str(guild.id)).run().dashboard.birthdays

            if not config.get("status"):
                continue

            channel_id = config.get("channel_id")
            if not channel_id:
                continue

            channel = guild.get_channel(int(channel_id))
            if not channel:
                continue

            birthdays = get_bdays(guild.id)

            for birthday in birthdays:
                if birthday.wished or not birthday.date:
                    continue

                date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
                if now.day != date.day or now.month != date.month:
                    continue

                member = guild.get_member(int(birthday.user_id))
                if not member:
                    continue

                birthday_role_id = config.get("birthday_role")
                if birthday_role_id:
                    role = guild.get_role(int(birthday_role_id))
                    if role:
                        await member.add_roles(role)

                age = now.year - date.year
                await channel.send(v.render_placeholders(
                    config["message"],
                    user=member,
                    age=age
                ))

                birthday.wished = True
                birthday.wished_at = now
                birthday.save()

    @birthday_check.before_loop
    async def before_birthday_check(self):
        await self.client.wait_until_ready()

    @tasks.loop(hours=24)
    async def role_reset(self):
        """Removes birthday role 24 hours after it was assigned."""
        now = datetime.datetime.now()

        for guild in self.client.guilds:
            config = Guild.get(str(guild.id)).run().dashboard.birthdays
            birthday_role_id = config.get("birthday_role")
            birthdays = get_bdays(guild.id)

            for birthday in birthdays:
                if not birthday.wished or not birthday.wished_at:
                    continue

                if (now - birthday.wished_at).total_seconds() < 86400:
                    continue

                if birthday_role_id:
                    member = guild.get_member(int(birthday.user_id))
                    if member:
                        role = guild.get_role(int(birthday_role_id))
                        if role:
                            await member.remove_roles(role)

                birthday.wished = False
                birthday.wished_at = None
                birthday.save()

    @role_reset.before_loop
    async def before_role_reset(self):
        await self.client.wait_until_ready()

class BirthdayCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.slash_command(name="birthdays", description="Show all birthdays for the current month")
    async def birthdays(self, ctx: discord.ApplicationContext):
        birthdays = get_bdays(ctx.guild.id)
        now = datetime.datetime.now()
        entries = []

        for birthday in birthdays:
            if not birthday.date:
                continue

            birthday_date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
            if birthday_date.month != now.month:
                continue

            user = ctx.guild.get_member(int(birthday.user_id))
            username = user.mention if user else f"<@{birthday.user_id}>"
            age = now.year - birthday_date.year
            entries.append(f"**{birthday_date.strftime('%d %B')}** — {username} ({ordinal(age)})")

        if not entries:
            return await ctx.respond("No birthdays this month.", ephemeral=True)

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=f"Birthdays in {now.strftime('%B')}",
            description="\n".join(entries)
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="next-birthdays", description="Shows the next 10 upcoming birthdays")
    async def next_birthdays(self, ctx: discord.ApplicationContext):
        birthdays = get_bdays(ctx.guild.id)

        if not birthdays:
            return await ctx.respond("I don't know **any** birthdays **yet**.", ephemeral=True)

        entries = []

        for birthday in birthdays:
            if not birthday.date:
                continue

            birthday_date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
            next_bd = next_birthday(birthday_date)
            user = ctx.guild.get_member(int(birthday.user_id))
            username = user.mention if user else f"<@{birthday.user_id}>"
            age = next_bd.year - birthday_date.year
            entries.append((next_bd, f"**{next_bd.strftime('%d %B')}** — {username} ({ordinal(age)})"))

        entries.sort(key=lambda x: x[0])
        top10 = entries[:10]

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title="Upcoming Birthdays",
            description="\n".join(entry[1] for entry in top10)
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="birthday", description="Show yours or another member's birthday")
    @discord.option("member", description="The member to view", required=False)
    async def view_birthday(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        member = member or ctx.author
        birthday = Birthday.get(f"{ctx.guild.id}_{member.id}").run()

        if birthday is None or not birthday.date:
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"{member.mention} has no birthday set."
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
        next_bd = next_birthday(date)
        age = next_bd.year - date.year
        days_away = (next_bd - datetime.datetime.now()).days + 1

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"{member.mention}'s **{ordinal(age)}** birthday is in **{days_away}** days on **{date.strftime('%d %B %Y')}**."
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="set-birthday", description="Set yours or another member's birthday")
    @discord.option("date", description="Birthday date (YYYY-MM-DD)", required=True)
    @discord.option("member", description="The member to set the birthday of", required=False)
    async def set_birthday(self, ctx: discord.ApplicationContext, date: str, member: discord.Member = None):
        member = member or ctx.author
        birthday = Birthday.get(f"{ctx.guild.id}_{member.id}").run()

        if birthday is not None:
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"{member.mention} already has a birthday set."
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        try:
            parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            embed = discord.Embed(
                color=v.error,
                description="❌ Invalid date format. Please use `YYYY-MM-DD`."
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        next_bd = next_birthday(parsed)
        age = next_bd.year - parsed.year
        days_away = (next_bd - datetime.datetime.now()).days + 1

        Birthday(
            id=f"{ctx.guild.id}_{member.id}",
            guild_id=str(ctx.guild.id),
            user_id=str(member.id),
            date=parsed.strftime("%Y-%m-%d"),
            age=age,
            wished=False,
            wished_at=None
        ).insert()

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"Duly noted, I'll wish {member.mention}'s **{ordinal(age)}** birthday in **{days_away}** days on **{parsed.strftime('%d %B %Y')}**."
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="remove-birthday", description="Remove your birthday")
    async def remove_birthday(self, ctx: discord.ApplicationContext):
        birthday = Birthday.get(f"{ctx.guild.id}_{ctx.author.id}").run()

        if birthday is None:
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description="You have no birthday set."
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        birthday.delete()
        await ctx.respond("I will no longer wish **your** birthday.", ephemeral=True)

def setup(client):
    client.add_cog(BirthdayTimers(client))
    client.add_cog(BirthdayCommands(client))