from flask import Blueprint, flash, jsonify, render_template, request

from modules import bot as v
from ...db import get_dash_config, update_config
from ...utils import bearer_client, login_required

temporary_channels_bp = Blueprint('temporary_channels', __name__)

@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels")
@login_required
def temporary_channels(guild_id):
    from ...utils import premium_module
    premium_module(guild_id, 'temporary_channels')
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)
    data = get_dash_config(guild.id).get('temporary_channels')
    return render_template(
        "dashboard/plugins/temporary_channels/tc_index.html",
        user=current_user, guild=guild, data=data
    )

@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels/creation", methods=['GET', 'POST'])
@login_required
def temporary_channels_create(guild_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    if request.method == 'POST':
        data = request.get_json()
        data['id'] = v.uuid(length=12, strCase='upper/lower/nums')

        async def run():
            if data['sync_hub_category']:
                if not data['category_id']:
                    category = await guild.create_category_channel(
                        data['hub_name'], reason=f"Temp category for hub {data['id']}"
                    )
                    data['category_id'] = category.id
                else:
                    category = await guild.fetch_channel(data['category_id'])
                    data['category_id'] = category.id
            else:
                category = guild

            vc = await category.create_voice_channel(
                data['hub_name'], reason=f"Temp voice channel for hub {data['id']}"
            )
            data['channel_id'] = vc.id

            hubs = get_dash_config(guild.id).get('temporary_channels')['hubs']
            for key, val in data.items():
                update_config(guild.id, f'Dash.temporary_channels.hubs.{len(hubs)}.{key}', val)

        v.client.loop.create_task(run())
        flash(f"Successfully created hub {data['id']}", 'success')
        return jsonify({'status': 'success', 'message': f"Successfully created hub {data['id']}"})

    return render_template(
        "dashboard/plugins/temporary_channels/tc_create.html",
        user=current_user, guild=guild
    )

@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/edition", methods=['GET', 'POST'])
@login_required
def temporary_channels_edit(guild_id, hub_id):
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    hubs = get_dash_config(guild.id).get('temporary_channels')['hubs']
    hub = next((h for h in hubs if h['id'] == hub_id), None)
    hub_idx = hubs.index(hub)

    if request.method == 'POST':
        data = request.get_json()

        async def run():
            category = None
            if data['sync_hub_category'] and data['category_id']:
                category = await guild.fetch_channel(data['category_id'])
                data['category_id'] = category.id
            channel = await guild.fetch_channel(hub['channel_id'])
            await channel.edit(name=data['hub_name'], category=category)
            for key, val in data.items():
                update_config(guild.id, f'Dash.temporary_channels.hubs.{hub_idx}.{key}', val)

        v.client.loop.create_task(run())
        flash(f"Successfully updated hub {hub['id']}", 'success')
        return jsonify({'status': 'success', 'message': 'Successfully updated hub'})

    return render_template(
        "dashboard/plugins/temporary_channels/tc_edit.html",
        user=current_user, guild=guild, data=hub
    )

@temporary_channels_bp.route("/dashboard/<int:guild_id>/temporary-channels/<hub_id>/delete", methods=['DELETE'])
def temporary_channels_delete(guild_id, hub_id):
    guild = v.client.get_guild(guild_id)
    hubs = get_dash_config(guild.id).get('temporary_channels')['hubs']
    hub = next((h for h in hubs if h['id'] == hub_id), None)

    async def run():
        await v.client.get_channel(hub['channel_id']).delete()
        if hub['sync_hub_category'] and hub['category_id']:
            await v.client.get_channel(hub['category_id']).delete()
        hubs.pop(hubs.index(hub))
        update_config(guild.id, 'Dash.temporary_channels.hubs', hubs)

    v.client.loop.create_task(run())
    flash(f"Successfully deleted hub {hub['id']}", 'success')
    return jsonify({'status': 'success', 'message': 'Successfully deleted hub'})