import pytz

premium_faqs = [
  {
    'title': "What is BobCat premium?",
    'desc': "BobCat premium is a subscription where you can get to support the development of the bot. While it's not mandatory to use BobCat but it allows you to unlock exclusive features."
  },
  {
    'title': "Can I get a refund if I don't like it?",
    'desc': "We want everyone to have a great experience with BobCat Premium. If you're not satisfied during your first week, please contact us and we will issue you a full refund."
  },
  {
    'title': "How many Discord servers is my subscription valid for?",
    'desc': "A subscription is valid for a single Discord server. If you wish to get premium for multiple servers, you need a subscription for each server."
  },
  {
    'title': "Can I transfer my premium subscription to another server?",
    'desc': "No, At this current moment of time you cannot transfer a subscription to another server."
  },
  {
    'title': "What is the money used for?",
    'desc': "BobCat is a real company run by real people. Premium is what keeps it alive. We use the money to pay salaries to our developers and to cover hosting."
  }
]

premium_types = {
  'monthly': {
    'price_id': 'price_1ODPSVDUmGmAJQ2o9OYR93OV',
    'price': '6.00',
    'mode': 'subscription',
    'features': [
      "Access to our premium plugins & features",
      "Early access",
      "Priority support"
    ]
  },
  'yearly': {
    'price_id': 'price_1ODPTfDUmGmAJQ2on8Ie2wUs',
    'price': '50.00',
    'mode': 'subscription',
    'features': [
      "Access to our premium plugins & features",
      "Early access",
      "Priority support"
    ]
  },
  'lifetime': {
    'price_id': 'price_1ODPUUDUmGmAJQ2oILOX7jwl',
    'price': '70.00',
    'mode': 'payment',
    'features': [
      "Access to our premium plugins & features",
      "Early access",
      "Priority support"
    ]
  }
}

flags = {
  "staff": "https://cdn3.emoji.gg/emojis/8485-discord-employee.png",
  "partner": "https://cdn3.emoji.gg/emojis/6714-discord-partner.png",
  "early_supporter": "https://cdn3.emoji.gg/emojis/3121-discord-earlysupporter.png",
  "hypesquad": "https://cdn3.emoji.gg/emojis/3809-discord-hypesquad.png",
  "hypesquad_bravery": "https://cdn3.emoji.gg/emojis/1247-discord-bravery.png",
  "hypesquad_brilliance": "https://cdn3.emoji.gg/emojis/1350-discord-brillance.png",
  "hypesquad_balance": "https://cdn3.emoji.gg/emojis/5946-discord-balance.png",
  "bug_hunter": "https://cdn3.emoji.gg/emojis/7732-discord-bughunterlv1.png",
  "bug_hunter_level_2": "https://cdn3.emoji.gg/emojis/7732-discord-bughunterlv2.png",
  "verified_bot_developer": "https://cdn3.emoji.gg/emojis/1564-badge-developer.png",
  "discord_certified_moderator": "https://cdn3.emoji.gg/emojis/9765-badge-moderators.png",
  "active_developer": "https://cdn3.emoji.gg/emojis/2156-active-developer.png"
}

langs = [
  { 'flag': 'https://em-content.zobj.net/thumbs/120/twitter/351/flag-united-kingdom_1f1ec-1f1e7.png', 'name': 'English, UK', 'code': 'en-GB' },
  { 'flag': 'https://em-content.zobj.net/thumbs/120/twitter/351/flag-united-states_1f1fa-1f1f8.png', 'name': 'English, US', 'code': 'en-US' },
]

# Full IANA timezone list, sourced from pytz's bundled tz database
# (already a project dependency) rather than hand-maintained - keeps
# this in sync with real timezone data with zero upkeep. NOTE: stdlib
# zoneinfo.available_timezones() is NOT a safe substitute here - on
# Windows it returns an empty set unless the extra `tzdata` package is
# installed, since Windows doesn't ship the IANA database itself.
tz = sorted(pytz.all_timezones)

# Reserved names a custom leaderboard slug may not use (avoids confusing URLs
# and collisions with real top-level paths).
RESERVED_SLUGS = {
    "dashboard", "leaderboard", "oauth", "login", "logout", "callback",
    "docs", "status", "api", "premium", "terms", "thanks", "contact-us",
    "plugins", "static", "lvl-cards", "t", "stripe", "web",
    "favicon.ico", "robots.txt", "sitemap.xml", "index", "about",
}
