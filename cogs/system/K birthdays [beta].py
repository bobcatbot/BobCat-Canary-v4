import discord
import datetime
from discord.ext import commands, tasks
import pytz
from modules import bot as v


def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def next_birthday(date: datetime.datetime) -> datetime.datetime:
    """Returns the next occurrence of a birthday from today."""
    now = datetime.datetime.now()
    next_bd = date.replace(year=now.year)
    if next_bd < now:
        next_bd = next_bd.replace(year=now.year + 1)
    return next_bd

def get_bdays(guild_id) -> dict:
    return v.db.get_server_config(guild_id)["birthdays"]


# ── Background Tasks ──────────────────────────────────────────────────────────
class Birthdays(commands.Cog):
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
            dash = v.db.get_dash(guild.id)
            if not dash:
                continue

            config = dash["birthdays"]
            if not config.get("status"):
                continue

            channel_id = config.get("channel_id")
            if not channel_id:
                continue

            channel = guild.get_channel(int(channel_id))
            if not channel:
                continue

            bdays = v.db.get_server_config(guild.id)["birthdays"]

            for user_id, birthday in bdays.items():
                # Skip if already wished today
                if birthday.get("wished", False):
                    continue

                date = datetime.datetime.strptime(birthday["date"], "%Y-%m-%d")
                if now.day != date.day or now.month != date.month:
                    continue

                member = guild.get_member(int(user_id))
                if not member:
                    continue

                # Add birthday role if configured
                birthday_role_id = config.get("birthday_role")
                if birthday_role_id:
                    role = guild.get_role(int(birthday_role_id))
                    if role:
                        await member.add_roles(role)

                age = now.year - date.year
                await channel.send(config["message"].format(user=member, age=age))

                # Single atomic write
                v.db.update_server_config(guild.id, key=f"birthdays.{user_id}", value={
                    **birthday,
                    "wished": True,
                    "wished_at": now.strftime("%Y-%m-%d %H:%M:%S")
                })
    @birthday_check.before_loop
    async def before_birthday_check(self):
        await self.client.wait_until_ready()

    @tasks.loop(hours=24)
    async def role_reset(self):
        """Removes birthday role 24 hours after it was assigned."""
        now = datetime.datetime.now()

        for guild in self.client.guilds:
            dash = v.db.get_dash(guild.id)
            if not dash:
                continue

            config = dash["birthdays"]
            birthday_role_id = config.get("birthday_role")
            bdays = v.db.get_server_config(guild.id)["birthdays"]

            for user_id, birthday in bdays.items():
                if not birthday.get("wished", False):
                    continue

                # Guard against None wished_at
                wished_at_str = birthday.get("wished_at")
                if not wished_at_str:
                    continue

                wished_at = datetime.datetime.strptime(wished_at_str, "%Y-%m-%d %H:%M:%S")
                if (now - wished_at).total_seconds() < 86400:
                    continue

                # Remove birthday role if configured
                if birthday_role_id:
                    member = guild.get_member(int(user_id))
                    if member:
                        role = guild.get_role(int(birthday_role_id))
                        if role:
                            await member.remove_roles(role)

                # Single atomic write
                v.db.update_server_config(guild.id, key=f"birthdays.{user_id}", value={
                    **birthday,
                    "wished": False,
                    "wished_at": None
                })
    @role_reset.before_loop
    async def before_role_reset(self):
        await self.client.wait_until_ready()

# ── Commands ──────────────────────────────────────────────────────────────────
class BirthdayCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.slash_command(name="birthdays", description="Show all birthdays for the current month")
    async def birthdays(self, ctx: discord.ApplicationContext):
        bdays = get_bdays(ctx.guild.id)
        now = datetime.datetime.now()

        entries = []
        for user_id, birthday_info in bdays.items():
            birthday_date = datetime.datetime.strptime(birthday_info["date"], "%Y-%m-%d")
            if birthday_date.month != now.month:
                continue

            user = ctx.guild.get_member(int(user_id))
            username = user.mention if user else f"<@{user_id}>"
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
        bdays = get_bdays(ctx.guild.id)

        if not bdays:
            return await ctx.respond("I don't know **any** birthdays **yet**.", ephemeral=True)

        now = datetime.datetime.now()
        entries = []

        for user_id, birthday_info in bdays.items():
            birthday_date = datetime.datetime.strptime(birthday_info["date"], "%Y-%m-%d")
            next_bd = next_birthday(birthday_date)  # sort by upcoming date, not birth year

            user = ctx.guild.get_member(int(user_id))
            username = user.mention if user else f"<@{user_id}>"
            age = next_bd.year - birthday_date.year
            entries.append((next_bd, f"**{next_bd.strftime('%d %B')}** — {username} ({ordinal(age)})"))

        entries.sort(key=lambda x: x[0])
        top10 = entries[:10]

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title="Upcoming Birthdays",
            description="\n".join(e[1] for e in top10)
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="birthday", description="Show yours or another member's birthday")
    @discord.option("member", description="The member to view", required=False)
    async def view_birthday(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        member = member or ctx.author
        bdays = get_bdays(ctx.guild.id)

        if not bdays.get(str(member.id)):
            return await ctx.respond(
                embed=discord.Embed(color=v.style(ctx.guild.id), description=f"{member.mention} has no birthday set."),
                ephemeral=True
            )

        birthday = bdays[str(member.id)]
        date = datetime.datetime.strptime(birthday["date"], "%Y-%m-%d")
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
        bdays = get_bdays(ctx.guild.id)

        if bdays.get(str(member.id)):
            return await ctx.respond(
                embed=discord.Embed(color=v.style(ctx.guild.id), description=f"{member.mention} already has a birthday set."),
                ephemeral=True
            )

        # Validate date format
        try:
            parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return await ctx.respond(
                embed=discord.Embed(color=v.error, description="❌ Invalid date format. Please use `YYYY-MM-DD`."),
                ephemeral=True
            )

        next_bd = next_birthday(parsed)
        age = next_bd.year - parsed.year
        days_away = (next_bd - datetime.datetime.now()).days + 1

        v.db.update_server_config(ctx.guild.id, key=f"birthdays.{member.id}", value={
            "date": parsed.strftime("%Y-%m-%d"),
            "wished": False,
            "wished_at": None
        })

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"Duly noted, I'll wish {member.mention}'s **{ordinal(age)}** birthday in **{days_away}** days on **{parsed.strftime('%d %B %Y')}**."
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="remove-birthday", description="Remove your birthday")
    async def remove_birthday(self, ctx: discord.ApplicationContext):
        bdays = get_bdays(ctx.guild.id)

        if not bdays.get(str(ctx.author.id)):
            return await ctx.respond(
                embed=discord.Embed(color=v.style(ctx.guild.id), description="You have no birthday set."),
                ephemeral=True
            )

        bdays.pop(str(ctx.author.id))
        v.db.update_server_config(ctx.guild.id, key="birthdays", value=bdays)
        await ctx.respond("I will no longer wish **your** birthday.", ephemeral=True)

def setup(client):
    client.add_cog(Birthdays(client))
    client.add_cog(BirthdayCommands(client))