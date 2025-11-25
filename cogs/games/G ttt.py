import discord
import random
from modules import bot as v
from discord.ext import commands

class GamesTTT(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    @commands.slash_command(name="tictactoe", description="Play tic-tac-toe with someone")
    @discord.option("member", discord.Member, description="A member you want to play with", required=True)
    async def _tictactoe(self, ctx, member: discord.Member):
        if member is None:
            return await ctx.respond(embed=discord.Embed(description="**❌ You can't play tic-tac-toe alone!**", color=discord.Color.red()))
        if member == ctx.author:
            return await ctx.respond(embed=discord.Embed(description="**❌ You can't play tic-tac-toe by yourself!**", color=discord.Color.red()))
        
        if member.bot:
            return await ctx.respond(embed=discord.Embed(description="**❌ You can't play with a bot!**", color=discord.Color.red()))

        players = {
            str(ctx.author.id): str(member.id),
            str(member.id): str(ctx.author.id)
        }

        player1 = random.choice(list(players.keys()))
        player2 = players[player1]

        
        view = TicTacToe(
            player1 = ctx.guild.get_member(int(player1)),
            player2 = ctx.guild.get_member(int(player2))
        )
        view.message = await ctx.respond(f"{ctx.guild.get_member(int(player1)).mention}\'s turn (X)", view=view)

def setup(client):
    client.add_cog(GamesTTT(client))

class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        if interaction.user != view.player1 and interaction.user != view.player2:
            return await interaction.response.send_message(embed=discord.Embed(description="**❌ This isn't your game!**", color=discord.Color.red()), ephemeral=True)

        elif interaction.user == view.player1 and view.current_player == view.O:
            return await interaction.response.send_message(embed=discord.Embed(description="**❌ It isn't your turn!**", color=discord.Color.red()), ephemeral=True)

        elif interaction.user == view.player2 and view.current_player == view.X:
            return await interaction.response.send_message(embed=discord.Embed(description="**❌ It isn't your turn!**", color=discord.Color.red()), ephemeral=True)

        if view.current_player == view.X:
            self.emoji = "<:ttt_x:930542490862379130>"
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = f"It is now {view.player2.mention}'s turn (O)"
        else:
            self.emoji = "<:ttt_o:930542761638244483>"
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = f"It is now {view.player1.mention}'s turn (X)"

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = f"{view.player1.mention} won!"
                view.ended = True
            elif winner == view.O:
                content = f"{view.player2.mention} won!"
                view.ended = True
            else:
                content = "It's a tie!"
                view.ended = True

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)
        
from typing import List
class TicTacToe(discord.ui.View):
    children: List[TicTacToeButton]
    X = -1
    O = 1

    def __init__(self, player1: discord.Member, player2: discord.Member):
        super().__init__(timeout=80)
        self.Tie = -2
        self.current_player = self.X
        self.player1 =  player1
        self.player2 = player2
        self.ended = False
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X
                
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

    async def on_timeout(self):
        if self.ended == True:
            return
        for child in self.children:
            child.disabled = True
        
        msg = "**<:error:897382665781669908> The game ended | Player(s) didn't respond within time!**"
        await self.message.edit_original_response(content=msg, embed=None, view=self)
        return