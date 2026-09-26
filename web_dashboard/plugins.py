import copy
import json
import pymongo

from .config import mongoURI_db

with open('web_dashboard/plugin_list.json', 'r', encoding='utf-8') as f:
  _BOOTSTRAP_PLUGIN_LIST = json.load(f)

# Plugin metadata (title/description/badge/category/item caps/...) lives in Mongo,
# not this JSON file, so an admin edit (web_dashboard/blueprints/admin.py) takes
# effect immediately - no process restart. The JSON above is only a one-time seed
# for a fresh database. See reload_plugin_list() below.
plugin_registry = pymongo.MongoClient(mongoURI_db)['Bot']['plugin_registry']

PLUGIN_LIST: dict = {}

def by_order(docs):
  """Registry docs in sidebar order. `order` is set by dragging in /admin/plugins; docs
  without one (never dragged, or newly added) keep their natural order after the ordered ones."""
  return sorted(docs, key=lambda d: d.get('order', float('inf')))

def reload_plugin_list() -> None:
  """Refresh PLUGIN_LIST from Mongo. Called once at boot (main.py, right after the
  database connects) and again after every /admin/plugins create/edit, so a saved
  change is live on the very next request.

  Mutates PLUGIN_LIST in place (clear + update) rather than rebinding the name -
  every plugin blueprint did `from .plugins import PLUGIN_LIST`, which binds its
  own reference to this exact dict object at import time. Reassigning `PLUGIN_LIST`
  here would leave all of those pointing at a stale, empty dict forever.
  """
  if plugin_registry.count_documents({}) == 0:
    plugin_registry.insert_many([
      {**meta, 'key': key} for key, meta in _BOOTSTRAP_PLUGIN_LIST.items()
    ])

  fresh = {
    doc['key']: {k: v for k, v in doc.items() if k not in ('_id', 'key')}
    for doc in by_order(plugin_registry.find({}))
  }
  PLUGIN_LIST.clear()
  PLUGIN_LIST.update(fresh)

def fetch_plugins(dash):
  """
  Returns a fresh copy of the plugin list with live status values from the guild's DashConfig. `dash` is a pydantic DashConfig object.
  Uses getattr() instead of .get() because DashConfig is not a dict.

  Deep-copies the in-memory PLUGIN_LIST instead of re-reading/re-parsing plugin_list.json from disk.
  this is called several times per page render (once per plugins()/get_plugin() call in the templates), 
  so re-parsing the file each time was pure overhead for static data.
  """
  PluginList = copy.deepcopy(PLUGIN_LIST)

  if dash is not None:
    for plugin in PluginList.values():
      # DashConfig fields are named by db_key, not the plugin list key.
      # Each field is a DictModel instance (or a plain dict for anything not yet migrated to a typed sub-model) - both support .get().
      plug_config = getattr(dash, plugin['db_key'], None)
      if plug_config is not None and hasattr(plug_config, 'get'):
        plugin['status'] = plug_config.get('status', False)
      else:
        plugin['status'] = False

  return PluginList.items()
