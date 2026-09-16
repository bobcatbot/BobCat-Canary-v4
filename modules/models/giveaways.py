from beanie import Document
from pydantic import Field
from typing import List, Dict, Any
from .core import DictModel, EmbedFieldConfig

# ---------------------------------------------------------
# Giveaways plugin
# ---------------------------------------------------------
class GiveawaysConfig(DictModel):
    status: bool = False

class Giveaway(Document):
    class Settings:
        name = "giveaways"
        indexes = ["guild_id", "message_id", "status"]

    id: str = Field(alias="_id")
    guild_id: str
    name: str = "giveaway"
    prize: str
    status: str = "Ongoing"
    channel_id: str
    channel_name: str
    message_id: str
    author_id: str
    embed_title: str
    embed_desc: str
    embed_color: int = 0x5865f2
    embed_fields: List[EmbedFieldConfig] = Field(default_factory=list)
    end_epoch: float
    end_timestamp: str
    winner_count: int = 1
    participants: List[str] = Field(default_factory=list)
    winners: List[str] = Field(default_factory=list)
    give_xp: Dict[str, Any] = Field(default_factory=dict)
    give_coins: Dict[str, Any] = Field(default_factory=dict)
