"""Shared dashboard UI components and save helpers."""
from collections.abc import Callable
from datetime import datetime
from typing import Any

import discord
from discord.ui import ActionRow, button

from modules.models import Guild

UPDATED_AT_FORMAT = "%Y-%m-%d %H:%M"

def _guild_id(guild: discord.Guild | int) -> int:
    return guild.id if isinstance(guild, discord.Guild) else int(guild)

def _get_guild(guild: discord.Guild | int) -> Guild | None:
    return Guild.get(str(_guild_id(guild))).run()

def _format_updated_at(guild: discord.Guild | int) -> str:
    config = _get_guild(guild)
    if config is None or config.updated_at is None:
        return "Never"

    return config.updated_at.strftime(UPDATED_AT_FORMAT)

def save_dash(guild: discord.Guild | int, key: str, value: Any) -> bool:
    """Update one nested dashboard value and the guild timestamp."""
    if not key or key.startswith(".") or key.endswith("."):
        raise ValueError("A valid dashboard key is required.")

    config = _get_guild(guild)
    if config is None:
        return False

    parts = key.split(".")
    current: Any = config.dashboard

    for index, part in enumerate(parts[:-1]):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            next_part = parts[index + 1]
            if part not in current:
                current[part] = [] if next_part.isdigit() else {}
            current = current[part]
        else:
            current = getattr(current, part)

    final = parts[-1]
    if isinstance(current, list):
        index = int(final)
        if index == len(current):
            current.append(value)
        else:
            current[index] = value
    elif isinstance(current, dict):
        current[final] = value
    else:
        setattr(current, final, value)

    config.updated_at = discord.utils.utcnow()
    config.save()
    return True

def refresh_footer(view: discord.ui.View | None, guild: discord.Guild | int) -> None:
    """Refresh the disabled 'Updated at' footer button when one exists."""
    if view is None or not hasattr(view, "get_item"):
        return

    footer = view.get_item("SaveSuccess")
    if footer is not None:
        footer.label = f"Updated at: {_format_updated_at(guild)}"

def FooterRow(
    guild: discord.Guild | int,
    back_to: Callable[[], discord.ui.View],
) -> ActionRow:
    """Build the standard dashboard back button and update timestamp."""
    timestamp = _format_updated_at(guild)

    class _FooterRow(ActionRow):
        @button(label="Go Back", style=discord.ButtonStyle.primary)
        async def go_back(
            self,
            btn: discord.ui.Button,
            interaction: discord.Interaction,
        ):
            await interaction.response.edit_message(view=back_to())

        @button(
            label=f"Updated at: {timestamp}",
            style=discord.ButtonStyle.gray,
            custom_id="SaveSuccess",
            disabled=True,
        )
        async def save_success(
            self,
            btn: discord.ui.Button,
            interaction: discord.Interaction,
        ):
            pass

    return _FooterRow()

def BackButton(back_to: Callable[[], discord.ui.View]) -> ActionRow:
    """Build a standalone dashboard back button."""

    class _BackButton(ActionRow):
        @button(label="Go Back", style=discord.ButtonStyle.primary)
        async def go_back(
            self,
            btn: discord.ui.Button,
            interaction: discord.Interaction,
        ):
            await interaction.response.edit_message(view=back_to())

    return _BackButton()

def StatusToggle(
    guild: discord.Guild | int,
    dash_key: str,
    initial: bool,
    custom_id: str = "status",
) -> ActionRow:
    """Build a dashboard status toggle backed by ``Dash.<dash_key>``."""

    class _StatusToggle(ActionRow):
        @button(
            label="Enabled" if initial else "Disabled",
            style=(
                discord.ButtonStyle.green
                if initial
                else discord.ButtonStyle.red
            ),
            custom_id=custom_id,
        )
        async def toggle(
            self,
            btn: discord.ui.Button,
            interaction: discord.Interaction,
        ):
            new_value = btn.label != "Enabled"

            if not save_dash(guild, dash_key, new_value):
                return await interaction.response.send_message(
                    "I couldn't save that dashboard setting.",
                    ephemeral=True,
                )

            btn.label = "Enabled" if new_value else "Disabled"
            btn.style = (
                discord.ButtonStyle.green
                if new_value
                else discord.ButtonStyle.red
            )

            refresh_footer(interaction.view, guild)
            await interaction.response.edit_message(view=interaction.view)

    return _StatusToggle()