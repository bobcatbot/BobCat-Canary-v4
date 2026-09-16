from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Any, Optional
from .core import DictModel

# ---------------------------------------------------------
# Birthdays plugin
# ---------------------------------------------------------
class BirthdaysConfig(DictModel):
    status: bool = False
    birthday_role: Optional[str] = None
    channel_id: Optional[str] = None
    message: Optional[str] = None
    message_hour: Optional[Any] = None

class Birthday(Document):
    class Settings:
        name = "birthdays"

    id: str = Field(alias="_id")
    guild_id: str
    user_id: str
    date: Optional[str] = None
    age: Optional[int] = None
    wished: bool = False
    wished_at: Optional[datetime] = None
    reminded: bool = False
