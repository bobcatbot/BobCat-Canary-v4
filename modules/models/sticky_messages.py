from beanie import Document
from pydantic import Field
from typing import List
from .core import DictModel

# ---------------------------------------------------------
# Sticky Messages plugin
# ---------------------------------------------------------
class StickyMessage(DictModel):
    channel_id: str
    text: str

class StickyMessagesConfig(DictModel):
    status: bool = False
    messages: List[StickyMessage] = Field(default_factory=list)

class StickyState(Document):
    """The sticky currently posted in a channel. Kept out of DashConfig because it changes on
    every repost, and rewriting the guild document per message would fight with dashboard saves."""
    class Settings:
        name = "sticky_states"

    id: str = Field(alias="_id")  # {guild_id}_{channel_id}
    guild_id: str
    channel_id: str
    message_id: str
