import time
import discord
import random
import asyncio
from typing import Optional
from datetime import datetime
from discord.ext import commands
from modules import bot as v
from cogs.money._shop import open_account, update_bank, parse_and_validate_bet

# Only the member who ran /rps places a bet - a tie refunds nothing (no
# money ever changes hands), a win pays out the bet, a loss forfeits it.

class RPSGame(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.games = {}  # {channel_id: game_data}
        self.scores = {}  # {user_id: {"wins": 0, "losses": 0, "ties": 0}}
        
        # Custom cooldown tracking (works for slash commands)
        self.cooldowns = {}  # {user_id: timestamp}
        self.cooldown_seconds = 5
        
        self.choices = {
            "rock": {"emoji": "🪨", "beats": "scissors"},
            "paper": {"emoji": "📄", "beats": "rock"},
            "scissors": {"emoji": "✂️", "beats": "paper"}
        }
        
    def check_cooldown(self, user_id: int) -> Optional[float]:
        """Check if user is on cooldown. Returns remaining time or None."""
        if user_id in self.cooldowns:
            elapsed = time.time() - self.cooldowns[user_id]
            if elapsed < self.cooldown_seconds:
                return self.cooldown_seconds - elapsed
        return None
        
    def apply_cooldown(self, user_id: int):
        """Apply cooldown to user."""
        self.cooldowns[user_id] = time.time()
        
    class RPSView(discord.ui.View):
        """The button view for RPS."""
        def __init__(self, cog, ctx, game_data):
            super().__init__(timeout=30)
            self.cog = cog
            self.ctx = ctx
            self.game_data = game_data
            self.selected = None
            self.player_id = None
            
        # Button labels are decorator-level (fixed at class-definition time, before
        # any guild context exists) - same DEFAULT_LANG-only constraint as a slash
        # command's own name/description. Unlike slash commands, Discord has no
        # native per-user localization for component labels, so these stay
        # DEFAULT_LANG for every guild for now.
        @discord.ui.button(label=v.t.msg(None, "rps.moves.rock"), emoji="🪨", style=discord.ButtonStyle.primary)
        async def rock_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self._handle_choice(interaction, "rock")

        @discord.ui.button(label=v.t.msg(None, "rps.moves.paper"), emoji="📄", style=discord.ButtonStyle.success)
        async def paper_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self._handle_choice(interaction, "paper")

        @discord.ui.button(label=v.t.msg(None, "rps.moves.scissors"), emoji="✂️", style=discord.ButtonStyle.danger)
        async def scissors_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await self._handle_choice(interaction, "scissors")
            
        async def _handle_choice(self, interaction: discord.Interaction, choice: str):
            """Handle a player's choice."""
            # Check if game is still active
            if self.ctx.channel.id not in self.cog.games:
                await interaction.response.send_message(
                    v.t.msg(self.ctx.guild, "rps.errors.ended"),
                    ephemeral=True
                )
                return

            # Check if it's the right player's turn
            if self.game_data["mode"] == "multi":
                expected_player = self.game_data["players"][self.game_data["current_player"]]
                if interaction.user.id != expected_player:
                    await interaction.response.send_message(
                        v.t.msg(self.ctx.guild, "rps.errors.not_your_turn"),
                        ephemeral=True
                    )
                    return
            else:
                # AI mode - only the player can click
                if interaction.user.id != self.game_data["players"][0]:
                    await interaction.response.send_message(
                        v.t.msg(self.ctx.guild, "rps.errors.ai_only_player"),
                        ephemeral=True
                    )
                    return
                    
            # Record the choice
            self.selected = choice
            self.player_id = interaction.user.id
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)
            
            # Store the move
            if self.game_data["mode"] == "multi":
                self.game_data["moves"][interaction.user.id] = choice
                self.game_data["current_player"] = 1 - self.game_data["current_player"]
                
                # Check if both players have chosen
                if len(self.game_data["moves"]) == 2:
                    await self.cog._determine_winner(self.ctx, self.game_data)
                else:
                    # Update embed to show next player's turn
                    next_player_id = self.game_data["players"][self.game_data["current_player"]]
                    next_player = self.ctx.guild.get_member(next_player_id) or await self.cog.client.fetch_user(next_player_id)
                    
                    embed = discord.Embed(
                        title=v.t.msg(self.ctx.guild, "rps.title"),
                        description=v.t.msg(self.ctx.guild, "rps.next_turn", player=next_player.display_name),
                        color=discord.Color.blue()
                    )
                    embed.timestamp = datetime.now()
                    
                    # Get the original message
                    msg = await self.ctx.channel.fetch_message(self.game_data.get("message_id"))
                    if msg:
                        await msg.edit(embed=embed)
            else:
                # AI mode
                self.game_data["moves"][interaction.user.id] = choice
                # AI moves after a short delay
                await asyncio.sleep(1)
                await self.cog._ai_move(self.ctx, self.game_data)
                
    @commands.slash_command(
        name="rps",
        description=v.t.msg(None, "rps.cmd.description"),
        name_localizations=v.t.localizations("rps.cmd.name"),
        description_localizations=v.t.localizations("rps.cmd.description"),
    )
    @discord.option(
        "amount",
        description=v.t.msg(None, "rps.cmd.options.amount.description"),
        name_localizations=v.t.localizations("rps.cmd.options.amount.name"),
        description_localizations=v.t.localizations("rps.cmd.options.amount.description"),
        required=True,
    )
    @discord.option(
        "opponent",
        description=v.t.msg(None, "rps.cmd.options.opponent.description"),
        name_localizations=v.t.localizations("rps.cmd.options.opponent.name"),
        description_localizations=v.t.localizations("rps.cmd.options.opponent.description"),
        required=False,
    )
    async def rps(self, ctx, amount: str, opponent: Optional[discord.Member] = None):
        """Play Rock Paper Scissors with buttons!"""

        # Check cooldown (custom implementation)
        cooldown_remaining = self.check_cooldown(ctx.author.id)
        if cooldown_remaining:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "rps.cooldown.title"),
                description=v.t.msg(ctx.guild, "rps.cooldown.description", seconds=f"{cooldown_remaining:.1f}"),
                color=discord.Color.orange()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Check if game already active in this channel
        if ctx.channel.id in self.games:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "rps.already_active.title"),
                description=v.t.msg(ctx.guild, "rps.already_active.description"),
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Validate opponent
        is_multiplayer = opponent is not None
        if is_multiplayer:
            if opponent == ctx.author:
                embed = discord.Embed(
                    title=v.t.msg(ctx.guild, "rps.cant_play_self.title"),
                    description=v.t.msg(ctx.guild, "rps.cant_play_self.description"),
                    color=discord.Color.red()
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            if opponent.bot:
                embed = discord.Embed(
                    title=v.t.msg(ctx.guild, "rps.cant_play_bot.title"),
                    description=v.t.msg(ctx.guild, "rps.cant_play_bot.description"),
                    color=discord.Color.red()
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return

        # Validate bet
        await open_account(ctx.guild, ctx.author)
        ok, result = await parse_and_validate_bet(ctx.guild, ctx.author, amount)
        if not ok:
            await ctx.respond(result, ephemeral=True)
            return
        bet = result

        # Apply cooldown
        self.apply_cooldown(ctx.author.id)

        # Create game data
        game_data = {
            "mode": "multi" if is_multiplayer else "ai",
            "players": [ctx.author.id],
            "bet": bet,
            "moves": {},
            "started": datetime.now(),
            "active": True,
            "winner": None,
            "current_player": 0,
            "completed": False,
            "message_id": None
        }

        if is_multiplayer:
            game_data["players"].append(opponent.id)

        self.games[ctx.channel.id] = game_data

        # Create embed
        if is_multiplayer:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "rps.title"),
                description=v.t.msg(
                    ctx.guild, "rps.challenge.description",
                    challenger=ctx.author.display_name, opponent=opponent.display_name, bet=bet,
                ),
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "rps.vs_ai.title"),
                description=v.t.msg(ctx.guild, "rps.vs_ai.description", player=ctx.author.display_name, bet=bet),
                color=discord.Color.blue()
            )
            
        embed.timestamp = datetime.now()
        
        # Create and send view
        view = self.RPSView(self, ctx, game_data)
        
        # Send the message with the view
        await ctx.respond(embed=embed, view=view)
        
        # Get the message for later editing
        interaction = await ctx.interaction.original_response()
        game_data["message_id"] = interaction.id
        
        # Wait for view to timeout or complete
        await view.wait()
        
        # Check if game timed out
        if ctx.channel.id in self.games and not game_data.get("completed"):
            # Timeout - clean up
            del self.games[ctx.channel.id]
            embed = discord.Embed(
                title=v.t.msg(ctx.guild, "rps.timed_out.title"),
                description=v.t.msg(ctx.guild, "rps.timed_out.description"),
                color=discord.Color.orange()
            )
            await interaction.edit(embed=embed, view=None)
            
    async def _ai_move(self, ctx, game_data):
        """Handle AI move in button-based RPS."""
        if ctx.channel.id not in self.games:
            return
            
        # AI chooses randomly with slight bias
        # 40% chance to counter player's previous move (if available)
        player_choice = None
        for pid, move in game_data["moves"].items():
            if pid != "ai" and isinstance(pid, int):
                player_choice = move
                break
                
        if player_choice and random.random() < 0.4:
            # Try to counter
            counter_moves = {
                "rock": "paper",
                "paper": "scissors",
                "scissors": "rock"
            }
            ai_choice = counter_moves[player_choice]
        else:
            ai_choice = random.choice(list(self.choices.keys()))
            
        game_data["moves"]["ai"] = ai_choice
        
        # Determine winner
        await self._determine_winner(ctx, game_data)
        
    async def _determine_winner(self, ctx, game_data):
        """Determine and announce the winner."""
        moves = game_data["moves"]
        
        # Create result embed
        result_embed = discord.Embed(
            title="🎯 Results!",
            color=discord.Color.gold()
        )
        
        # Get the message to edit
        try:
            msg = await ctx.channel.fetch_message(game_data.get("message_id"))
        except discord.HTTPException:
            msg = None
            
        bet = game_data["bet"]

        def move_name(move_key: str) -> str:
            return v.t.msg(ctx.guild, f"rps.moves.{move_key}")

        if game_data["mode"] == "ai":
            # AI mode
            player_id = game_data["players"][0]
            player_move = moves.get(player_id)
            ai_move = moves.get("ai")

            if not player_move or not ai_move:
                return

            player = ctx.guild.get_member(player_id) or await self.client.fetch_user(player_id)

            # Show moves
            result_embed.add_field(
                name=f"{player.display_name}",
                value=f"{self.choices[player_move]['emoji']} {move_name(player_move)}",
                inline=True
            )
            result_embed.add_field(
                name=v.t.msg(ctx.guild, "rps.ai_field"),
                value=f"{self.choices[ai_move]['emoji']} {move_name(ai_move)}",
                inline=True
            )

            # Determine winner
            if player_move == ai_move:
                result_embed.title = v.t.msg(ctx.guild, "rps.tie.title")
                result_embed.color = discord.Color.blue()
                result_embed.description = v.t.msg(ctx.guild, "rps.tie.description", move=move_name(player_move))
                if player_id not in self.scores:
                    self.scores[player_id] = {"wins": 0, "losses": 0, "ties": 0}
                self.scores[player_id]["ties"] += 1

            elif self.choices[player_move]["beats"] == ai_move:
                await update_bank(ctx.guild, player, "bank", bet)

                result_embed.title = v.t.msg(ctx.guild, "rps.ai_win.title")
                result_embed.color = discord.Color.green()
                result_embed.description = v.t.msg(
                    ctx.guild, "rps.ai_win.description",
                    winner_move=move_name(player_move), loser_move=move_name(ai_move), bet=bet,
                )
                if player_id not in self.scores:
                    self.scores[player_id] = {"wins": 0, "losses": 0, "ties": 0}
                self.scores[player_id]["wins"] += 1

            else:
                await update_bank(ctx.guild, player, "bank", -bet)

                result_embed.title = v.t.msg(ctx.guild, "rps.ai_lose.title")
                result_embed.color = discord.Color.red()
                result_embed.description = v.t.msg(
                    ctx.guild, "rps.ai_lose.description",
                    winner_move=move_name(ai_move), loser_move=move_name(player_move), bet=bet,
                )
                if player_id not in self.scores:
                    self.scores[player_id] = {"wins": 0, "losses": 0, "ties": 0}
                self.scores[player_id]["losses"] += 1

        else:
            # Multiplayer mode
            player1_id = game_data["players"][0]
            player2_id = game_data["players"][1]
            move1 = moves.get(player1_id)
            move2 = moves.get(player2_id)

            if not move1 or not move2:
                return

            p1 = ctx.guild.get_member(player1_id) or await self.client.fetch_user(player1_id)
            p2 = ctx.guild.get_member(player2_id) or await self.client.fetch_user(player2_id)

            # Show moves
            result_embed.add_field(
                name=p1.display_name,
                value=f"{self.choices[move1]['emoji']} {move_name(move1)}",
                inline=True
            )
            result_embed.add_field(
                name=p2.display_name,
                value=f"{self.choices[move2]['emoji']} {move_name(move2)}",
                inline=True
            )

            # Determine winner
            if move1 == move2:
                result_embed.title = v.t.msg(ctx.guild, "rps.tie.title")
                result_embed.color = discord.Color.blue()
                result_embed.description = v.t.msg(ctx.guild, "rps.tie.description", move=move_name(move1))
                for pid in [player1_id, player2_id]:
                    if pid not in self.scores:
                        self.scores[pid] = {"wins": 0, "losses": 0, "ties": 0}
                    self.scores[pid]["ties"] += 1

            elif self.choices[move1]["beats"] == move2:
                # p1 is always the member who ran /rps and placed the bet
                await update_bank(ctx.guild, p1, "bank", bet)

                result_embed.title = v.t.msg(ctx.guild, "rps.multi_win.title", winner=p1.display_name)
                result_embed.color = discord.Color.green()
                result_embed.description = v.t.msg(
                    ctx.guild, "rps.multi_win.description",
                    winner_move=move_name(move1), loser_move=move_name(move2), bettor=p1.display_name, bet=bet,
                )
                for pid in [player1_id, player2_id]:
                    if pid not in self.scores:
                        self.scores[pid] = {"wins": 0, "losses": 0, "ties": 0}
                self.scores[player1_id]["wins"] += 1
                self.scores[player2_id]["losses"] += 1

            else:
                await update_bank(ctx.guild, p1, "bank", -bet)

                result_embed.title = v.t.msg(ctx.guild, "rps.multi_lose.title", winner=p2.display_name)
                result_embed.color = discord.Color.green()
                result_embed.description = v.t.msg(
                    ctx.guild, "rps.multi_lose.description",
                    winner_move=move_name(move2), loser_move=move_name(move1), bettor=p1.display_name, bet=bet,
                )
                for pid in [player1_id, player2_id]:
                    if pid not in self.scores:
                        self.scores[pid] = {"wins": 0, "losses": 0, "ties": 0}
                self.scores[player1_id]["losses"] += 1
                self.scores[player2_id]["wins"] += 1
                
        # Mark as completed and clean up
        game_data["completed"] = True
        if ctx.channel.id in self.games:
            del self.games[ctx.channel.id]
            
        # Edit the original message
        if msg:
            await msg.edit(embed=result_embed, view=None)
        else:
            await ctx.send(embed=result_embed)

def setup(client):
    client.add_cog(RPSGame(client))