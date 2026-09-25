import discord
from pydantic import Field
from typing import List, Literal
from .core import DictModel

# A trigger must not be able to hand out roles that let a member escalate their own power.
DANGEROUS_PERMISSIONS = discord.Permissions(
    administrator=True, manage_guild=True, manage_roles=True, manage_channels=True,
    manage_webhooks=True, kick_members=True, ban_members=True, moderate_members=True,
)

def role_is_grantable(role: discord.Role, me: discord.Member) -> bool:
    return (
        role < me.top_role
        and not role.managed
        and not role.is_default()
        and not (role.permissions & DANGEROUS_PERMISSIONS).value
    )

# ---------------------------------------------------------
# Custom Commands plugin
# ---------------------------------------------------------
class CustomCommand(DictModel):
    id: str = ""
    enabled: bool = True
    trigger: str
    match: Literal["exact", "contains", "startswith"] = "exact"
    action: Literal["reply", "add_role", "remove_role"] = "reply"
    role_id: str = ""
    reply: str = ""  # required for "reply", optional confirmation for the role actions

class CustomCommandsConfig(DictModel):
    status: bool = False
    commands: List[CustomCommand] = Field(default_factory=list)
