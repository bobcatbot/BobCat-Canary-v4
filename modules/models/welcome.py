from pydantic import Field
from typing import Optional, List
from .core import DictModel, EmbedConfig

# ---------------------------------------------------------
# Welcome plugin
# ---------------------------------------------------------
class MessageConfig(DictModel):
    type: Optional[str] = None
    content: Optional[str] = None
    embed: EmbedConfig = Field(default_factory=EmbedConfig)

class WelcomeJoinConfig(DictModel):
    status: bool = False
    channel: Optional[str] = None
    message: MessageConfig = Field(default_factory=MessageConfig)

class WelcomeLeaveConfig(DictModel):
    status: bool = False
    channel: Optional[str] = None
    message: MessageConfig = Field(default_factory=MessageConfig)

class WelcomeDMConfig(DictModel):
    status: bool = False
    message: MessageConfig = Field(default_factory=MessageConfig)

class WelcomeAutoRolesConfig(DictModel):
    status: bool = False
    roles: List[str] = Field(default_factory=list)

class WelcomeConfig(DictModel):
    status: bool = False
    join: WelcomeJoinConfig = Field(default_factory=WelcomeJoinConfig)
    leave: WelcomeLeaveConfig = Field(default_factory=WelcomeLeaveConfig)
    dm: WelcomeDMConfig = Field(default_factory=WelcomeDMConfig)
    autoRoles: WelcomeAutoRolesConfig = Field(default_factory=WelcomeAutoRolesConfig)
