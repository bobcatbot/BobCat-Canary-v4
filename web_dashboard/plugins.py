import json

with open('web_dashboard/plugin_list.json', 'r', encoding='utf-8') as f:
  PLUGIN_LIST = json.load(f)

def fetch_plugins(dash):
  for _item, _plugin in PLUGIN_LIST.items():
    plug = dash.get(_item)
    _plugin['status'] = plug['status']
  
  return PLUGIN_LIST.items()