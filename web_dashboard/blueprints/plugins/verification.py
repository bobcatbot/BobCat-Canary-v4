import discord
from flask import Blueprint, jsonify, render_template, request

from modules import bot as v
from ...db import get_dash_config, update_config
from ...utils import bearer_client, login_required, premium_module

verification_bp = Blueprint('verification', __name__)


@verification_bp.route("/dashboard/<int:guild_id>/verification", methods=['GET'])
@login_required
def verify(guild_id):
    premium_module(guild_id, 'verification')
    current_user = bearer_client().get_current_user()
    guild = v.client.get_guild(guild_id)

    data = get_dash_config(guild).get('verification')
    return render_template(
        "dashboard/plugins/verification.html",
        user=current_user, guild=guild,
        data=data
    )


@verification_bp.route("/dashboard/<int:guild_id>/verification/publish", methods=['POST'])
def verify_publish(guild_id):
    guild = v.client.get_guild(guild_id)
    data = request.get_json()
    config = get_dash_config(guild)['verification']

    async def publish():
        embed = discord.Embed.from_dict(data['embed'])
        style = {
            'secondary': discord.ButtonStyle.gray,
            'blurple':   discord.ButtonStyle.blurple,
            'danger':    discord.ButtonStyle.red,
            'success':   discord.ButtonStyle.green,
        }[data['btn']['color']]

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            emoji=data['btn']['emoji'] or None,
            label=data['btn']['title'],
            style=style,
            custom_id='Verification'
        ))

        if config['message_published']:
            channel = guild.get_channel(int(config['channel']))
            msg = await channel.fetch_message(int(config['message_id']))
            await msg.edit(embed=embed, view=view)
            return

        role = guild.get_role(int(config['role']))
        if not role:
            role = await guild.create_role(name='Verified', reason='Enabled verification system')
            update_config(guild, 'Dash.verification.role', role.id)

        channel = guild.get_channel(int(config['channel']))
        if not channel:
            channel = await guild.create_text_channel(
                'verification',
                reason='Enabled verification system',
                overwrites={
                    guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
                    role:               discord.PermissionOverwrite(read_messages=True, send_messages=False, read_message_history=True),
                }
            )
            update_config(guild, 'Dash.verification.channel', channel.id)

        await channel.set_permissions(guild.default_role, overwrite=discord.PermissionOverwrite(read_messages=True, send_messages=False))
        await channel.set_permissions(role, overwrite=discord.PermissionOverwrite(read_messages=False, send_messages=False))
        await guild.default_role.edit(reason="Verification system enabled", permissions=discord.Permissions(read_messages=False))
        if role.id == int(config['role']):
            await role.edit(reason="Verification system enabled", permissions=discord.Permissions(read_messages=True))

        msg = await channel.send(embed=embed, view=view)
        update_config(guild, 'Dash.verification.message_id', f'{msg.id}')
        update_config(guild, 'Dash.verification.message_published', True)

    v.client.loop.create_task(publish())
    return jsonify({'status': 'success', 'message': 'Successfully published verification message'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/unpublish", methods=['POST'])
def verify_unpublish(guild_id):
    guild = v.client.get_guild(guild_id)
    config = get_dash_config(guild)['verification']

    async def unpublish():
        channel = guild.get_channel(int(config['channel']))
        msg = await channel.fetch_message(int(config['message_id']))
        await msg.delete()
        update_config(guild, 'Dash.verification.message_published', False)

    v.client.loop.create_task(unpublish())
    return jsonify({'status': 'success', 'message': 'Successfully deleted verification message'})


@verification_bp.route("/dashboard/<int:guild_id>/verification/update", methods=['POST'])
def verify_update(guild_id):
    data = request.get_json()
    guild = v.client.get_guild(guild_id)

    update_config(guild, f'Dash.verification.{data["key"]}', data["value"])
    return jsonify({'status': 'success', 'message': 'Successfully updated verification settings'})