from beanie import Document
from pydantic import Field
from typing import Dict, List, Optional

# ---------------------------------------------------------
# Insights
# ---------------------------------------------------------
class InsightsDaily(Document):
    """One document per guild per day (in the guild's timezone), incremented in place by the
    collector (cogs/system/M_insights.py). Counter maps are keyed by
    channel id / command name / hour-of-day ("0"-"23") so a new breakdown
    is just another `$inc` path - no schema change."""

    class Settings:
        name = "insights"
        indexes = [
            [("guild_id", 1), ("date", -1)],
        ]

    id: str = Field(alias="_id")  # "<guild_id>:<YYYY-MM-DD>"
    guild_id: str
    date: str  # YYYY-MM-DD, guild timezone

    joins: int = 0
    leaves: int = 0
    member_count: Optional[int] = None  # latest snapshot for the day
    boosts: Optional[int] = None  # latest snapshot for the day
    boost_tier: Optional[int] = None
    leave_age: Dict[str, int] = Field(default_factory=dict)  # how long leavers had been members: 1d | 7d | 30d | older

    messages: int = 0
    replies: int = 0
    with_attachments: int = 0
    with_links: int = 0
    active_users: List[str] = Field(default_factory=list)  # ids of everyone who spoke; only the count is ever shown
    hourly: Dict[str, int] = Field(default_factory=dict)
    channels: Dict[str, int] = Field(default_factory=dict)

    voice_minutes: float = 0
    voice_channels: Dict[str, float] = Field(default_factory=dict)

    reactions: int = 0
    emojis: Dict[str, int] = Field(default_factory=dict)

    commands: Dict[str, int] = Field(default_factory=dict)
