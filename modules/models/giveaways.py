from beanie import Document
from pydantic import ConfigDict, Field
from typing import List, Dict, Any
from .core import DictModel, EmbedConfig

# ---------------------------------------------------------
# Giveaways plugin
# ---------------------------------------------------------
class GiveawaysConfig(DictModel):
    status: bool = False

class Giveaway(Document):
    # The dashboard assigns whatever the page posts, so validate on assignment:
    # "3" becomes 3, an embed dict becomes an EmbedConfig, a bad value is rejected.
    model_config = ConfigDict(validate_assignment=True)

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
    embed: EmbedConfig = Field(default_factory=lambda: EmbedConfig(color=0x5865f2))
    end_epoch: float
    end_timestamp: str
    winner_count: int = 1
    participants: List[str] = Field(default_factory=list)
    winners: List[str] = Field(default_factory=list)
    give_xp: Dict[str, Any] = Field(default_factory=dict)
    give_coins: Dict[str, Any] = Field(default_factory=dict)
