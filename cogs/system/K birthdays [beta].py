import asyncio
import discord
import json
import datetime
from discord.ext import commands, tasks
import pytz
from modules import bot as v

# dash idea) 24h - 12h

def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

class Birthdays(commands.Cog):
    def __init__(self, client: commands.bot):
        self.client: commands.Bot = client
        self.birthdays.start()
        self.role_rest.start()

    async def wait_until_hour(self, guild, target_hour):
        """Waits until the next occurrence of the specified hour."""
        tz = v.datetimes(guild)
        now = datetime.datetime.now(pytz.utc).astimezone(tz)
        target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        
        if now > target_time:  # If it's past the target hour today, wait until tomorrow
            target_time += datetime.timedelta(days=1)

        wait_seconds = (target_time - now).total_seconds()
        # print(f"Waiting {wait_seconds // 3600} hours and {wait_seconds % 3600 // 60} minutes until {target_hour}:00...")
        await asyncio.sleep(wait_seconds)

    @tasks.loop(seconds=30)
    async def birthdays(self):
        for guild in self.client.guilds:
            if not v.db.get_dash(guild.id):
                continue
            
            config = v.db.get_dash(guild.id)["birthdays"]
            bdays = v.db.get_server_config(guild.id)["birthdays"]

            # await self.wait_until_hour(guild, int(config["message_hour"])) # Wait until the configured hour
            
            now = datetime.datetime.now()

            for user_id, birthday in bdays.items():
                date = datetime.datetime.strptime(birthday["date"], "%Y-%m-%d")

                # Check if today is their birthday and they haven't been wished yet
                if now.day == date.day and now.month == date.month and not birthday.get("wished", False):
                    member = guild.get_member(int(user_id))
                    if member:
                        if config.get("birthday_role"): # If a role is configured
                            role = guild.get_role(int(config["birthday_role"]))
                            await member.add_roles(role)

                        channel = guild.get_channel(int(config["channel_id"]))
                        await channel.send(config["message"].format(user=member, age=birthday["age"]))
                        
                        # Update database to mark as wished
                        v.db.update_server_config(guild.id, key=f"birthdays.{user_id}.wished", value=True)
                        v.db.update_server_config(guild.id, key=f"birthdays.{user_id}.wished_at", value=now.strftime("%Y-%m-%d %H:%M:%S"))

                        print(f"Sent birthday message for {member}")
    
    @tasks.loop(hours=24)
    async def role_rest(self):
        """Removes users from self.already_wished exactly 24 hours after their birthday message."""
        now = datetime.datetime.now()
        
        for guild in self.client.guilds:
            config = v.db.get_dash(guild.id)["birthdays"]
            bdays = v.db.get_server_config(guild.id)["birthdays"]

            for user_id, birthday in bdays.items():
                if not birthday.get("wished", False):
                    continue # Skip users who haven't been wished

                wished_at = datetime.datetime.strptime(birthday["wished_at"], "%Y-%m-%d %H:%M:%S")
                
                if (now - wished_at).total_seconds() >= 86400:
                    member = guild.get_member(int(user_id))
                    if member:
                        role = guild.get_role(int(config["birthday_role"]))
                        await member.remove_roles(role)
                    
                    v.db.update_server_config(guild.id, key=f"birthdays.{user_id}.wished", value=False)
                    v.db.update_server_config(guild.id, key=f"birthdays.{user_id}.wished_at", value=None) # Clear the timestamp

class BirthdayCommands(commands.Cog):
    def __init__(self, client: commands.bot):
        self.client = client

    @commands.slash_command(name="birthdays", description="Show all birthdays for the current month")
    async def birthdays(self, ctx: discord.ApplicationContext):
        """
        Shows all birthdays for the current month
        """
        bdays = v.db.get_server_config(ctx.guild.id)["birthdays"]

        now = datetime.datetime.now()
        upcoming_birthdays = []

        if not upcoming_birthdays:
            return await ctx.respond("I don't know **any** birthday **yet**.", ephemeral=True)
        
        for user_id, birthday_info in bdays.items():
            birthday_date = datetime.datetime.strptime(birthday_info["date"], "%Y-%m-%d")

            if birthday_date.month == now.month:  # Show only this month's birthdays
                user = ctx.guild.get_member(int(user_id))
                username = user.mention if user else f"<@{user_id}>"
                age = int(birthday_info["age"])
                
                formatted_date = birthday_date.strftime("%d %B %Y")
                upcoming_birthdays.append(f"**{formatted_date}**\n{username} ({age})\n")

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title="Upcoming Birthdays",
            description="\n".join(upcoming_birthdays)
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="next-birthdays", description="Shows the next 10 upcoming birthdays")
    async def birthdays(self, ctx: discord.ApplicationContext):
        """
        Shows the next 10 upcoming birthdays
        """
        bdays = v.db.get_server_config(ctx.guild.id)["birthdays"]

        upcoming_birthdays = []
        
        for user_id, birthday_info in bdays.items():
            birthday_date = datetime.datetime.strptime(birthday_info["date"], "%Y-%m-%d")
            age = int(birthday_info["age"])

            # Get user's mention or fallback to ID
            user = ctx.guild.get_member(int(user_id))
            username = user.mention if user else f"<@{user_id}>"

            # Format: 01 January 2025
            formatted_date = birthday_date.strftime("%d %B %Y")
            upcoming_birthdays.append((birthday_date, f"**{formatted_date}**\n{username} ({age})\n"))
        
        if not upcoming_birthdays:
            return await ctx.respond("I don't know **any** birthday(s) **yet**.", ephemeral=True)

        # Sort by date and get the next 10 birthdays
        upcoming_birthdays.sort()
        upcoming_birthdays = upcoming_birthdays[:10]  # Take only the next 10

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            title="Upcoming Birthdays",
            description="\n".join([entry[1] for entry in upcoming_birthdays])
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="birthday", description="Show yours or another member's birthday")
    @discord.option("member", description="The member to view the birthday of", required=False)
    async def view_birthday(self, ctx: discord.ApplicationContext, member: discord.Member=None):
        """
        Views yours or another member's birthday

        Parameters:
        - member: The member to view the birthday of, optional
        """
        bdays = v.db.get_server_config(ctx.guild.id)["birthdays"]

        member = ctx.author if not member else member

        if not bdays.get(str(member.id)):
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"{member.mention} has no birthday set."
            )
            return await ctx.respond(embed=embed)
        
        birthday = bdays[str(member.id)]

        datee = datetime.datetime.strptime(birthday["date"], "%Y-%m-%d")
        age = datetime.datetime.now().year - int(birthday["date"].split("-")[0]) + 1

        # Calculate the next birthday
        now = datetime.datetime.now()
        next_birthday = datee.replace(year=now.year)
        if next_birthday < now:
            next_birthday = next_birthday.replace(year=now.year + 1)

        days_away = (next_birthday - now).days + 1

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"{member.mention}'s **{ordinal(age)}** birthday is in **{days_away}** days on **{datee.strftime('%d %B %Y')}**."
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="set-birthday", description="Sets yours or another member's birthday")
    @discord.option("date", description="Birthday (YYYY-MM-DD)", required=True)
    @discord.option("member", description="The member to set the birthday of", required=False)
    async def birthday(self, ctx: discord.ApplicationContext, date: str, member: discord.Member=None):
        """
        Sets yours or another member's birthday

        Parameters:
        - date: Birthday (YYYY-MM-DD or MM/DD), required
        - member: The member to set the birthday of, optional
        """
        member = ctx.author if not member else member

        bdays = v.db.get_server_config(ctx.guild.id)["birthdays"]

        if bdays.get(str(member.id)):
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"{member.mention} already has a birthday set."
            )
            return await ctx.respond(embed=embed)

        datee = datetime.datetime.strptime(date, "%Y-%m-%d")
        age = datetime.datetime.now().year - int(date.split("-")[0]) + 1

        # Calculate the next birthday
        now = datetime.datetime.now()
        next_birthday = datee.replace(year=now.year)
        if next_birthday < now:
            next_birthday = next_birthday.replace(year=now.year + 1)

        days_away = (next_birthday - now).days + 1

        v.db.update_server_config(ctx.guild.id, key=f"birthdays.{member.id}", value={
            "date": datee.strftime("%Y-%m-%d"),
            "age": age,
            "wished": False,
            "wished_at": None
        })

        embed = discord.Embed(
            color=v.style(ctx.guild.id),
            description=f"Duly noted, I'll wish {member.mention}'s **{ordinal(age)}** birthday in **{days_away}** days on **{datee.strftime('%d %B %Y')}**."
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(name="remove-birthday", description="Removes a member's birthday")
    async def remove_birthday(self, ctx: discord.ApplicationContext):
        """
        Removes a member's birthday

        Parameters:
        - member: The member to remove the birthday of
        """
        member = ctx.author
        bdays = v.db.get_server_config(ctx.guild.id)["birthdays"]

        if not bdays.get(str(member.id)):
            embed = discord.Embed(
                color=v.style(ctx.guild.id),
                description=f"You have no birthday set. Use </set-birthday:{ctx.command.id}> to set one."
            )
            return await ctx.respond(embed=embed)
        
        bdays.pop(str(member.id))
        v.db.update_server_config(ctx.guild.id, key=f"birthdays", value=bdays)

        await ctx.respond(f"I will no longer wish **your** birthday anymore.")

def setup(client):
    client.add_cog(Birthdays(client))
    client.add_cog(BirthdayCommands(client))