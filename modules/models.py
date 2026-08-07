from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bunnet import Document
from pydantic import Field, BaseModel

# ---------------------------------------------------------
# Embedded Dash Sub-Models (Optional, for Autocomplete!)
# ---------------------------------------------------------
class DashConfig(BaseModel):
    """Embedded Dashboard configuration inside Guild document"""

    # Member lifecycle & safety
    welcome: Dict[str, Any] = Field(default_factory=dict)
    verification: Dict[str, Any] = Field(default_factory=dict)
    moderation: Dict[str, Any] = Field(default_factory=dict)

    # Engagement & economy
    leveling: Dict[str, Any] = Field(default_factory=dict)
    economy: Dict[str, Any] = Field(default_factory=dict)
    starboard: Dict[str, Any] = Field(default_factory=dict)
    giveaways: Dict[str, Any] = Field(default_factory=dict)

    # Server utility
    ticketing: Dict[str, Any] = Field(default_factory=dict)
    temporary_channels: Dict[str, Any] = Field(default_factory=dict)
    forms: Dict[str, Any] = Field(default_factory=dict)

    # Misc
    birthdays: Dict[str, Any] = Field(default_factory=dict)

    # TODO: add these
    # sticky_messages: Dict[str, Any] = Field(default_factory=dict)

# =========================================================
# COLLECTIONS
# =========================================================
class Guild(Document):
    class Settings:
        name = "guilds"

    id: str = Field(alias="_id")  # Guild ID
    premium: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    dashboard: DashConfig = Field(default_factory=DashConfig, alias="Dash")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Notification(Document):
    class Settings:
        name = "notifications"

    guild_id: str
    notification_id: str
    type: str = "info"
    title: str
    description: Optional[str] = None
    fix: Optional[str] = None
    link: Optional[str] = None
    user: Optional[str] = None
    read: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

class Warning(Document):
    class Settings:
        name = "warnings"
        indexes = ["guild_id", "user_id", "case"]

    guild_id: str
    user_id: str
    case: str
    reason: str = "No reason provided"
    moderator_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Economy(Document):
    class Settings:
        name = "economy"

    id: str = Field(alias="_id")  # Format: "guild_id_user_id"
    guild_id: str
    user_id: str
    wallet: int = 0
    bank: int = 0
    bag: List[Any] = Field(default_factory=list)

class Leveling(Document):
    class Settings:
        name = "leveling"

    id: str = Field(alias="_id")  # Format: "guild_id_user_id"
    guild_id: str
    user_id: str
    exp: int = 0
    lvl: int = 0
    msg_count: int = 0

class Starboard(Document):
    class Settings:
        name = "starboards"
        indexes = ["guild_id", "root_message_id", "star_message_id"]

    guild_id: str
    root_message_id: str
    star_message_id: str
    stars: int = 1

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
    channel_name: str = ""
    message_id: str
    author_id: str
    embed_title: str = ""
    embed_desc: str = ""
    end_epoch: float
    end_timestamp: str = ""
    winner_count: int = 1
    participants: List[str] = Field(default_factory=list)
    winners: List[str] = Field(default_factory=list)
    give_xp: Dict[str, Any] = Field(default_factory=dict)
    give_coins: Dict[str, Any] = Field(default_factory=dict)


class Form(Document):
    class Settings:
        name = "forms"

    guild_id: str
    name: str
    description: Optional[str] = ""
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)
    status: bool = True

class FormResponse(Document):
    class Settings:
        name = "form_responses"

    guild_id: str
    form_id: str
    user_id: str
    answers: List[Any] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Ticket(Document):
    class Settings:
        name = "tickets"
        indexes = [
            "guild_id",
            "channel_id",
            "creator_id",
            "status",
        ]

    guild_id: str
    channel_id: str
    message_id: str
    creator_id: str
    creator: Dict[str, Any] = Field(default_factory=dict)
    panel_id: Optional[str] = None
    status: str = "open"
    claimed_by: Optional[str] = None
    claimed: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "user": "",
        "updated_at": "",
    })
    closed: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "reason": "",
        "user": "",
        "updated_at": "",
    })
    reopened: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "user": "",
        "updated_at": "",
    })
    deleted: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "user": "",
        "updated_at": "",
    })
    transcript: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

class TempChannel(Document):
    class Settings:
        name = "temp_channels"
        indexes = ["guild_id", "channel_id", "creator_id"]

    guild_id: str
    channel_id: str
    creator_id: str
    index: int = 1


# List of all models to pass to init
ALL_MODELS = [
    Guild,
    Notification,
    Warning,
    Economy,
    Leveling,
    Starboard,
    Giveaway,
    Form,
    FormResponse,
    Ticket,
    TempChannel,
    Birthday,
]