import discord
import random
import asyncio
from modules import bot as v
from discord.ext import commands
from cogs.money._shop import open_account, update_bank, parse_and_validate_bet

# ── diceroll odds ────────────────────────────────────────────
# Doubles are a jackpot; a non-double total of 7+ is a normal win;
# anything else loses the bet.
DICEROLL_DOUBLES_MULTIPLIER = 2  # net coins won = bet * this, on doubles
DICEROLL_WIN_TOTAL = 9           # minimum non-double total to win
# Odds with these numbers (out of 36 rolls): 6 doubles (2x), 8 plain wins (1x),
# 22 losses (-1x) -> expected value ≈ -0.056 per coin bet, a mild house edge
# in line with /economy gamble's ~10% edge.

class GamesDiceroll(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.slash_command(
        description=v.t.msg(None, "diceroll.cmd.description"),
        name_localizations=v.t.localizations("diceroll.cmd.name"),
        description_localizations=v.t.localizations("diceroll.cmd.description"),
    )
    @discord.option(
        "amount",
        description=v.t.msg(None, "diceroll.cmd.options.amount.description"),
        name_localizations=v.t.localizations("diceroll.cmd.options.amount.name"),
        description_localizations=v.t.localizations("diceroll.cmd.options.amount.description"),
        required=True,
    )
    @commands.cooldown(rate=1, per=10, type=commands.BucketType.user)
    async def diceroll(self, ctx, amount: str):
        await open_account(ctx.guild, ctx.user)

        ok, result = await parse_and_validate_bet(ctx.guild, ctx.user, amount)
        if not ok:
            return await ctx.respond(result, ephemeral=True)
        bet = result

        msg = await ctx.respond(v.t.msg(ctx.guild, "diceroll.rolling", user=ctx.user.name))
        await asyncio.sleep(2)

        die1 = random.randint(1, 6)
        die2 = random.randint(1, 6)
        total = die1 + die2
        doubles = die1 == die2

        if doubles:
            change = bet * DICEROLL_DOUBLES_MULTIPLIER
        elif total >= DICEROLL_WIN_TOTAL:
            change = bet
        else:
            change = -bet

        await update_bank(ctx.guild, ctx.user, "bank", change)

        if change > 0:
            outcome = v.t.msg(ctx.guild, "diceroll.win", change=change)
            if doubles:
                outcome += v.t.msg(ctx.guild, "diceroll.doubles_suffix")
        else:
            outcome = v.t.msg(ctx.guild, "diceroll.lose", bet=bet)

        content = v.t.msg(ctx.guild, "diceroll.result", user=ctx.user.name, die1=die1, die2=die2, total=total, outcome=outcome)
        await msg.edit_original_response(content=content)

def setup(client):
    client.add_cog(GamesDiceroll(client))