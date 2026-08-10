import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
import math
from typing import Optional
from datetime import datetime
import time

class TicTacToeGame(commands.Cog):
    """Tic Tac Toe with BUTTONS!"""
    
    def __init__(self, client):
        self.client = client
        self.games = {}  # {channel_id: game_data}
        self.scores = {}  # {user_id: {"wins": 0, "losses": 0, "ties": 0}}
        
        # Custom cooldown
        self.cooldowns = {}  # {user_id: timestamp}
        self.cooldown_seconds = 5
        
        self.EMPTY = "⬜"
        self.PLAYER = "❌"
        self.AI = "⭕"
        
    def check_cooldown(self, user_id: int) -> Optional[float]:
        """Check if user is on cooldown."""
        if user_id in self.cooldowns:
            elapsed = time.time() - self.cooldowns[user_id]
            if elapsed < self.cooldown_seconds:
                return self.cooldown_seconds - elapsed
        return None
        
    def apply_cooldown(self, user_id: int):
        """Apply cooldown to user."""
        self.cooldowns[user_id] = time.time()
        
    class TTTView(View):
        """The button view for Tic Tac Toe."""
        def __init__(self, cog, ctx, game_data):
            super().__init__(timeout=120)
            self.cog = cog
            self.ctx = ctx
            self.game_data = game_data
            self.message = None
            
            # Create 3x3 grid of buttons
            for i in range(9):
                button = Button(
                    label=self.cog.EMPTY,
                    style=discord.ButtonStyle.secondary,
                    row=i // 3,
                    custom_id=f"ttt_{i}"
                )
                # Store position in the button object
                button.position = i
                button.callback = self.button_callback
                self.add_item(button)
                
        async def button_callback(self, interaction: discord.Interaction):
            """Handle button press - gets the button from the interaction."""
            # Find which button was pressed by matching custom_id
            custom_id = interaction.data.get("custom_id")
            button = None
            for child in self.children:
                if child.custom_id == custom_id:
                    button = child
                    break
                    
            if button is None:
                await interaction.response.send_message("❌ Button not found!", ephemeral=True)
                return
                
            await self._handle_move(interaction, button, button.position)
            
        async def _handle_move(self, interaction: discord.Interaction, button: Button, position: int):
            """Handle a player's move."""
            # Check if game is still active
            if self.ctx.channel.id not in self.cog.games:
                await interaction.response.send_message(
                    "❌ This game has already ended!", 
                    ephemeral=True
                )
                return
                
            # Check if it's the right player's turn
            if self.game_data["mode"] == "multi":
                expected_player = self.game_data["players"][self.game_data["current_player"]]
                if interaction.user.id != expected_player:
                    await interaction.response.send_message(
                        "❌ It's not your turn!", 
                        ephemeral=True
                    )
                    return
            else:
                # AI mode - only the player can click
                if interaction.user.id != self.game_data["players"][0]:
                    await interaction.response.send_message(
                        "❌ Only the player can play against AI!", 
                        ephemeral=True
                    )
                    return
                    
            # Check if position is already taken
            if self.game_data["board"][position] != self.cog.EMPTY:
                await interaction.response.send_message(
                    "❌ That position is already taken!", 
                    ephemeral=True
                )
                return
                
            # Make the move
            symbol = self.game_data["player_symbols"][interaction.user.id]
            self.game_data["board"][position] = symbol
            self.game_data["moves"] += 1
            
            # Update the button
            button.label = symbol
            button.style = discord.ButtonStyle.success if symbol == self.cog.PLAYER else discord.ButtonStyle.danger
            button.disabled = True
            
            # Check win
            if self.cog._check_winner(self.game_data["board"], symbol):
                self.game_data["winner"] = interaction.user.id
                await interaction.response.edit_message(view=self)
                await self.cog._end_game(self.ctx, self.game_data, self)
                return
                
            # Check tie
            if self.game_data["moves"] >= 9:
                self.game_data["winner"] = "tie"
                await interaction.response.edit_message(view=self)
                await self.cog._end_game(self.ctx, self.game_data, self)
                return
                
            # Switch player
            if self.game_data["mode"] == "multi":
                self.game_data["current_player"] = 1 - self.game_data["current_player"]
                
                # Get the next player
                next_player_id = self.game_data["players"][self.game_data["current_player"]]
                next_player = self.ctx.guild.get_member(next_player_id) or await self.cog.client.fetch_user(next_player_id)
                
                # Create updated embed
                embed = discord.Embed(
                    title="🎯 Tic Tac Toe",
                    description=f"**{next_player.display_name}**, it's your turn!",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"Game started at {self.game_data['started'].strftime('%H:%M')}")
                
                # Update both embed and view in one response
                await interaction.response.edit_message(embed=embed, view=self)
                
            else:
                # AI mode
                self.game_data["current"] = ["ai"]
                embed = discord.Embed(
                    title="🎯 Tic Tac Toe",
                    description="🤖 AI is thinking...",
                    color=discord.Color.blue()
                )
                embed.set_footer(text=f"Game started at {self.game_data['started'].strftime('%H:%M')}")
                
                # Update the message
                await interaction.response.edit_message(embed=embed, view=self)
                
                # AI moves after a short delay
                await asyncio.sleep(1)
                await self.cog._ai_move(self.ctx, self.game_data, self)
                
    @commands.slash_command(name="ttt", description="Play Tic Tac Toe against AI or another user.")
    @discord.option("opponent", description="Challenge another user", required=False)
    async def ttt(self, ctx, opponent: Optional[discord.Member] = None):
        """Play Tic Tac Toe with buttons!"""
        
        # Check cooldown
        cooldown_remaining = self.check_cooldown(ctx.author.id)
        if cooldown_remaining:
            embed = discord.Embed(
                title="⏳ Slow Down!",
                description=f"Please wait `{cooldown_remaining:.1f}s` before starting another game.",
                color=discord.Color.orange()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
            
        # Check if game already active in this channel
        if ctx.channel.id in self.games:
            embed = discord.Embed(
                title="❌ Game Already Active!",
                description="There's already a game in this channel.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
            
        # Determine game mode
        is_multiplayer = opponent is not None
        if is_multiplayer and opponent == ctx.author:
            embed = discord.Embed(
                title="❌ Can't Play Yourself!",
                description="Challenge someone else to play.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
            
        if is_multiplayer and opponent.bot:
            embed = discord.Embed(
                title="❌ Can't Play Bots!",
                description="Challenge a real user instead.",
                color=discord.Color.red()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
            
        # Apply cooldown
        self.apply_cooldown(ctx.author.id)
            
        # Initialize game
        game_data = {
            "board": [self.EMPTY] * 9,
            "mode": "multi" if is_multiplayer else "ai",
            "players": [ctx.author.id],
            "current_player": 0,
            "player_symbols": {ctx.author.id: self.PLAYER},
            "moves": 0,
            "active": True,
            "winner": None,
            "started": datetime.now(),
            "message_id": None
        }
        
        if is_multiplayer:
            game_data["players"].append(opponent.id)
            game_data["player_symbols"][opponent.id] = self.AI
        else:
            game_data["ai_symbol"] = self.AI
            
        self.games[ctx.channel.id] = game_data
        
        # Create embed
        if is_multiplayer:
            embed = discord.Embed(
                title="🎯 Tic Tac Toe",
                description=f"**{ctx.author.display_name}** challenged **{opponent.display_name}**!\n\n"
                           f"{ctx.author.display_name}, it's your turn!",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="🎯 Tic Tac Toe vs AI",
                description=f"**{ctx.author.display_name}**, it's your turn!",
                color=discord.Color.blue()
            )
        embed.set_footer(text=f"Game started at {datetime.now().strftime('%H:%M')}")
        
        # Create view
        view = self.TTTView(self, ctx, game_data)
        
        # Send message
        await ctx.respond(embed=embed, view=view)
        interaction = await ctx.interaction.original_response()
        view.message = interaction
        game_data["message_id"] = interaction.id
        
        # Wait for view to timeout
        await view.wait()
        
        # Check if game timed out
        if ctx.channel.id in self.games and not game_data.get("completed"):
            # Timeout - clean up
            del self.games[ctx.channel.id]
            embed = discord.Embed(
                title="⏰ Game Timed Out!",
                description="No one made a move in time.",
                color=discord.Color.orange()
            )
            await interaction.edit(embed=embed, view=None)
            
    async def _ai_move(self, ctx, game_data, view):
        """Make AI move using minimax algorithm."""
        if ctx.channel.id not in self.games:
            return
            
        # Find best move
        best_score = -math.inf
        best_move = None
        
        for i in range(9):
            if game_data["board"][i] == self.EMPTY:
                game_data["board"][i] = self.AI
                score = self._minimax(game_data["board"], 0, False)
                game_data["board"][i] = self.EMPTY
                
                if score > best_score:
                    best_score = score
                    best_move = i
                    
        if best_move is not None:
            # Make AI move
            game_data["board"][best_move] = self.AI
            game_data["moves"] += 1
            
            # Update the button
            for child in view.children:
                if child.custom_id == f"ttt_{best_move}":
                    child.label = self.AI
                    child.style = discord.ButtonStyle.danger
                    child.disabled = True
                    break
                    
            # Check win
            if self._check_winner(game_data["board"], self.AI):
                game_data["winner"] = "ai"
                await view.message.edit(view=view)
                await self._end_game(ctx, game_data, view)
                return
                
            # Check tie
            if game_data["moves"] >= 9:
                game_data["winner"] = "tie"
                await view.message.edit(view=view)
                await self._end_game(ctx, game_data, view)
                return
                
            # Switch to player's turn
            game_data["current"] = [game_data["players"][0]]
            player = ctx.guild.get_member(game_data["players"][0]) or await self.client.fetch_user(game_data["players"][0])
            
            embed = discord.Embed(
                title="🎯 Tic Tac Toe",
                description=f"**{player.display_name}**, it's your turn!",
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Game started at {game_data['started'].strftime('%H:%M')}")
            
            # Update both embed and view
            await view.message.edit(embed=embed, view=view)
            
    def _minimax(self, board, depth, is_maximizing):
        """Minimax algorithm."""
        if self._check_winner(board, self.AI):
            return 10 - depth
        if self._check_winner(board, self.PLAYER):
            return depth - 10
        if all(cell != self.EMPTY for cell in board):
            return 0
            
        if is_maximizing:
            best_score = -math.inf
            for i in range(9):
                if board[i] == self.EMPTY:
                    board[i] = self.AI
                    score = self._minimax(board, depth + 1, False)
                    board[i] = self.EMPTY
                    best_score = max(score, best_score)
            return best_score
        else:
            best_score = math.inf
            for i in range(9):
                if board[i] == self.EMPTY:
                    board[i] = self.PLAYER
                    score = self._minimax(board, depth + 1, True)
                    board[i] = self.EMPTY
                    best_score = min(score, best_score)
            return best_score
            
    def _check_winner(self, board, symbol):
        """Check if the given symbol has won."""
        win_patterns = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        return any(all(board[i] == symbol for i in pattern) for pattern in win_patterns)
        
    async def _end_game(self, ctx, game_data, view):
        """End the game and update scores."""
        winner = game_data["winner"]
        embed = discord.Embed()
        
        if winner == "tie":
            embed.title = "🤝 It's a Tie!"
            embed.color = discord.Color.blue()
            embed.description = "The game ended in a draw!"
            for player_id in game_data["players"]:
                if player_id not in self.scores:
                    self.scores[player_id] = {"wins": 0, "losses": 0, "ties": 0}
                self.scores[player_id]["ties"] += 1
                
        elif winner == "ai":
            embed.title = "😔 AI Wins!"
            embed.color = discord.Color.red()
            embed.description = "The AI beat you! Better luck next time."
            player_id = game_data["players"][0]
            if player_id not in self.scores:
                self.scores[player_id] = {"wins": 0, "losses": 0, "ties": 0}
            self.scores[player_id]["losses"] += 1
            
        else:
            winner_user = ctx.guild.get_member(winner) or await self.client.fetch_user(winner)
            embed.title = f"🏆 {winner_user.display_name} Wins!"
            embed.color = discord.Color.green()
            embed.description = f"Congratulations {winner_user.mention}! You won!"
            
            for player_id in game_data["players"]:
                if player_id not in self.scores:
                    self.scores[player_id] = {"wins": 0, "losses": 0, "ties": 0}
                    
            self.scores[winner]["wins"] += 1
            loser_id = next(pid for pid in game_data["players"] if pid != winner)
            self.scores[loser_id]["losses"] += 1
            
        # Clean up
        game_data["active"] = False
        game_data["completed"] = True
        if ctx.channel.id in self.games:
            del self.games[ctx.channel.id]
            
        # Disable all buttons
        if view:
            for child in view.children:
                child.disabled = True
            await view.message.edit(embed=embed, view=view)
        else:
            await ctx.send(embed=embed)

def setup(client):
    client.add_cog(TicTacToeGame(client))