from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import List, Any, Optional
from .core import DictModel

# ---------------------------------------------------------
# Economy plugin
# ---------------------------------------------------------
class ShopItemConfig(DictModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    price: Optional[int] = None
    max_limit: Optional[int] = None
    type: Optional[str] = None

class EconomyConfig(DictModel):
    status: bool = False
    icon: Optional[str] = None
    name: Optional[str] = None
    MaxGambling: Optional[str] = None
    MaxPayment: Optional[str] = None
    shop: List[ShopItemConfig] = Field(default_factory=list)

class Economy(Document):
    class Settings:
        name = "economy"

    id: str = Field(alias="_id")  # Format: "guild_id_user_id"
    guild_id: str
    user_id: str
    wallet: int = 0
    bank: int = 0
    bag: List[Any] = Field(default_factory=list)
    last_daily: Optional[datetime] = None
    daily_streak: int = 0
