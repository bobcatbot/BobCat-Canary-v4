from beanie import Document
from pydantic import Field
from typing import List, Optional
from .core import DictModel

# ---------------------------------------------------------
# Temporary channels plugin
# ---------------------------------------------------------
class HubPermissionsConfig(DictModel):
    manage_channels: bool = False
    manage_permissions: bool = False
    move_members: bool = False
    priority_speaker: bool = False

class HubConfig(DictModel):
    id: Optional[str] = None
    channel_id: Optional[str] = None
    hub_name: Optional[str] = None
    name: Optional[str] = None
    bitrate: Optional[int] = None
    user_limit: Optional[int] = None
    sync_hub_category: bool = False
    permissions: HubPermissionsConfig = Field(default_factory=HubPermissionsConfig)

class TemporaryChannelsConfig(DictModel):
    status: bool = False
    hubs: List[HubConfig] = Field(default_factory=list)

class TempChannel(Document):
    class Settings:
        name = "temp_channels"
        indexes = ["guild_id", "channel_id", "creator_id", "hub_id"]

    guild_id: str
    channel_id: str
    creator_id: str
    hub_id: Optional[str] = None
    index: int = 1
