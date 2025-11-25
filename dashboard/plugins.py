import json

def fetch_plugins(dash):
  with open('dashboard/plugin_list.json', 'r', encoding='utf-8') as f:
    plugins_dict = json.load(f)

  for _item, _plugin in plugins_dict.items():
    plug = dash.get(_item)
    _plugin['status'] = plug['status']
  
  return plugins_dict.items()