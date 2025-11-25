import discord

from datetime import datetime
from dashboard.index import bot, login_required, bearer_client, get_dash_config, get_server_config, update_config, premium_module
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

forms = Blueprint('forms', __name__)

## Forms Main ##
@forms.route("/form/<int:guild_id>/<form_id>", methods=['GET', 'POST'])
@login_required
async def form(guild_id, form_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  server_config = get_server_config(guild, True).get('settings')

  if request.method == 'POST':
    data = request.get_json()
    
    forms = get_server_config(guild).get('forms')
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)

    form['responses'].append(data)
    update_config(guild, f'Bot.forms.{form_idx}.responses', form['responses'])

    channel = guild.get_channel(int(form['settings']['submission_channel']))
    async def send_message():
      submitted_at = datetime.fromisoformat(data['submitted_at'])
      embed = discord.Embed(
        title=f"{form['name']} (#{len(form['responses'])})", 
        color=0x5865F2, timestamp=submitted_at, 
      ) 

      for index, question in enumerate(form['questions']):
        embed.add_field(name=question['title'], value=data['answers'][index], inline=False)        

      embed.set_footer(text=f"User ID: {data['user']['id']}")
      msg = await channel.send(embed=embed)

      # thread on submission
      if form['settings']['options']['thread'] == True:
        await msg.create_thread(name=f"{form['name']} ({form['id']})")
      
      form_reactions = form['settings']['options']['reactions']
      if form_reactions['status'] == True and form_reactions['emojis']:
        for emoji in form_reactions['emojis']:
          await msg.add_reaction(emoji)

    bot.loop.create_task(send_message())
    return jsonify({ 'status': 200 })
  
  forms = get_server_config(guild).get('forms')

  for form in forms:
    if form['id'] != form_id:
      continue
    data = form

  return render_template("form.html", user=current_user, guild=guild, data=data)

@forms.route("/form/<int:guild_id>/<form_id>/submissions", methods=['GET', 'POST', 'DELETE'])
@login_required
async def form_submissions(guild_id, form_id):
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)

  user = guild.get_member(current_user.id)
  
  forms = get_server_config(guild).get('forms')

  if request.method == 'DELETE':
    res = request.get_json()
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)
    for response in form['responses']:
      if response['id'] != res['id']:
        continue
      form['responses'].remove(response)
      update_config(guild, f'Bot.forms.{form_idx}.responses', form['responses'])

    return jsonify({ 'status': 200 })

  for _form in forms:
    if _form['id'] != form_id:
      continue
    form = _form
  
  submission_viewers = form['settings'].get('submission_viewers', [])
  submission_managers = form['settings'].get('submission_managers', [])

  allowed_roles = set(submission_viewers) | set(submission_managers)
  user_role_ids = {str(role.id) for role in user.roles}

  if allowed_roles and not user_role_ids & allowed_roles:
    flash('You are not allowed to view the submissions', 'error')
    return redirect(url_for('index'))
  
  # Check if the user can manage submissions
  can_manage = any(str(role.id) in submission_managers for role in user.roles)

  return render_template("form_subs.html", user=current_user, guild=guild, form=form, can_manage=can_manage)


## Forms Config ##
@forms.route("/dashboard/<int:guild_id>/forms")
@login_required
async def forms_cindex(guild_id):
  premium_module(guild_id, 'forms')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  data = get_server_config(guild).get('forms')
  plugin = get_dash_config(guild).get('forms')
  return render_template("dashboard/plugins/forms/form_index.html", user=current_user, guild=guild, data=data, plugin=plugin)
@forms.route("/dashboard/<int:guild_id>/forms/creation", methods=['GET', 'POST'])
@login_required
async def forms_create(guild_id):
  premium_module(guild_id, 'forms')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  if request.method == 'POST':
    data = request.get_json()

    def generateId(length=8):
      import random, string
      letters = string.ascii_letters + string.digits
      return ''.join(random.choice(letters) for i in range(length))

    data['id'] = generateId(12)

    forms = get_server_config(guild).get('forms')

    for key, val in data.items():
      update_config(guild.id, f'Bot.forms.{len(forms)}.{key}', val)
    
    flash(f"Successfully created form {data['id']}", 'success')
    return jsonify({'status': 'success', 'message': f"Successfully created form {data['id']}"})
  
  return render_template("dashboard/plugins/forms/form_create.html", user=current_user, guild=guild)
@forms.route("/dashboard/<int:guild_id>/forms/<form_id>/edit", methods=['GET', 'POST', 'DELETE'])
@login_required
async def forms_edit(guild_id, form_id):
  premium_module(guild_id, 'forms')
  current_user = bearer_client().get_current_user()
  guild = bot.get_guild(guild_id)
  
  if request.method == 'POST':
    data = request.get_json()

    forms = get_server_config(guild).get('forms')
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)
    
    for key, val in data.items():
      update_config(guild.id, f'Bot.forms.{form_idx}.{key}', val)

    return jsonify({'status': 'success', 'message': 'Successfully updated form'})
  
  if request.method == 'DELETE':
    forms = get_server_config(guild).get('forms')
    for _form in forms:
      if _form['id'] != form_id:
        continue
      form = _form

    form_idx = forms.index(form)
    forms.pop(form_idx)
    update_config(guild.id, 'Bot.forms', forms)
    return jsonify({'status': 'success', 'message': 'Successfully deleted form'})

  forms = get_server_config(guild).get('forms')

  for form in forms:
    if form['id'] != form_id:
      continue
    data = form
  
  return render_template("dashboard/plugins/forms/form_edit.html", user=current_user, guild=guild, data=data)
