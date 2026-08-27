import discord
from discord.ext import commands
from modules import bot as v
from modules.models import Guild

async def can_moderate(guild, moderator, member, action="moderate") -> tuple[bool, str | None]:
    settings = (await Guild.get(str(guild.id))).settings

    if member == guild.owner:
        return False, f"You cannot {action} the server owner."
    if member == moderator:
        return False, f"You cannot {action} yourself."
    if member == guild.me:
        return False, f"You cannot make me {action} myself."

    immune_role_ids = set(settings.get("admin_roles", []) + settings.get("bot_masters", [])) # + settings.get("moderator_roles", []))
    if any(str(role.id) in immune_role_ids for role in member.roles) and moderator != guild.owner:
        return False, "That member has an immunity role and cannot be moderated."

    if member.top_role >= guild.me.top_role:
        return False, "That member's highest role is above or equal to my highest role."
    if moderator != guild.owner and member.top_role >= moderator.top_role:
        return False, "That member's highest role is above or equal to your highest role."

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
        title=f"You have been {action.lower()}",
        color=v.style(guild),
    )

    field_values = {
        "server": ("Server", guild.name, True),
        "action": ("Action", action, True),
        "moderator": ("Moderator", moderator.mention, True),
        "reason": ("Reason", reason, False),
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
    ctx: commands.Context | discord.Interaction,
    event: str,
    embed: discord.Embed,
) -> bool:
    guild = getattr(ctx, "guild", None)

    if guild is None:
        return False

    dashboard = await v.dashboard(guild)

    if dashboard is None:
        return False

    moderation = dashboard.moderation or {}
    logging_config = moderation.get("logging", {})
    enabled_events = logging_config.get("events", {})

    if not enabled_events.get(event, False):
        return False

    channel_id = logging_config.get("channel")

    if not channel_id:
        return False

    try:
        channel_id = int(channel_id)
    except (TypeError, ValueError):
        return False

    channel = ctx.guild.get_channel(channel_id)

    if channel is None:
        try:
            channel = await ctx.guild.fetch_channel(channel_id)
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