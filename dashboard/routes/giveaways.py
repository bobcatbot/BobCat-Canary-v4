import discord
from dashboard.index import bot, v, bearer_client, login_required, get_server_config, get_dash_config, update_config, premium_module
from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for

giveaways = Blueprint('giveaways', __name__)

@giveaways.route("/dashboard/<int:guild_id>/giveaways")
@login_required
async def giveaways_index(guild_id):
  premium_module(guild_id, 'giveaway')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  plugin = get_dash_config(guild.id).get('giveaway')

  data = get_server_config(guild)['giveaways']
  return render_template("dashboard/plugins/giveaways/gway_index.html", user=current_user, guild=guild, config=plugin, data=data)

@giveaways.route("/dashboard/<int:guild_id>/giveaways/creation", methods=['GET', 'POST'])
@login_required
async def giveaways_creation(guild_id):
  premium_module(guild_id, 'giveaway')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  gways = get_server_config(guild)['giveaways']

  if request.method == 'POST':
    data = request.get_json()
    
    uuid = v.uuid(length=12, strCase="upper/lower/nums")

    channel = guild.get_channel(int(data['channel_id']))

    sdata = {
      'id': uuid, 'guild': guild.id, 'name': data['name'], 'status': 'Ongoing',  'channel': { 'id': channel.id, 'name': channel.name }, 'message': '', 'author': current_user.id, 'time': { 'epoch': data['time.epoch'], 'timestamp': data['time.timestamp'] }, 'prize': data['prize'], 
      'winners': data['winners'],
      'givexp': { 'enabled': data.get('givexp.enabled', False), 'amount': data.get('givexp.amount', 0) },
      'givecoins': { 'enabled': data.get('givecoins.enabled', False), 'amount': data.get('givecoins.amount', 0) },
      'gwinners': [], 'participants': [], 'embed_title': data['embed.title'], 'embed_desc': data['embed.desc'],
    }

    if data['button'] == 'save':
      sdata['status'] = 'Draft'
      # only update the database
      update_config(guild.id, f'Bot.giveaways.{len(gways)}', sdata) 
      
      flash('Giveaway saved successfully!', 'success')
      return jsonify({'status': 'success', 'message': 'Giveaway saved successfully!'})

    if data['button'] == 'publish':
      # create giveaway to discord
      async def create_giveaway():
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(emoji="🎉", style=discord.ButtonStyle.blurple, custom_id="JoinGiveaway"))

        embed = discord.Embed(title=sdata['embed_title'], description=sdata['embed_desc'], color=discord.Color.embed_background())
        embed.add_field(name="Ends", value=f"<t:{int(sdata['time']['epoch'])}:R> (<t:{int(sdata['time']['epoch'])}:f>)", inline=False)
        embed.add_field(name="Hosted by", value=f"<@{current_user.id}>", inline=False)
        embed.add_field(name="Winners", value=f"**{sdata['winners']}**", inline=False)
        embed.add_field(name="Participants", value="**0**", inline=False)
        embed.set_footer(text="Click on the button below to participate!")

        msg = await channel.send(embed=embed, view=view)
        sdata['message'] = msg.id

        update_config(guild.id, f'Bot.giveaways.{len(gways)}', sdata)
      bot.loop.create_task(create_giveaway())      

      flash('Giveaway published successfully!', 'success')
      return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})

  return render_template("dashboard/plugins/giveaways/gway_create.html", user=current_user, guild=guild)

@giveaways.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/edition", methods=['GET', 'POST'])
@login_required
async def giveaways_edition(guild_id, gway_id):
  premium_module(guild_id, 'giveaway')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  gways = get_server_config(guild)['giveaways']

  for _gway in gways:
    if _gway['id'] != gway_id:
      continue
    data = _gway
  
  gway_idx = gways.index(data)

  if request.method == 'POST': # update only
    jdata = request.get_json()
    
    async def runDiscordTask():
      msg = await guild.get_channel(int(data['channel']['id'])).fetch_message(int(data['message']))

      embed = discord.Embed.to_dict(msg.embeds[0])
      embed['title'] = f"🎉 {jdata['prize']} 🎉"
      embed['description'] = jdata['embed.desc']
      embed['fields'][0]['value'] = f"<t:{int(jdata['time.epoch'])}:R> (<t:{int(jdata['time.epoch'])}:f>)"
      embed['fields'][2]['value'] = f"**{jdata['winners']}**"
      embed['fields'][3]['value'] = f"**{len(data['participants'])}**"

      await msg.edit(embed=discord.Embed.from_dict(embed))

      for key, value in jdata.items():
        print(guild.id, f'Bot.giveaways.{gway_idx}.{key}', value)
      return
    bot.loop.create_task(runDiscordTask())
    
    flash('Giveaway updated successfully!', 'success')
    return jsonify({'status': 'successs', 'message': 'Giveaway updated successfully!'})

  return render_template("dashboard/plugins/giveaways/gway_edit.html", user=current_user, guild=guild, data=data)

# TODO: deletion