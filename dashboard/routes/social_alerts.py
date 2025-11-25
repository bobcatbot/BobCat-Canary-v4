import os
import json
import requests
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from dashboard.index import bot, bearer_client
from flask import Blueprint, render_template, request, session, flash, jsonify, redirect, url_for

from dotenv import load_dotenv
load_dotenv()

social_alerts = Blueprint('social_alerts', __name__)

# Disable OAuthlib's HTTPS verification when running locally
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# ~~ YOUTUBE - OAuth 2.0 credentials (from Google Cloud Console) ~~
CLIENT_SECRETS_FILE = "./dashboard/client_secret_891255097662-8h2f723jd5cunchghmerkgcpess23ds9.apps.googleusercontent.com.json"  # Download this from Google Cloud Console
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]
YTREDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI")

# ~~ TWITCH ~~
TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_REDIRECT_URI = os.getenv("TWITCH_REDIRECT_URI")

# ~~ TIKTOK ~~
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REDIRECT_URI = "https://cc0b-2a02-c7c-7a80-5000-911c-f366-1d96-fc99.ngrok-free.app/logintotiktok/callback"

@social_alerts.route("/dashboard/<int:guild_id>/alerts", methods=['GET', 'POST'])
async def socialAlerts(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == 'POST':
    data = request.get_json()
    
    if data['plugin'] == 'youtube':
      with open("server.json", "r") as f:
        jdata = json.load(f)
      config = jdata['Dash']['social_alerts']

      if data['key'] == 'youtube.discord.channel_id':
        config['youtube']['discord']['channel_id'] = data['value']
      if data['key'] == 'youtube.discord.vid_message':
        config['youtube']['discord']['vid_message'] = data['value']

      if data['key'] == 'twitch.discord.channel_id':
        config['twitch']['discord']['channel_id'] = data['value']
      if data['key'] == 'twitch.discord.message':
        config['twitch']['discord']['message'] = data['value']

      if data['key'] == 'tiktok.discord.channel_id':
        config['tiktok']['discord']['channel_id'] = data['value']
      if data['key'] == 'tiktok.discord.message':
        config['tiktok']['discord']['message'] = data['value']
      
      with open("server.json", "w") as f:
        json.dump(jdata, f, indent=2)

  with open("server.json", "r", encoding='utf-8') as f:
    data = json.load(f)
  config = data['Dash']['social_alerts']
  return render_template("dashboard/plugins/socialAlerts.html", user=current_user, guild=guild, data=config)


# ========== YOUTUBE ========== #
@social_alerts.route("/logintoyoutube/<guild_id>")
def logintoyoutube(guild_id):
  # Step 1: Redirect the user to the OAuth authorization URL
  flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=YTREDIRECT_URI
  )
  authorization_url, state = flow.authorization_url(
    access_type="offline",  # Request a refresh token
    include_granted_scopes="true",
    state=guild_id
  )

  # Store the state in the session for later validation
  session["state"] = state
  return redirect(authorization_url)

@social_alerts.route("/logintoyoutube/callback")
def logintoyoutube_callback():
  # Handle the OAuth redirect and exchange the authorization code for tokens
  flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=YTREDIRECT_URI,
    state=session.get("state")  # Validate the state
  )
  flow.fetch_token(authorization_response=request.url)

  guild_id = session.get("state")

  # Use the access token to get the connected channel
  credentials = flow.credentials
  youtube = build("youtube", "v3", credentials=credentials)
  ytrequest = youtube.channels().list(part="snippet", mine=True)
  response = ytrequest.execute()

  with open("server.json", "r") as f:
    data = json.load(f)
  config = data['Dash']['social_alerts']['youtube']
  
  config['channel']['id'] = response["items"][0]["id"]
  config['channel']['name'] = response["items"][0]["snippet"]["localized"]["title"]
  config['channel']['url'] = response["items"][0]["snippet"]["customUrl"]
  config['channel']['profile_picture'] = response["items"][0]["snippet"]["thumbnails"]["high"]["url"]

  with open("server.json", "w") as f:
    json.dump(data, f, indent=2)
  return redirect(url_for("social_alerts", guild_id=guild_id) + "#youtube")


# ========== TWITCH ========== #
@social_alerts.route("/logintotwitch/<guild_id>")
def logintotwitch(guild_id):
  auth_url = (
    f"https://id.twitch.tv/oauth2/authorize"
    f"?client_id={TWITCH_CLIENT_ID}"
    f"&redirect_uri={TWITCH_REDIRECT_URI}"
    f"&response_type=code"
    f"&scope=user:read:email"  # Add required scopes here
    f"&state={guild_id}"  # Include the guild_id in the state parameter
  )
  return redirect(auth_url)

@social_alerts.route("/logintotwitch/callback")
def logintotwitch_callback():
  code = request.args.get("code")
  state = request.args.get("state") # Include guild_id in the state

  # Verify the state
  if not code or not state:
    return "Authorization failed: Missing code or state.", 400

  # Exchange the code for an access token
  token_url = "https://id.twitch.tv/oauth2/token"
  data = {
    "client_id": TWITCH_CLIENT_ID,
    "client_secret": TWITCH_CLIENT_SECRET,
    "code": code,
    "grant_type": "authorization_code",
    "redirect_uri": TWITCH_REDIRECT_URI,
  }
  response = requests.post(token_url, data=data)
  response_data = response.json()

  print(response_data)

  if "access_token" not in response_data:
    return "Authorization failed: Could not retrieve access token.", 400

  access_token = response_data["access_token"]

  user_profile = requests.get("https://api.twitch.tv/helix/users", headers={
    "Client-ID": TWITCH_CLIENT_ID,
    "Authorization": f"Bearer {access_token}"
  }).json()
  
  with open("server.json", "r") as f:
    data = json.load(f)
  config = data['Dash']['social_alerts']['twitch']
  
  config['channel']['id'] = user_profile["data"][0]["id"]
  config['channel']['name'] = user_profile["data"][0]["user_login"]
  config['channel']['profile_picture'] = user_profile["data"][0]["profile_image_url"]

  with open("server.json", "w") as f:
    json.dump(data, f, indent=2)

  return redirect(url_for("social_alerts", guild_id=state) + "#twitch")


# ========== TIKTOK ========== #
@social_alerts.route("/logintotiktok/<int:guild_id>")
async def logintotiktok(guild_id):
  ttauth_url = (
    f"https://www.tiktok.com/v2/auth/authorize/"
    f"?client_key={TIKTOK_CLIENT_KEY}"
    f"&response_type=code"
    f"&scope=user.info.basic,user.info.profile,video.list"
    f"&redirect_uri={TIKTOK_REDIRECT_URI}"
    f"&state={guild_id}"
  )
  return redirect(ttauth_url)
@social_alerts.route("/logintotiktok/callback")
def logintotiktok_callback():
  # Extract the authorization code and state from the query parameters
  authorization_code = request.args.get("code")
  state = request.args.get("state")

  if not authorization_code:
    return "Authorization failed: No authorization code found.", 400

  # Exchange the authorization code for an access token
  token_url = "https://open.tiktokapis.com/v2/oauth/token/"
  token_data = {
    'client_key': TIKTOK_CLIENT_KEY,
    'client_secret': TIKTOK_CLIENT_SECRET,
    'grant_type': 'authorization_code',
    'code': authorization_code,
    'redirect_uri': TIKTOK_REDIRECT_URI
  }

  authResponse = requests.post(token_url, data=token_data)

  if authResponse.status_code != 200:
    return "Authorization failed: Could not retrieve access token.", 400

  auth_response = authResponse.json()

  # Fetch user info
  user_info_url = "https://open.tiktokapis.com/v2/user/info/?fields=open_id,username,avatar_large_url"
  headers = {
    'Authorization': f'Bearer {auth_response["access_token"]}',
  }
  user_info = requests.get(user_info_url, headers=headers).json()
  print("User Info Response:", user_info)

  if user_info['error']['code'] != 'ok':
    return "Authorization failed: Could not retrieve user info.", 400
  
  with open("server.json", "r") as f:
    data = json.load(f)
  config = data['Dash']['social_alerts']['tiktok']
  
  config['channel']['token'] = auth_response['refresh_token']
  config['channel']['id'] = user_info['data']['user']['open_id']
  config['channel']['name'] = user_info['data']['user']['username']
  config['channel']['profile_picture'] = user_info['data']['user']['avatar_large_url']

  with open("server.json", "w") as f:
    json.dump(data, f, indent=2)

  return redirect(url_for("social_alerts", guild_id=state) + "#tiktok")