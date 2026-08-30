import copy
import json

with open('web_dashboard/plugin_list.json', 'r', encoding='utf-8') as f:
  PLUGIN_LIST = json.load(f)

def fetch_plugins(dash):
  """
  Returns a fresh copy of the plugin list with live status values from the
  guild's DashConfig. `dash` is a pydantic DashConfig object.
  Uses getattr() instead of .get() because DashConfig is not a dict.
  """
  result = PLUGIN_LIST
  
  if dash is not None:
    for plugin in result.values():
      # DashConfig fields are named by db_key, not the plugin list key
      plug_config = getattr(dash, plugin['db_key'], None)
      if isinstance(plug_config, dict):
        plugin['status'] = plug_config.get('status', False)
      else:
        plugin['status'] = False
  
  return result.items()