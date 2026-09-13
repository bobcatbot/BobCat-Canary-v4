import discord
from discord.ext import commands
import random
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from cogs.money._shop import open_account, update_bank, parse_and_validate_bet

# ── guess odds ───────────────────────────────────────────────
GUESS_MAX_NUMBER = 100
GUESS_HINT_AFTER = 7
# Payout multiplier tiers, keyed by max guesses used — net profit is
# bet * (multiplier - 1), so a multiplier of 1 just refunds the bet.
GUESS_PAYOUT_TIERS = [
    (3, 3),   # solved in 3 guesses or fewer: triple the bet
    (7, 2),   # solved in 7 guesses or fewer: double the bet
]
GUESS_PAYOUT_FLOOR_MULTIPLIER = 1  # anything slower just refunds the bet

class GuessGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.games = {}  # {user_id: game_data}
        self.scores = {}  # {user_id: {"wins": 0, "losses": 0}}
        self.cooldown = commands.CooldownMapping.from_cooldown(
            1, 10, commands.BucketType.user
        )  # 1 game per 10 seconds per user

    @commands.slash_command(name="guess", description="Guess the number between 1 and 100 to win your bet")
    @discord.option("amount", description="Bet amount", required=True)
    async def guess(self, ctx, amount: str):
        # Check cooldown
        bucket = self.cooldown.get_bucket(ctx.interaction)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            embed = discord.Embed(
                title="⏳ Slow Down!",
                description=f"Please wait `{retry_after:.1f}s` before starting another game.",
                color=discord.Color.orange()
            )
            return await ctx.send(embed=embed)

        # Check if user already has a game running
        if ctx.author.id in self.games:
            embed = discord.Embed(
                title="❌ Game Already Active!",
                description="You already have a game running. Type `cancel` to stop it.",
                color=discord.Color.red()
            )
            return await ctx.respond(embed=embed)

        await open_account(ctx.guild, ctx.author)
        ok, result = await parse_and_validate_bet(ctx.guild, ctx.author, amount)
        if not ok:
            return await ctx.respond(result, ephemeral=True)
        bet = result

        # Generate number
        target = random.randint(1, GUESS_MAX_NUMBER)
        game_data = {
            "target": target,
            "max": GUESS_MAX_NUMBER,
            "hint_after": GUESS_HINT_AFTER,
            "bet": bet,
            "guesses": 0,
            "hint_count": 0,
            "started": datetime.now(),
            "guessed_numbers": [],
            "game_over": False
        }

        self.games[ctx.author.id] = game_data

        # Create embed
        embed = discord.Embed(
            title="🎯 Guess the Number!",
            description=f"Guess a number between `1` and `{GUESS_MAX_NUMBER}`.\n"
                       f"You bet **`{bet}`** coins. Type `cancel` to end the game and get your bet back.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Game started by {ctx.author.display_name}")
        embed.timestamp = datetime.now()

        await ctx.respond(embed=embed)

        # Start listening for guesses
        try:
            await self._game_loop(ctx, ctx.author)
        except asyncio.TimeoutError:
            # Game timed out - forfeit the bet for not finishing
            if ctx.author.id in self.games:
                del self.games[ctx.author.id]
            await update_bank(ctx.guild, ctx.author, "bank", -bet)
            embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"You took too long to guess. Game ended and you lost your **`{bet}`** coin bet.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed)

    async def _game_loop(self, ctx, player):
        """Handle the game loop with timeout."""
        start_time = datetime.now()

        while True:
            # Check timeout (60 seconds)
            if (datetime.now() - start_time).seconds > 60:
                raise asyncio.TimeoutError()

            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=60,
                    check=lambda m: (
                        m.author == player and
                        m.channel == ctx.channel and
                        (m.content.isdigit() or m.content.lower() == "cancel")
                    )
                )
            except asyncio.TimeoutError:
                raise

            game = self.games.get(player.id)
            if not game or game["game_over"]:
                return

            # Handle cancellation - bet is refunded since nothing was played
            if msg.content.lower() == "cancel":
                del self.games[player.id]
                embed = discord.Embed(
                    title="🚫 Game Cancelled",
                    description=f"Your **`{game['bet']}`** coin bet was refunded. Better luck next time!",
                    color=discord.Color.orange()
                )
                return await ctx.respond(embed=embed)

            # Process guess
            guess = int(msg.content)
            game["guesses"] += 1
            game["guessed_numbers"].append(guess)

            # Check if it's the right number
            if guess == game["target"]:
                # Winner! Payout scales down the more guesses it took.
                multiplier = GUESS_PAYOUT_FLOOR_MULTIPLIER
                for max_guesses, tier_multiplier in GUESS_PAYOUT_TIERS:
                    if game["guesses"] <= max_guesses:
                        multiplier = tier_multiplier
                        break

                change = game["bet"] * (multiplier - 1)
                if change != 0:
                    await update_bank(ctx.guild, player, "bank", change)

                embed = discord.Embed(
                    title="🎉 You Got It!",
                    description=f"The number was **{game['target']}**!\n"
                               f"You guessed it in **{game['guesses']}** tries and "
                               + (f"won **`{change}`** coins!" if change > 0 else "got your bet back."),
                    color=discord.Color.gold()
                )
                embed.add_field(
                    name="📊 Score",
                    value=f"Wins: {self.scores.get(player.id, {}).get('wins', 0)}",
                    inline=True
                )

                # Update score
                if player.id not in self.scores:
                    self.scores[player.id] = {"wins": 0, "losses": 0}
                self.scores[player.id]["wins"] += 1

                del self.games[player.id]
                return await ctx.respond(embed=embed)

            # Provide feedback
            is_higher = guess > game["target"]
            embed = discord.Embed(
                title="📈 Hint",
                description=f"Your guess `{guess}` is **{'too high' if is_higher else 'too low'}**!",
                color=discord.Color.blue()
            )

            # Provide hint after certain number of guesses
            if game["guesses"] >= game["hint_after"] and game["hint_count"] < 3:
                hint = self._generate_hint(game["target"], game["max"])
                embed.add_field(
                    name="💡 Hint",
                    value=f"Number is {hint}",
                    inline=False
                )
                game["hint_count"] += 1

            # Show previous guesses (last 5)
            if game["guessed_numbers"]:
                last_guesses = game["guessed_numbers"][-5:]
                embed.add_field(
                    name="📋 Recent Guesses",
                    value=", ".join(str(n) for n in last_guesses),
                    inline=False
                )

            embed.set_footer(text=f"Attempt {game['guesses']} • Type 'cancel' to quit")
            await ctx.respond(embed=embed)

    def _generate_hint(self, target, max_num):
        """Generate a useful hint."""
        if target < max_num * 0.25:
            return "very low 🧊"
        elif target < max_num * 0.5:
            return "low ⬇️"
        elif target < max_num * 0.75:
            return "medium ↔️"
        elif target < max_num * 0.9:
            return "high ⬆️"
        else:
            return "very high 🔥"

def setup(client):
    client.add_cog(GuessGame(client))