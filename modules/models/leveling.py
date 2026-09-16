from beanie import Document
from pydantic import Field
from typing import List, Any, Optional
from .core import DictModel

# ---------------------------------------------------------
# Leveling plugins
# ---------------------------------------------------------
class LevelingLeaderboardConfig(DictModel):
    banner: Optional[str] = None
    public: bool = False
    url: Optional[str] = None

class LevelingMessageConfig(DictModel):
    content: Optional[str] = None
    status: Optional[Any] = None

class LevelingRoleRewardConfig(DictModel):
    id: Optional[str] = None
    level: Optional[str] = None
    name: Optional[str] = None

class LevelingRoleRewardsConfig(DictModel):
    stacked: bool = False
    roles: List[LevelingRoleRewardConfig] = Field(default_factory=list)

class LevelingConfig(DictModel):
    status: bool = False
    auto_reset: bool = False
    card: Optional[str] = None
    channel: Optional[str] = None
    cooldown: Optional[Any] = None
    economy: bool = False
    max_level: Optional[Any] = None
    noXP: List[str] = Field(default_factory=list)
    message: LevelingMessageConfig = Field(default_factory=LevelingMessageConfig)
    leaderboard: LevelingLeaderboardConfig = Field(default_factory=LevelingLeaderboardConfig)
    roleRewards: LevelingRoleRewardsConfig = Field(default_factory=LevelingRoleRewardsConfig)

class Leveling(Document):
    class Settings:
        name = "leveling"

    id: str = Field(alias="_id")  # Format: "guild_id_user_id"
    guild_id: str
    user_id: str
    exp: int = 0
    lvl: int = 0
    msg_count: int = 0
