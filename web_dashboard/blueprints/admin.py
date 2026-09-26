from quart import Blueprint, flash, redirect, render_template, request, url_for
from modules.models import Guild
from web_dashboard.utils import dev_required, get_current_user
from .plugins.leveling import rank_cards
from ..uploads import UploadError, upload_rank_card_image
from ..plugins import plugin_registry, reload_plugin_list

admin_bp = Blueprint('admin', __name__)

# The bot renders this card whenever a server's chosen card is missing (cogs/system/E_leveling.py)
FALLBACK_CARD = "blurple-rank.png"

# ── Site-wide admin: Rank Card Catalog ─────────────────────────────────────────
THEME_DEFAULTS = { "pic": {"bar_bg": "#FFFFFF"}, "brand": {"bar_bg": "#FFFFFF"} }

async def _servers_using_cards():
  """{card key: number of servers that have it selected}"""
  rows = await Guild.aggregate([
    {"$group": {"_id": "$dashboard.leveling.card", "n": {"$sum": 1}}}
  ]).to_list()
  return {r["_id"]: r["n"] for r in rows}

@admin_bp.route("/admin/rank-cards", methods=["GET", "POST"])
@dev_required
async def admin_rank_cards():
  error = None

  if request.method == "POST":
    form = await request.form
    files = await request.files

    card = (form.get("card") or "").strip()
    card_name = (form.get("card_name") or "").strip()
    theme = form.get("theme") or "pic"
    bar_fill = (form.get("bar_fill") or "").strip()
    defaults = THEME_DEFAULTS.get(theme, THEME_DEFAULTS["pic"])

    if not card or not card_name or not bar_fill:
      error = "Card key, name, and bar fill color are required."
    elif rank_cards.find_one({"card": card}):
      error = f"'{card}' already exists."
    else:
      try:
        url = await upload_rank_card_image(files.get("image"))
        rank_cards.insert_one({
          "card": card,
          "card_name": card_name,
          "theme": theme,
          "bar_fill": bar_fill,
          "bar_bg": (form.get("bar_bg") or "").strip() or defaults["bar_bg"],
          "url": url,
        })
        await flash(f"Added {card_name}.", "success")
        return redirect(url_for('admin.admin_rank_cards'))
      except UploadError as e:
        error = str(e)

  cards = list(rank_cards.find({}, {'_id': 0}))
  usage = await _servers_using_cards()
  for c in cards:
    c["servers"] = usage.get(c["card"], 0)

  return await render_template(
    "dashboard/admin/rank_cards.html",
    user=get_current_user(),
    **_sidebar_context(),
    cards=cards,
    theme_defaults=THEME_DEFAULTS,
    fallback_card=FALLBACK_CARD,
    error=error,
  )

# The card key is fixed once created (servers store it); the look and the picture can change.
@admin_bp.route("/admin/rank-cards/<card>/edit", methods=["POST"])
@dev_required
async def edit_rank_card(card):
  form = await request.form
  files = await request.files
  card_name = (form.get("card_name") or "").strip()
  bar_fill = (form.get("bar_fill") or "").strip()
  bar_bg = (form.get("bar_bg") or "").strip()

  if not card_name or not bar_fill or not bar_bg:
    await flash("Name, bar fill color, and bar background color are required.", "error")
    return redirect(url_for('admin.admin_rank_cards'))

  changes = {
    "card_name": card_name,
    "theme": form.get("theme") or "pic",
    "bar_fill": bar_fill,
    "bar_bg": bar_bg,
  }

  image = files.get("image")
  if image and image.filename:
    try:
      changes["url"] = await upload_rank_card_image(image)
    except UploadError as e:
      await flash(str(e), "error")
      return redirect(url_for('admin.admin_rank_cards'))

  if rank_cards.update_one({"card": card}, {"$set": changes}).matched_count == 0:
    await flash(f"'{card}' no longer exists.", "error")
  else:
    await flash(f"Updated {card_name}.", "success")

  return redirect(url_for('admin.admin_rank_cards'))

@admin_bp.route("/admin/rank-cards/<card>/delete", methods=["POST"])
@dev_required
async def delete_rank_card(card):
  if card == FALLBACK_CARD:
    await flash("That's the fallback card the bot uses when a server's card is missing, so it can't be deleted.", "error")
  elif rank_cards.delete_one({"card": card}).deleted_count == 0:
    await flash(f"'{card}' no longer exists.", "error")
  else:
    await flash(f"Deleted {card}. Servers that had it now get the fallback card.", "success")

  return redirect(url_for('admin.admin_rank_cards'))

# ── Site-wide admin: Plugin registry ────────────────────────────────────────
BADGE_CHOICES = ["", "new", "beta", "soon", "prem"]
# (heading, category value) - keep in sync with plugin_categories in components/DashSidebar.html
CATEGORIES = [
  ("Server Management", "management"),
  ("Utilities", "utilities"),
  ("Games & Fun", "fun"),
  ("Social", "social"),
]

def _sidebar_context():
  """What components/AdminSidebar.html needs on every admin page."""
  return {
    "plugins": list(plugin_registry.find({}, {'_id': 0}).sort("category")),
    "categories": CATEGORIES,
  }

def _plugin_form_fields(form):
  return {
    "title": (form.get("title") or "").strip(),
    "description": (form.get("description") or "").strip(),
    "db_key": (form.get("db_key") or "").strip(),
    "icon": (form.get("icon") or "").strip(),
    "url": (form.get("url") or "").strip(),
    "badge": form.get("badge") if form.get("badge") in BADGE_CHOICES else "",
    "category": (form.get("category") or "").strip(),
    "premium": form.get("premium") == "on",
    "status": False,
    "max": int(form["max"]) if (form.get("max") or "").strip().isdigit() else None,
    "max_premium": int(form["max_premium"]) if (form.get("max_premium") or "").strip().isdigit() else None,
  }

@admin_bp.route("/admin/plugins", methods=["GET", "POST"])
@dev_required
async def admin_plugins():
  error = None
  add_values = None  # set on a failed add so the form re-opens with what was typed

  if request.method == "POST":
    form = await request.form
    key = (form.get("key") or "").strip()
    fields = _plugin_form_fields(form)

    if not key or not fields["title"] or not fields["db_key"] or not fields["url"]:
      error = "Key, title, db_key, and url are required."
    elif plugin_registry.find_one({"key": key}):
      error = f"'{key}' already exists."
    else:
      plugin_registry.insert_one({"key": key, **fields})
      reload_plugin_list()
      await flash(f"Added {fields['title']}.", "success")
      return redirect(url_for('admin.admin_plugins'))

    add_values = {**fields, "key": key}

  return await render_template(
    "dashboard/admin/plugins.html",
    user=get_current_user(),
    **_sidebar_context(),
    badge_choices=BADGE_CHOICES,
    add_values=add_values,
    error=error,
  )

@admin_bp.route("/admin/plugins/<key>/edit", methods=["POST"])
@dev_required
async def edit_plugin(key):
  form = await request.form
  fields = _plugin_form_fields(form)

  if not fields["title"] or not fields["db_key"] or not fields["url"]:
    await flash("Title, db_key, and url are required.", "error")
    return redirect(url_for('admin.admin_plugins'))

  if plugin_registry.update_one({"key": key}, {"$set": fields}).matched_count == 0:
    await flash(f"'{key}' no longer exists.", "error")
  else:
    reload_plugin_list()
    await flash(f"Updated {fields['title']}.", "success")

  return redirect(url_for('admin.admin_plugins'))
