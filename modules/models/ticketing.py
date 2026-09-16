from beanie import Document
from pydantic import Field, field_validator
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .core import DictModel, EmbedConfig

# ---------------------------------------------------------
# Ticketing plugin
# ---------------------------------------------------------
class TicketMessageConfig(DictModel):
    embed: EmbedConfig = Field(default_factory=EmbedConfig)

def _default_panel_message() -> TicketMessageConfig:
    return TicketMessageConfig(embed=EmbedConfig(
        title="Ticket Tool",
        description="Welcome to our tickets channel. If you have any questions or inquiries, please click on the Open ticket button below to contact the staff!",
    ))

def _default_intro_message() -> TicketMessageConfig:
    return TicketMessageConfig(embed=EmbedConfig(
        description="Your ticket has been created.\nPlease provide any additional info you deem relevant to help us answer faster.",
    ))

class PanelButtonConfig(DictModel):
    emoji: Optional[str] = None
    label: Optional[str] = None
    style: Optional[str] = None

class TicketPanelConfig(DictModel):
    id: Optional[str] = None
    panel_name: Optional[str] = None
    channel_id: Optional[str] = None
    category_open: Optional[str] = None
    category_claimed: Optional[str] = None
    category_closed: Optional[str] = None
    intro_message: TicketMessageConfig = Field(default_factory=_default_intro_message)
    panel_message: TicketMessageConfig = Field(default_factory=_default_panel_message)
    panel_message_id: Optional[str] = None
    panel_button: PanelButtonConfig = Field(default_factory=PanelButtonConfig)
    manager_roles: List[str] = Field(default_factory=list)
    max_open_tickets: Optional[int] = None
    pin_intro: bool = False
    threading_mode: bool = False
    transcript_channel: Optional[str] = None
    transcript_dm: bool = False

class TicketingConfig(DictModel):
    status: bool = False
    panels: List[TicketPanelConfig] = Field(default_factory=list)

class Ticket(Document):
    class Settings:
        name = "tickets"
        indexes = [
            "guild_id",
            "channel_id",
            "creator_id",
            "status",
        ]

    id: str = Field(alias="_id")
    guild_id: str
    channel_id: str
    message_id: str
    creator_id: str
    creator: Dict[str, Any] = Field(default_factory=dict)
    panel_id: Optional[str] = None
    status: str = "open"
    claimed: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "user": {
            "id": "",
            "username": "",
            "avatar": "",
        },
        "updated_at": "",
    })
    closed: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "reason": "",
        "user": {
            "id": "",
            "username": "",
            "avatar": "",
        },
        "updated_at": "",
    })
    reopened: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "user": {
            "id": "",
            "username": "",
            "avatar": "",
        },
        "updated_at": "",
    })
    deleted: Dict[str, Any] = Field(default_factory=lambda: {
        "status": False,
        "user": {
            "id": "",
            "username": "",
            "avatar": "",
        },
        "updated_at": "",
    })
    transcript: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id(cls, value):
        # Older ticket docs were stored with an ObjectId _id.
        return str(value) if value is not None else value

class TicketMessage(Document):
    """One transcript message, stored separately from `Ticket` so a long-running
    ticket doesn't force a full rewrite of a growing embedded array on every
    message (and can't approach MongoDB's 16MB document cap)."""

    class Settings:
        name = "ticket_messages"
        indexes = [
            "ticket_id",
            "guild_id",
            [("ticket_id", 1), ("created_at", 1)],
        ]

    id: str = Field(alias="_id")  # Discord message id
    ticket_id: str
    guild_id: str
    channel_id: str
    user: Dict[str, Any] = Field(default_factory=dict)
    content: str = ""
    embeds: List[Dict[str, Any]] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    pin: bool = False
    edited: bool = False
    edited_at: Optional[datetime] = None
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
