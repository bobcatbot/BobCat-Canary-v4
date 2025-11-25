import discord
from modules import bot as v
from flask import Blueprint, render_template, request, flash, jsonify
from dashboard.index import bot, login_required, bearer_client, get_dash_config, update_config, premium_module

ticketing = Blueprint('ticketing', __name__)

## Ticketing ##
@ticketing.route("/dashboard/<int:guild_id>/ticketing")
@login_required
async def ticketing_index(guild_id):
  premium_module(guild_id, 'ticketing')
  
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  dash_data = get_dash_config(guild.id).get('ticketing')
  return render_template("dashboard/plugins/ticketing/ticketing_index.html", user=current_user, guild=guild, data=dash_data)

@ticketing.route("/dashboard/<int:guild_id>/ticketing/creation", methods=['GET', 'POST'])
@login_required
async def ticketing_create(guild_id):
  premium_module(guild_id, 'ticketing')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  if request.method == "POST":
    data = request.get_json()

    def generateId(length=8):
      import random, string
      letters = string.ascii_letters + string.digits
      return ''.join(random.choice(letters) for i in range(length))

    data['id'] = generateId(12)

    async def runDiscordTask():
      ticketing_data = get_dash_config(guild.id).get('ticketing')['pannels']

      for key, val in data.items():
        # print(guild.id, f'Dash.ticketing.pannels.{len(ticketing_data)}.{key}', val)
        update_config(guild.id, f'Dash.ticketing.pannels.{len(ticketing_data)}.{key}', val)

      pmEmbed = discord.Embed(
        title=data['pannel_message.embed.title'],
        description=data['pannel_message.embed.description'],
        color=data['pannel_message.embed.color']
      )

      view = discord.ui.View()
      view.add_item(discord.ui.Button(
        emoji=data['pannel_button.emoji'],
        label=data['pannel_button.label'],
        style=getattr(discord.ButtonStyle, data['pannel_button.style']),
        custom_id='create_ticket'
      ))

      channel = guild.get_channel(int(data['channel_id']))
      msg = await channel.send(embed=pmEmbed, view=view)

      update_config(guild.id, f'Dash.ticketing.pannels.{len(ticketing_data)}.pannel_message_id', str(msg.id))
      return
    bot.loop.create_task(runDiscordTask())
    flash(f"Successfully created ticket pannel {data['id']}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully created ticket'})
  
  return render_template("dashboard/plugins/ticketing/ticketing_create.html", user=current_user, guild=guild)

@ticketing.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/edition", methods=['GET', 'POST'])
@login_required
async def ticketing_edit(guild_id, ticket_id):
  premium_module(guild_id, 'ticketing')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  ticket_data = get_dash_config(guild.id).get('ticketing')['pannels']

  for ticket in ticket_data:
    if ticket['id'] != ticket_id:
      continue
    tk_data = ticket
  
  ticket_idx = ticket_data.index(tk_data)

  if request.method == 'POST':
    data = request.get_json()
    
    async def runDiscordTask():
      pannel_message = guild.get_channel(int(tk_data['channel_id'])).get_partial_message(int(tk_data['pannel_message_id']))
      
      pmEmbed = discord.Embed(
        title=data.get('pannel_message.embed.title', tk_data['pannel_message']['embed']['title']),
        description=data.get('pannel_message.embed.description', tk_data['pannel_message']['embed']['description']),
        color=data.get('pannel_message.embed.color', tk_data['pannel_message']['embed']['color'])
      )
      
      view = discord.ui.View()
      view.add_item(discord.ui.Button(
        emoji=data.get('pannel_button.emoji', tk_data['pannel_button']['emoji']),
        label=data.get('pannel_button.label', tk_data['pannel_button']['label']),
        style=getattr(discord.ButtonStyle, data.get('pannel_button.style', tk_data['pannel_button']['style'])),
        custom_id='create_ticket'
      ))
      await pannel_message.edit(embed=pmEmbed, view=view)

      for key, val in data.items():
        update_config(guild.id, f'Dash.ticketing.pannels.{ticket_idx}.{key}', val)
      return
    bot.loop.create_task(runDiscordTask())

    flash(f"Successfully updated ticket pannel {ticket_id}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully updated ticket'})
  
  return render_template("dashboard/plugins/ticketing/ticketing_edit.html", user=current_user, guild=guild, data=tk_data)

@ticketing.route("/dashboard/<int:guild_id>/ticketing/<ticket_id>/delete", methods=['DELETE'])
async def ticketing_delete(guild_id, ticket_id):
  guild = bot.get_guild(guild_id)

  ticket_data = get_dash_config(guild.id).get('ticketing')['pannels']

  for ticket in ticket_data:
    if ticket['id'] != ticket_id:
      continue
    data = ticket

  async def runDiscordTask():
    pannel_message = guild.get_channel(int(data['channel_id'])).get_partial_message(int(data['pannel_message_id']))
    await pannel_message.delete()
    
    ticket_data.pop(ticket_data.index(data))
    update_config(guild.id, 'Dash.ticketing.pannels', ticket_data)
  bot.loop.create_task(runDiscordTask())

  flash(f"Successfully deleted ticket pannel {ticket_id}", 'success')
  return jsonify({'status': 'success', 'message': 'Successfully deleted ticket pannel'})
