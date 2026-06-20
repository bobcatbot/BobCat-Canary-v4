import os
from dotenv import load_dotenv

load_dotenv()

URL_BASE = os.getenv('URL_BASE')
PY_ENV = os.getenv('PY_ENV')

APP_SECRET = os.getenv('APP_SECRET')

BOT_TOKEN = os.getenv('BOT_TOKEN')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

REDIRECT_URI = os.getenv('REDIRECT_URI')
OAUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify%20guilds%20email%20guilds.join"

WEBHOOK_PREM = os.getenv('WEBHOOK_PREM')

mongoURI_db = os.getenv('mongoURI_db')
mongo_cdn = os.getenv('mongoURI_cdn')

stripe_config = {
  "PUBLIC_KEY": os.getenv('STRIPE_PUBLIC_KEY'),
  "SECRET_KEY": os.getenv('STRIPE_SECRET_KEY'),
  "WH_KEY": os.getenv('STRIPE_WH_KEY')
}