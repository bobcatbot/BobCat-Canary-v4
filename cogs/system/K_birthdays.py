import discord
import datetime
from discord.ext import commands, tasks
from modules import bot as v
from modules.models import Birthday, Guild

def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def next_birthday(date: datetime.datetime, now: datetime.datetime = None) -> tuple[datetime.datetime, int]:
    """Returns the next occurrence of a birthday and the age they'll be."""
    if now is None:
        now = datetime.datetime.now()
    
    # FIX: Make date timezone-aware if now has timezone
    if now.tzinfo and date.tzinfo is None:
        date = date.replace(tzinfo=now.tzinfo)
    
    next_bd = date.replace(year=now.year)
    age = now.year - date.year

    # Compare by date, not full timestamp: next_bd is always midnight of the
    # target day (strptime never sets a time-of-day), so comparing it against
    # `now` directly made TODAY's birthday look "already passed" the instant
    # any time had elapsed past midnight, pushing it a full year ahead.
    if next_bd.date() < now.date():
        next_bd = next_bd.replace(year=now.year + 1)
        age = now.year + 1 - date.year

    return next_bd, age

async def get_bdays(guild_id) -> list[Birthday]:
    return await Birthday.find(Birthday.guild_id == str(guild_id)).to_list()

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
        """Check for birthdays every minute (respecting timezones via v.datetimes)."""
        for guild in self.client.guilds:
            config = (await Guild.get(str(guild.id))).dashboard.birthdays

            if not config.status:
                continue

            # FIX: v.datetimes returns a timezone, use it with datetime.now()
            tz = v.datetimes(guild.id)
            now = datetime.datetime.now(tz)

            channel_id = config.channel_id
            if not channel_id:
                continue

            channel = guild.get_channel(int(channel_id))
            if not channel:
                continue

            # Only wish birthdays during the configured hour (default: midnight).
            # birthday.wished still guards against resending for the rest of that hour.
            try:
                wishing_hour = int(config.message_hour or 0)
            except (TypeError, ValueError):
                wishing_hour = 0
            if now.hour != wishing_hour:
                continue

            birthdays = await get_bdays(guild.id)

            for birthday in birthdays:
                if birthday.wished or not birthday.date:
                    continue

                date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
                
                # Check if it's their birthday in the guild's timezone
                if now.day != date.day or now.month != date.month:
                    continue

                member = guild.get_member(int(birthday.user_id))
                if not member:
                    continue

                # Calculate actual age
                age = now.year - date.year

                # Assign birthday role
                birthday_role_id = config.birthday_role
                if birthday_role_id:
                    role = guild.get_role(int(birthday_role_id))
                    if role:
                        # ✅ Check bot permissions first
                        if guild.me.guild_permissions.manage_roles:
                            if role.position < guild.me.top_role.position:
                                try:
                                    await member.add_roles(role, reason="Birthday!")
                                except discord.Forbidden:
                                    print(f"❌ Could not add birthday role to {member} in {guild.name}")
                                except Exception as e:
                                    print(f"❌ Error adding birthday role: {e}")
                            else:
                                print(f"⚠️ Birthday role {role.name} is above bot's highest role")
                        else:
                            print(f"⚠️ Bot missing manage_roles permission in {guild.name}")

                # Send birthday message (dashboard-configurable, admin-authored - not translated, matches welcome.py/leveling.py precedent)
                message_template = config.message or "🎉 Happy Birthday {user}! You are now {age} years old! 🎂"
                await channel.send(v.render_placeholders(
                    message_template,
                    user=member,
                    age=age,
                    server=guild
                ))

                # Send DM if enabled
                # if config.get("dm", False):
                #     try:
                #         await member.send(f"🎉 Happy Birthday {member.display_name}! 🎂\n\nHope you have an amazing day! 🎈")
                #     except discord.HTTPException:
                #         pass

                birthday.wished = True
                # Store a real datetime, not a string - Birthday.wished_at is typed
                # Optional[datetime]. Assigning a str here bypasses validation on
                # write, but the next fetch re-validates and hands role_reset() an
                # actual datetime, not the string it expects (see role_reset below).
                birthday.wished_at = now
                birthday.age = age
                await birthday.save()

    @tasks.loop(hours=1)
    async def role_reset(self):
        """Removes birthday role at end of birthday (midnight in guild timezone)."""
        for guild in self.client.guilds:
            config = (await Guild.get(str(guild.id))).dashboard.birthdays
            birthday_role_id = config.birthday_role

            if not birthday_role_id:
                continue

            # FIX: v.datetimes returns a timezone, use it with datetime.now()
            tz = v.datetimes(guild.id)
            now = datetime.datetime.now(tz)

            # Only run at midnight (or close to it)
            if now.hour != 0 or now.minute > 5:
                continue

            birthdays = await get_bdays(guild.id)
            role = guild.get_role(int(birthday_role_id))
            
            if not role:
                continue

            for birthday in birthdays:
                if not birthday.wished or not birthday.wished_at:
                    continue

                # wished_at is normally already a real datetime (Beanie/Pydantic
                # validates it on load from Mongo), but tolerate a leftover string
                # from data written before this field stopped being isoformat()'d.
                wished_at = birthday.wished_at
                if isinstance(wished_at, str):
                    wished_at = datetime.datetime.fromisoformat(wished_at)

                # If it's past midnight after their birthday, remove role
                if wished_at.date() < now.date():
                    member = guild.get_member(int(birthday.user_id))
                    if member and role in member.roles:
                        try:
                            await member.remove_roles(role, reason="Birthday over")
                        except discord.HTTPException:
                            pass

                    birthday.wished = False
                    birthday.wished_at = None
                    await birthday.save()

    @birthday_check.before_loop
    async def before_birthday_check(self):
        await self.client.wait_until_ready()

    @role_reset.before_loop
    async def before_role_reset(self):
        await self.client.wait_until_ready()

class BirthdayCommands(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.slash_command(
        name=v.t.msg(None, "birthdays.cmd.list.name"),
        description=v.t.msg(None, "birthdays.cmd.list.description"),
        name_localizations=v.t.localizations("birthdays.cmd.list.name"),
        description_localizations=v.t.localizations("birthdays.cmd.list.description"),
    )
    async def birthdays(self, ctx: discord.ApplicationContext):
        birthdays = await get_bdays(ctx.guild.id)
        tz = v.datetimes(ctx.guild.id)
        now = datetime.datetime.now(tz)
        entries = []

        for birthday in birthdays:
            if not birthday.date:
                continue

            birthday_date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
            if birthday_date.month != now.month:
                continue

            user = ctx.guild.get_member(int(birthday.user_id))
            username = user.mention if user else f"<@{birthday.user_id}>"
            age = birthday.age or (now.year - birthday_date.year)
            entries.append(f"**{birthday_date.strftime('%d %B')}** — {username} ({ordinal(age)})")

        if not entries:
            return await ctx.respond(v.t.msg(ctx.guild, "birthdays.no_birthdays_month"), ephemeral=True)

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=v.t.msg(ctx.guild, "birthdays.month_title", month=now.strftime('%B')),
            description="\n".join(entries)
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(
        name=v.t.msg(None, "birthdays.cmd.next.name"),
        description=v.t.msg(None, "birthdays.cmd.next.description"),
        name_localizations=v.t.localizations("birthdays.cmd.next.name"),
        description_localizations=v.t.localizations("birthdays.cmd.next.description"),
    )
    async def next_birthdays(self, ctx: discord.ApplicationContext):
        birthdays = await get_bdays(ctx.guild.id)

        if not birthdays:
            return await ctx.respond(v.t.msg(ctx.guild, "birthdays.none_known"), ephemeral=True)

        tz = v.datetimes(ctx.guild.id)
        now = datetime.datetime.now(tz)
        entries = []

        for birthday in birthdays:
            if not birthday.date:
                continue

            birthday_date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
            next_bd, age = next_birthday(birthday_date, now)
            user = ctx.guild.get_member(int(birthday.user_id))
            username = user.mention if user else f"<@{birthday.user_id}>"
            entries.append((next_bd, f"**{next_bd.strftime('%d %B')}** — {username} ({ordinal(age)})"))

        entries.sort(key=lambda x: x[0])
        top10 = entries[:10]

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title=v.t.msg(ctx.guild, "birthdays.upcoming_title"),
            description="\n".join(entry[1] for entry in top10)
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(
        name=v.t.msg(None, "birthdays.cmd.view.name"),
        description=v.t.msg(None, "birthdays.cmd.view.description"),
        name_localizations=v.t.localizations("birthdays.cmd.view.name"),
        description_localizations=v.t.localizations("birthdays.cmd.view.description"),
    )
    @discord.option(
        "member",
        description=v.t.msg(None, "birthdays.cmd.view.options.member.description"),
        name_localizations=v.t.localizations("birthdays.cmd.view.options.member.name"),
        description_localizations=v.t.localizations("birthdays.cmd.view.options.member.description"),
        required=False,
    )
    async def view_birthday(self, ctx: discord.ApplicationContext, member: discord.Member = None):
        member = member or ctx.author
        birthday = await Birthday.get(f"{ctx.guild.id}_{member.id}")

        if birthday is None or not birthday.date:
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=v.t.msg(ctx.guild, "birthdays.no_birthday_set", member=member.mention)
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        tz = v.datetimes(ctx.guild.id)
        now = datetime.datetime.now(tz)
        date = datetime.datetime.strptime(birthday.date, "%Y-%m-%d")
        next_bd, age = next_birthday(date, now)
        days_away = (next_bd - now.replace(hour=0, minute=0, second=0, microsecond=0)).days

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=v.t.msg(
                ctx.guild, "birthdays.info",
                member=member.mention, age=ordinal(age), days=days_away, date=date.strftime('%d %B %Y')
            )
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(
        name=v.t.msg(None, "birthdays.cmd.set.name"),
        description=v.t.msg(None, "birthdays.cmd.set.description"),
        name_localizations=v.t.localizations("birthdays.cmd.set.name"),
        description_localizations=v.t.localizations("birthdays.cmd.set.description"),
    )
    @discord.option(
        "date",
        description=v.t.msg(None, "birthdays.cmd.set.options.date.description"),
        name_localizations=v.t.localizations("birthdays.cmd.set.options.date.name"),
        description_localizations=v.t.localizations("birthdays.cmd.set.options.date.description"),
        required=True,
    )
    @discord.option(
        "member",
        description=v.t.msg(None, "birthdays.cmd.set.options.member.description"),
        name_localizations=v.t.localizations("birthdays.cmd.set.options.member.name"),
        description_localizations=v.t.localizations("birthdays.cmd.set.options.member.description"),
        required=False,
    )
    async def set_birthday(self, ctx: discord.ApplicationContext, date: str, member: discord.Member = None):
        member = member or ctx.author

        existing = await Birthday.get(f"{ctx.guild.id}_{member.id}")
        if existing is not None:
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=v.t.msg(ctx.guild, "birthdays.already_set", member=member.mention)
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        try:
            parsed = datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            embed = discord.Embed(
                color=v.error,
                description=v.t.msg(ctx.guild, "birthdays.invalid_format")
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        # Prevent setting birthday in the future (can't be born tomorrow)
        tz = v.datetimes(ctx.guild.id)
        now = datetime.datetime.now(tz)
        # parsed is naive (strptime never attaches tzinfo) - localize it to the
        # guild's timezone before comparing, same as next_birthday() has to.
        if parsed.replace(tzinfo=tz) > now:
            return await ctx.respond(v.t.msg(ctx.guild, "birthdays.future_date"), ephemeral=True)

        next_bd, age = next_birthday(parsed, now)
        days_away = (next_bd - now.replace(hour=0, minute=0, second=0, microsecond=0)).days

        await Birthday(
            id=f"{ctx.guild.id}_{member.id}",
            guild_id=str(ctx.guild.id),
            user_id=str(member.id),
            date=parsed.strftime("%Y-%m-%d"),
            age=age,
            wished=False,
            wished_at=None,
        ).insert()

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=v.t.msg(
                ctx.guild, "birthdays.success",
                member=member.mention, age=ordinal(age), days=days_away, date=parsed.strftime('%d %B %Y')
            )
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(
        name=v.t.msg(None, "birthdays.cmd.remove.name"),
        description=v.t.msg(None, "birthdays.cmd.remove.description"),
        name_localizations=v.t.localizations("birthdays.cmd.remove.name"),
        description_localizations=v.t.localizations("birthdays.cmd.remove.description"),
    )
    async def remove_birthday(self, ctx: discord.ApplicationContext):
        birthday = await Birthday.get(f"{ctx.guild.id}_{ctx.author.id}")

        if birthday is None:
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=v.t.msg(ctx.guild, "birthdays.not_set")
            )
            return await ctx.respond(embed=embed, ephemeral=True)

        await birthday.delete()
        await ctx.respond(v.t.msg(ctx.guild, "birthdays.removed"), ephemeral=True)

def setup(client):
    client.add_cog(BirthdayTimers(client))
    client.add_cog(BirthdayCommands(client))