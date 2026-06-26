import copy
import json

with open('web_dashboard/plugin_list.json', 'r', encoding='utf-8') as f:
  PLUGIN_LIST = json.load(f)

def fetch_plugins(dash):
  """
  Returns a fresh copy of the plugin list with live status values from the
  guild's dash config. Never mutates the shared PLUGIN_LIST singleton.
  """
  result = copy.deepcopy(PLUGIN_LIST)
  for _item, _plugin in result.items():
    plug = dash.get(_item)
    if plug:
      _plugin['status'] = plug.get('status', False)
  return result.items()