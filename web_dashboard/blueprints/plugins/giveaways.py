import discord
from flask import Blueprint, flash, jsonify, render_template, request

from modules import bot as v
from ...db import get_dash_config, get_server_config, update_config
from ...utils import bearer_client, login_required, premium_module

giveaways_bp = Blueprint('giveaways', __name__)

@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways")
@login_required
def giveaways(guild_id):
    premium_module(guild_id, 'giveaway')
    
    current_user = bearer_client().get_current_user()
    
    guild = v.client.get_guild(guild_id)
    return render_template(
        "dashboard/plugins/giveaways/gway_index.html",
        user=current_user, 
        guild=guild,
        config=get_dash_config(guild.id).get('giveaway'),
        data=get_server_config(guild)['giveaways']
    )

@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/creation", methods=['GET', 'POST'])
@login_required
def giveaways_creation(guild_id):
    premium_module(guild_id, 'giveaway')
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    gways = get_server_config(guild)['giveaways']

    if request.method == 'POST':
        data = request.get_json()
        uuid = v.uuid(length=12, strCase="upper/lower/nums")
        channel = guild.get_channel(int(data['channel_id']))

        sdata = {
            'id': uuid, 'guild': guild.id, 'name': data['name'], 'status': 'Ongoing',
            'channel': {'id': channel.id, 'name': channel.name},
            'message': '', 'author': current_user.id,
            'time': {'epoch': data['time.epoch'], 'timestamp': data['time.timestamp']},
            'prize': data['prize'], 'winners': data['winners'],
            'givexp':    {'enabled': data.get('givexp.enabled',    False), 'amount': data.get('givexp.amount',    0)},
            'givecoins': {'enabled': data.get('givecoins.enabled', False), 'amount': data.get('givecoins.amount', 0)},
            'gwinners': [], 'participants': [],
            'embed_title': data['embed.title'], 'embed_desc': data['embed.desc'],
        }

        if data['button'] == 'save':
            sdata['status'] = 'Draft'
            update_config(guild.id, f'Bot.giveaways.{len(gways)}', sdata)
            flash('Giveaway saved successfully!', 'success')
            return jsonify({'status': 'success', 'message': 'Giveaway saved successfully!'})

        if data['button'] == 'publish':
            async def create():
                view = discord.ui.View(timeout=None)
                view.add_item(discord.ui.Button(emoji="🎉", style=discord.ButtonStyle.blurple, custom_id="JoinGiveaway"))
                embed = discord.Embed(
                    title=sdata['embed_title'], description=sdata['embed_desc'],
                    color=discord.Color.embed_background()
                )
                embed.add_field(name="Ends",         value=f"<t:{int(sdata['time']['epoch'])}:R> (<t:{int(sdata['time']['epoch'])}:f>)", inline=False)
                embed.add_field(name="Hosted by",    value=f"<@{current_user.id}>",      inline=False)
                embed.add_field(name="Winners",      value=f"**{sdata['winners']}**",    inline=False)
                embed.add_field(name="Participants", value="**0**",                       inline=False)
                embed.set_footer(text="Click on the button below to participate!")
                msg = await channel.send(embed=embed, view=view)
                sdata['message'] = msg.id
                update_config(guild.id, f'Bot.giveaways.{len(gways)}', sdata)

            v.client.loop.create_task(create())
            flash('Giveaway published successfully!', 'success')
            return jsonify({'status': 'success', 'message': 'Giveaway published successfully!'})

    return render_template(
        "dashboard/plugins/giveaways/gway_create.html", 
        user=current_user, 
        guild=guild
    )

@giveaways_bp.route("/dashboard/<int:guild_id>/giveaways/<gway_id>/edition", methods=['GET', 'POST'])
@login_required
def giveaways_edition(guild_id, gway_id):
    premium_module(guild_id, 'giveaway')
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    gways = get_server_config(guild)['giveaways']
    data = next((g for g in gways if g['id'] == gway_id), None)
    gway_idx = gways.index(data)

    if request.method == 'POST':
        jdata = request.get_json()

        async def run():
            msg = await guild.get_channel(int(data['channel']['id'])).fetch_message(int(data['message']))
            embed = discord.Embed.to_dict(msg.embeds[0])
            embed['title']          = f"🎉 {jdata['prize']} 🎉"
            embed['description']    = jdata['embed.desc']
            embed['fields'][0]['value'] = f"<t:{int(jdata['time.epoch'])}:R> (<t:{int(jdata['time.epoch'])}:f>)"
            embed['fields'][2]['value'] = f"**{jdata['winners']}**"
            embed['fields'][3]['value'] = f"**{len(data['participants'])}**"
            await msg.edit(embed=discord.Embed.from_dict(embed))
            for key, value in jdata.items():
                update_config(guild.id, f'Bot.giveaways.{gway_idx}.{key}', value)

        v.client.loop.create_task(run())
        flash('Giveaway updated successfully!', 'success')
        return jsonify({'status': 'success', 'message': 'Giveaway updated successfully!'})

    return render_template(
        "dashboard/plugins/giveaways/gway_edit.html", 
        user=current_user, 
        guild=guild, 
        data=data
    )