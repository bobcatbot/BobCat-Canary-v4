import discord, pymongo
from config import BOT_TOKEN, CLIENT_SECRET, mongoURI_db
from zenora import APIClient
from flask import Flask, redirect, url_for, render_template, request, flash, session, jsonify

bot = discord.Client(intents=discord.Intents.all())
client = APIClient(BOT_TOKEN, client_secret=CLIENT_SECRET)

MongoClientBot = pymongo.MongoClient(mongoURI_db)
db = MongoClientBot['Bot']['Bot']

def bearer_client():
  bearer_client = APIClient(session.get("token"), bearer=True)
  return bearer_client.users

def get_server_config(guild: int, all=False):
  try:
    guildID = guild.id
  except AttributeError:
    guildID = guild
  
  data: dict = db.find_one({"_id": str(guildID)})
  if data is None:
    return None
  
  if all:
    return data
  return data["Bot"]

def get_dash_config(guild: int):
  try:
    id = str(guild.id)
  except AttributeError:
    id = str(guild)

  data = db.find_one({'_id': id})
  if data is None:
    return None
  
  return data["Dash"]

def update_config(guild_id: int, key: str, value):
  try:
    id = str(guild_id.id)
  except AttributeError:
    id = str(guild_id)

  d = db.update_one(
    { '_id': id },
    { '$set': { key: value } }
  )
  if d:
    return True
  return False

def login_required(f):
  from functools import wraps
  
  @wraps(f)
  async def decorated_function(*args, **kwargs):
    if 'token' not in session:
      session['redirect'] = request.url
      return render_template("login.html", logInWithDiscord=url_for('login'))
    return await f(*args, **kwargs)
  return decorated_function

class guild_models:
  def __init__(self, guild=None):
    super().__init__()
    self.guild: discord.Guild = guild

  @property
  def roles(self):
    roles = [role for role in self.guild.roles]
    roles.sort(reverse=True)
    return roles
  
  @property
  def channels(self):
    text = [channel for channel in self.guild.text_channels]
    voice = [channel for channel in self.guild.voice_channels]
    categories = [category for category in self.guild.categories]

    def sortFn(chan):
      return chan.position
    
    text.sort(key=sortFn)
    voice.sort(key=sortFn)
    categories.sort(key=sortFn)
    return {"text": text, "voice": voice, "categories": categories}
  
  @property
  def emojis(self):
    emojis = [emoji for emoji in self.guild.emojis]
    return emojis

  @property
  def isPremium(self):
    premiumStatus = False
    data = get_server_config(self.guild, True)
    
    premiumStatus = data['premium']['status']
    return premiumStatus