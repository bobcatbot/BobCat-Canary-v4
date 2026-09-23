import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild

async def can_moderate(guild, moderator, member, action="moderate") -> tuple[bool, str | None]:
    settings = (await Guild.get(str(guild.id))).settings

    immune_role_ids = set(
        settings.get("admin_roles", []) +
        settings.get("bot_masters", []) +
        settings.get("moderator_roles", [])
    )

    # `action` is always the "moderate" default in this codebase (no caller
    # overrides it), which maps straight to mod.actions.moderate. A future
    # custom action word with no matching mod.actions.<word> entry would show
    # up as that literal dotted key in the message (msg()'s usual missing-key
    # fallback) rather than crashing - add it to mod.actions if that happens.
    translated_action = v.t.msg(guild, f"mod.actions.{action}")

    if member == guild.owner:
        return False, v.t.msg(guild, "mod.helpers.cannot_owner", action=translated_action)
    if member == moderator:
        return False, v.t.msg(guild, "mod.helpers.cannot_self", action=translated_action)
    if member == guild.me:
        return False, v.t.msg(guild, "mod.helpers.cannot_me", action=translated_action)


    if any(str(role.id) in immune_role_ids for role in member.roles) and moderator != guild.owner:
        return False, v.t.msg(guild, "mod.helpers.immune_role")

    if member.top_role >= guild.me.top_role:
        return False, v.t.msg(guild, "mod.helpers.role_above_mine")
    if moderator != guild.owner and member.top_role >= moderator.top_role:
        return False, v.t.msg(guild, "mod.helpers.role_above_yours")

    return True, None

async def send_member_dm(
    member: discord.Member,
    guild: discord.Guild,
    moderator: discord.Member,
    action: str,
    reason: str,
    dm_fields: list[str],
) -> None:
    if not dm_fields:
        return

    embed = discord.Embed(
        title=v.t.msg(guild, "mod.helpers.dm_title", action=action.lower()),
        color=v.style(guild),
    )

    field_values = {
        "server": (v.t.msg(guild, "mod.helpers.dm_fields.server"), guild.name, True),
        "action": (v.t.msg(guild, "mod.helpers.dm_fields.action"), action, True),
        "moderator": (v.t.msg(guild, "mod.helpers.dm_fields.moderator"), moderator.mention, True),
        "reason": (v.t.msg(guild, "mod.helpers.dm_fields.reason"), reason, False),
    }

    for key in dm_fields:
        field = field_values.get(key)

        if field is None:
            continue

        name, value, inline = field
        embed.add_field(
            name=name,
            value=value,
            inline=inline,
        )

    try:
        await member.send(embed=embed)
    except (discord.Forbidden, discord.HTTPException):
        pass

async def audit_log(
    ctx: commands.Context | discord.Interaction | discord.Guild,
    event: str,
    embed: discord.Embed,
) -> bool:
    guild = ctx if isinstance(ctx, discord.Guild) else getattr(ctx, "guild", None)

    if guild is None:
        return False

    dashboard = await v.dashboard(guild)

    if dashboard is None:
        return False

    logging_config = dashboard.moderation.logging

    if not logging_config.events.get(event, False):
        return False

    channel_id = logging_config.channel

    if not channel_id:
        return False

    try:
        channel_id = int(channel_id)
    except (TypeError, ValueError):
        return False

    channel = guild.get_channel(channel_id)

    if channel is None:
        try:
            channel = await guild.fetch_channel(channel_id)
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            return False

    if not isinstance(channel, discord.TextChannel):
        return False

    try:
        await channel.send(embed=embed)
    except (
        discord.Forbidden,
        discord.HTTPException,
    ):
        return False

    return True