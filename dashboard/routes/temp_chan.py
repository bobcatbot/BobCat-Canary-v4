from dashboard.index import bot, login_required, bearer_client, get_dash_config, update_config, premium_module
from flask import Blueprint, render_template, request, flash, jsonify

temp_chan = Blueprint('temp_chan', __name__)

@temp_chan.route("/dashboard/<int:guild_id>/temporary-channels", methods=['GET'])
@login_required
async def temporary_channels(guild_id):
  premium_module(guild_id, 'temporary_channels')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  tempchan_data = get_dash_config(guild.id).get('temporary_channels')
  return render_template("dashboard/plugins/temporary_channels/tc_index.html", user=current_user, guild=guild, data=tempchan_data)

@temp_chan.route("/dashboard/<int:guild_id>/temporary-channels/creation", methods=['GET', 'POST'])
@login_required
async def temporary_channels_create(guild_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == 'POST':
    data = request.get_json()

    def generateId(length=8):
      import random, string
      letters = string.ascii_letters + string.digits
      return ''.join(random.choice(letters) for i in range(length))

    data['id'] = generateId(12)

    async def runDiscordTask():
      if data['sync_hub_category'] == True:
        if data['category_id'] == '':
          # create category
          category = await guild.create_category_channel(data['hub_name'], reason=f"Temporary category for hub {data['id']}")
          data['category_id'] = category.id
        else:
          category = await guild.fetch_channel(data['category_id'])
          data['category_id'] = category.id
      else:
        category = guild

      vc = await category.create_voice_channel(data['hub_name'], reason=f"Temporary voice channel for hub {data['id']}")
      data['channel_id'] = vc.id
      
      tempchan_data = get_dash_config(guild.id).get('temporary_channels')['hubs']
      
      for key, val in data.items():
        update_config(guild.id, f'Dash.temporary_channels.hubs.{len(tempchan_data)}.{key}', val)
      
      return vc
    bot.loop.create_task(runDiscordTask())

    flash(f"Successfully created hub {data['id']}", 'success')
    return jsonify({'status': 'success', 'message': f"Successfully created hub {data['id']}"})
  
  return render_template("dashboard/plugins/temporary_channels/tc_create.html", user=current_user, guild=guild)

@temp_chan.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/edition", methods=['GET', 'POST', 'DELETE'])
@login_required
async def temporary_channels_edit(guild_id, hub_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  tempchan_data = get_dash_config(guild.id).get('temporary_channels')['hubs']

  for _hub in tempchan_data:
    if _hub['id'] != hub_id:
      continue
    hub = _hub
  
  if request.method == 'POST':
    data = request.get_json()

    hub_idx = tempchan_data.index(hub)
    
    async def runDiscordTask():
      if data['sync_hub_category'] == True:
        if data['category_id'] != '':
          category = await guild.fetch_channel(data['category_id'])
          data['category_id'] = category.id

      channel = await guild.fetch_channel(hub['channel_id'])
      await channel.edit(name=data['hub_name'], category=category)
      
      for key, val in data.items():
        update_config(guild.id, f'Dash.temporary_channels.hubs.{hub_idx}.{key}', val)
    
    bot.loop.create_task(runDiscordTask())
    flash(f"Successfully updated hub {hub['id']}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully updated hub'})
  
  return render_template("dashboard/plugins/temporary_channels/tc_edit.html", user=current_user, guild=guild, data=hub)

@temp_chan.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/delete", methods=['DELETE'])
async def temporary_channels_delete(guild_id, hub_id):
  guild = bot.get_guild(guild_id)

  tempchan_data = get_dash_config(guild.id).get('temporary_channels')['hubs']

  for hub in tempchan_data:
    if hub['id'] != hub_id:
      continue
    data = hub
  
  async def runDiscordTask():
    await bot.get_channel(data['channel_id']).delete()

    if data['sync_hub_category'] == True:
      if data['category_id'] != '':
        await bot.get_channel(data['category_id']).delete()

    tempchan_idx = tempchan_data.index(data)
    tempchan_data.pop(tempchan_idx)
    update_config(guild.id, 'Dash.temporary_channels.hubs', tempchan_data)
    return
  bot.loop.create_task(runDiscordTask())

  flash(f"Successfully deleted hub {data['id']}", 'success')
  return jsonify({'status': 'success', 'message': 'Successfully deleted hub'})
