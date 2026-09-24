from beanie import Document
from pydantic import Field
from datetime import datetime, timezone
from typing import List, Literal, Optional
from .core import DictModel

# ---------------------------------------------------------
# Moderation plugin
# ---------------------------------------------------------
class AntiLinkConfig(DictModel):
    status: bool = False
    block_invites: bool = True
    block_scam_links: bool = True
    action: Literal["delete", "warn", "mute", "kick", "ban"] = "delete"
    whitelist_channels: List[str] = Field(default_factory=list)
    whitelist_roles: List[str] = Field(default_factory=list)
    dm: List[Literal["server", "action", "moderator", "reason"]] = Field(default_factory=list)

class AntiSpamConfig(DictModel):
    status: bool = False
    threshold: int = 5
    interval: int = 10
    action: Literal["delete", "warn", "mute", "kick", "ban"] = "mute"
    whitelist_channels: List[str] = Field(default_factory=list)
    whitelist_roles: List[str] = Field(default_factory=list)
    dm: List[Literal["server", "action", "moderator", "reason"]] = Field(default_factory=list)

class GhostPingConfig(DictModel):
    status: bool = False
    delete_window: int = 60
    action: Literal["delete", "warn", "mute", "kick", "ban"] = "warn"
    whitelist_channels: List[str] = Field(default_factory=list)
    whitelist_roles: List[str] = Field(default_factory=list)
    dm: List[Literal["server", "action", "moderator", "reason"]] = Field(default_factory=list)

class ExcessiveCapsConfig(DictModel):
    status: bool = False
    threshold: int = 70
    min_length: int = 10
    action: Literal["delete", "warn", "mute", "kick", "ban"] = "delete"
    whitelist_channels: List[str] = Field(default_factory=list)
    whitelist_roles: List[str] = Field(default_factory=list)
    dm: List[Literal["server", "action", "moderator", "reason"]] = Field(default_factory=list)

class ExcessiveEmojisConfig(DictModel):
    status: bool = False
    threshold: int = 10
    action: Literal["delete", "warn", "mute", "kick", "ban"] = "delete"
    whitelist_channels: List[str] = Field(default_factory=list)
    whitelist_roles: List[str] = Field(default_factory=list)
    dm: List[Literal["server", "action", "moderator", "reason"]] = Field(default_factory=list)

class RestrictedChannelRule(DictModel):
    channel_id: str
    commands: bool = False
    images: bool = False
    videos: bool = False

class RestrictedChannelsConfig(DictModel):
    channels: List[RestrictedChannelRule] = Field(default_factory=list)
    action: Literal["delete", "warn", "mute", "kick", "ban"] = "delete"
    whitelist_roles: List[str] = Field(default_factory=list)
    dm: bool = False
    reply: bool = False

class AutomatedActionRule(DictModel):
    infractions: int = Field(ge=1, le=150)
    timeframe_count: int = Field(ge=1, le=365)
    timeframe_unit: Literal["minutes", "hours", "days"] = "days"
    action: Literal["mute", "kick", "ban"] = "mute"

class AutomatedActionsConfig(DictModel):
    rules: List[AutomatedActionRule] = Field(default_factory=list)

class AutoModConfig(DictModel):
    antilink: AntiLinkConfig = Field(default_factory=AntiLinkConfig)
    antispam: AntiSpamConfig = Field(default_factory=AntiSpamConfig)
    ghostping: GhostPingConfig = Field(default_factory=GhostPingConfig)
    caps: ExcessiveCapsConfig = Field(default_factory=ExcessiveCapsConfig)
    emojis: ExcessiveEmojisConfig = Field(default_factory=ExcessiveEmojisConfig)
    restricted_channels: RestrictedChannelsConfig = Field(default_factory=RestrictedChannelsConfig)
    automated_actions: AutomatedActionsConfig = Field(default_factory=AutomatedActionsConfig)

class LoggingEventsConfig(DictModel):
    ChannelCreate: bool = False
    ChannelDelete: bool = False
    ChannelUpdate: bool = False
    MemberBan: bool = False
    MemberJoin: bool = False
    MemberLeave: bool = False
    MemberUnban: bool = False
    MemberUpdate: bool = False
    MessageDelete: bool = False
    MessageEdit: bool = False
    ModerationAntiLink: bool = False
    ModerationAntiSpam: bool = False
    ModerationGhostPing: bool = False
    ModerationCaps: bool = False
    ModerationEmojis: bool = False
    ModerationChannelRestriction: bool = False
    ModerationAutomatedAction: bool = False
    ModerationBan: bool = False
    ModerationKick: bool = False
    ModerationMute: bool = False
    ModerationUnban: bool = False
    ModerationUnmute: bool = False
    ModerationUnwarn: bool = False
    ModerationWarn: bool = False
    RoleCreate: bool = False
    RoleDelete: bool = False
    RoleUpdate: bool = False
    ServerEmojis: bool = False
    ServerInviteCreate: bool = False
    ServerInviteDelete: bool = False
    ServerUpdate: bool = False
    Verification: bool = False

class ModerationLoggingConfig(DictModel):
    bots: bool = False
    channel: Optional[str] = None
    events: LoggingEventsConfig = Field(default_factory=LoggingEventsConfig)

class ActionSettingsConfig(DictModel):
    """Base shape for a moderation action's DM-on-punishment settings.
    Values are the embed-field keys _helpers.send_member_dm knows how to
    render - real guild data confirmed to only ever use these four."""
    dm: List[Literal["server", "action", "moderator", "reason"]] = Field(default_factory=list)

class BanSettingsConfig(ActionSettingsConfig):
    deleteMessageDays: Optional[str] = None

class MuteSettingsConfig(ActionSettingsConfig):
    duration: Optional[str] = None
    type: Optional[str] = None

class ModerationSettingsConfig(DictModel):
    ban: BanSettingsConfig = Field(default_factory=BanSettingsConfig)
    kick: ActionSettingsConfig = Field(default_factory=ActionSettingsConfig)
    mute: MuteSettingsConfig = Field(default_factory=MuteSettingsConfig)
    warn: ActionSettingsConfig = Field(default_factory=ActionSettingsConfig)

class ModerationConfig(DictModel):
    status: bool = False
    automod: AutoModConfig = Field(default_factory=AutoModConfig)
    logging: ModerationLoggingConfig = Field(default_factory=ModerationLoggingConfig)
    settings: ModerationSettingsConfig = Field(default_factory=ModerationSettingsConfig)

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
