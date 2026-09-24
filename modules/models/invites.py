from beanie import Document
from pydantic import Field
from datetime import datetime
from typing import Optional
from .core import DictModel

# ---------------------------------------------------------
# Invite Tracker plugin
# ---------------------------------------------------------
class InviteTrackerConfig(DictModel):
    status: bool = False

class PersonalInvite(Document):
    class Settings:
        name = "personal_invites"

    id: str = Field(alias="_id")  # {guild_id}_{user_id}
    guild_id: str
    user_id: str
    code: str

class InviteJoin(Document):
    class Settings:
        name = "invite_joins"

    id: str = Field(alias="_id")  # {guild_id}_{member_id}, overwritten on rejoin
    guild_id: str
    member_id: str
    inviter_id: str
    code: str
    joined_at: datetime
    left_at: Optional[datetime] = None
