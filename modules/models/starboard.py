from beanie import Document
from pydantic import Field
from typing import List, Any, Optional
from .core import DictModel

# ---------------------------------------------------------
# Starboard plugin
# ---------------------------------------------------------
class StarboardConfig(DictModel):
    status: bool = False
    allowNsfw: bool = False
    autoStar: List[Any] = Field(default_factory=list)
    channel: Optional[str] = None
    embedNsfwImages: bool = False
    emoji: Optional[str] = None
    ignore: List[Any] = Field(default_factory=list)
    jumpLink: bool = False
    limit: Optional[str] = None
    locked: bool = False
    selfStar: bool = False

class Starboard(Document):
    class Settings:
        name = "starboards"
        indexes = ["guild_id", "root_message_id", "star_message_id"]

    guild_id: str
    root_message_id: str
    star_message_id: str
    stars: int = 1
