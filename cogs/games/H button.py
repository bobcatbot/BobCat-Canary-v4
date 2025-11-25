import discord
import sqlite3
from modules import bot as v
from discord.ext import commands

con = sqlite3.connect('databases/button.db')
cur = con.cursor()

class Buttons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Click me", style=discord.ButtonStyle.gray, custom_id="button")
    async def click(self, button: discord.ui.Button, interaction: discord.Interaction):
        cur.execute("SELECT * FROM button WHERE guild = ?", (interaction.guild.id,))
        data = cur.fetchone()
        cur.execute("UPDATE button SET count = ? WHERE guild = ?", (int(data[1]) + 1, interaction.guild.id))
        cur.execute("UPDATE button SET btn_clicker = ? WHERE guild = ?", (interaction.user.id, interaction.guild.id))
        con.commit()

        cur.execute("SELECT * FROM button WHERE guild = ?", (interaction.guild.id,))
        res = cur.fetchone()
        em = discord.Embed(
            title="Click the buton", 
            description=f"The button was clicked **{res[1]}** times"
        )
        em.set_footer(icon_url=interaction.user.avatar.url, text=f"Last clicked by {interaction.user.name}")
        await interaction.response.edit_message(embed=em, view=self)

class GamesButton(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.persistent_views_added = False
    
    @commands.Cog.listener()
    async def on_ready(self):
        cur.execute("CREATE TABLE IF NOT EXISTS button (guild TEXT, count TEXT,btn_clicker TEXT)")
        con.commit()
        #print("Buttons database created")

        if not self.persistent_views_added:
            self.client.add_view(Buttons())
    
    @commands.slash_command(description="Click the button")
    async def button(self, ctx):

        cur.execute("SELECT * FROM button WHERE guild = ?", (ctx.guild.id,))
        data = cur.fetchone()
        if data:
            count = data[1]
        else:
            cur.execute("INSERT INTO button (guild, count, btn_clicker) VALUES (?, ?, ?)", (ctx.guild.id, "0", ctx.author.id))
            con.commit()
            count = "0"
        
        em = discord.Embed(title="Click the buton", description="")
        em.description += f"The button was clicked **{count}** times"
        em.set_footer(icon_url=ctx.author.avatar.url, text=f"Last clicked by {ctx.author.name}")
        await ctx.respond(embed=em, view=Buttons())
    
def setup(client):
    client.add_cog(GamesButton(client))