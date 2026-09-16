import discord
from bson import ObjectId
from beanie import Document
from pydantic import ConfigDict, Field, BaseModel, field_validator
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Literal

# ---------------------------------------------------------
# DictModel: Pydantic model that still behaves like a dict
# ---------------------------------------------------------
class DictModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    def get(self, key, default=None):
        return getattr(self, key, default)

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __contains__(self, key):
        return hasattr(self, key)

    def setdefault(self, key, default=None):
        if getattr(self, key, None) is None:
            setattr(self, key, default)
        return getattr(self, key)

    def keys(self):
        return self.model_dump().keys()

    def items(self):
        return self.model_dump().items()

    def values(self):
        return self.model_dump().values()

    def copy(self):
        return self.model_dump()

    def update(self, other=None, **kwargs):
        for key, value in {**(other or {}), **kwargs}.items():
            setattr(self, key, value)

# ---------------------------------------------------------
# Shared embed shape (used by welcome/verification messages and
# ticketing panels — all built through the same embed_editor.html
# component, so they share one schema). Every field is optional
# since the editor only ever writes what the user filled in.
# ---------------------------------------------------------
class EmbedFieldConfig(DictModel):
    name: Optional[str] = None
    value: Optional[str] = None
    inline: bool = False

class EmbedAuthorConfig(DictModel):
    name: Optional[str] = None

class EmbedFooterConfig(DictModel):
    text: Optional[str] = None

class EmbedConfig(DictModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    color: Optional[Any] = None
    title: Optional[str] = None
    description: Optional[str] = None
    author: EmbedAuthorConfig = Field(default_factory=EmbedAuthorConfig)
    footer: EmbedFooterConfig = Field(default_factory=EmbedFooterConfig)
    fields: List[EmbedFieldConfig] = Field(default_factory=list)

    @field_validator('color', mode='before')
    @classmethod
    def _coerce_color(cls, v):
        """Dashboard color pickers hand back a hex string ("#5865f2" or "5865f2");
        Discord embeds and the DB store an int. Coerce here so every writer -
        dashboard routes, the bot itself - can just assign either shape."""
        if isinstance(v, str) and v.strip():
            return int(v.strip().lstrip('#'), 16)
        return v

    def to_embed(self, transform=None) -> discord.Embed:
        """Build a live discord.Embed from this config.

        Must dump with exclude_none - discord.Embed.from_dict expects an
        unset color/title/etc. to be an ABSENT key (as in a real Discord API
        payload), not an explicit `null`; passing `color: None` through
        raises `TypeError: Expected int parameter, received NoneType`.

        `transform`, if given, runs on the dumped dict before it becomes an
        embed - e.g. recursively substituting {user}/{server} placeholders
        (welcome/goodbye messages) without every caller re-implementing its
        own dump-then-from_dict dance.
        """
        data = self.model_dump(exclude_none=True)
        if transform is not None:
            data = transform(data)
        return discord.Embed.from_dict(data)

# ---------------------------------------------------------
# Welcome plugin
# ---------------------------------------------------------
class MessageConfig(DictModel):
    type: Optional[str] = None
    content: Optional[str] = None
    embed: EmbedConfig = Field(default_factory=EmbedConfig)

class WelcomeJoinConfig(DictModel):
    status: bool = False
    channel: Optional[str] = None
    message: MessageConfig = Field(default_factory=MessageConfig)

class WelcomeLeaveConfig(DictModel):
    status: bool = False
    channel: Optional[str] = None
    message: MessageConfig = Field(default_factory=MessageConfig)

class WelcomeDMConfig(DictModel):
    status: bool = False
    message: MessageConfig = Field(default_factory=MessageConfig)

class WelcomeAutoRolesConfig(DictModel):
    status: bool = False
    roles: List[str] = Field(default_factory=list)

class WelcomeConfig(DictModel):
    status: bool = False
    join: WelcomeJoinConfig = Field(default_factory=WelcomeJoinConfig)
    leave: WelcomeLeaveConfig = Field(default_factory=WelcomeLeaveConfig)
    dm: WelcomeDMConfig = Field(default_factory=WelcomeDMConfig)
    autoRoles: WelcomeAutoRolesConfig = Field(default_factory=WelcomeAutoRolesConfig)

# ---------------------------------------------------------
# Verification plugin
# ---------------------------------------------------------
class VerificationButtonConfig(DictModel):
    color: Optional[str] = None
    emoji: Optional[str] = None
    title: Optional[str] = None

class VerificationMessageConfig(DictModel):
    btn: VerificationButtonConfig = Field(default_factory=VerificationButtonConfig)
    embed: EmbedConfig = Field(default_factory=EmbedConfig)

class VerificationConfig(DictModel):
    status: bool = False
    mode: Optional[str] = None
    role: Optional[Any] = None
    channel: Optional[str] = None
    failAction: Optional[str] = None
    message_id: Optional[str] = None
    message_published: bool = False
    message: VerificationMessageConfig = Field(default_factory=VerificationMessageConfig)

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

class AutoModConfig(DictModel):
    antilink: AntiLinkConfig = Field(default_factory=AntiLinkConfig)
    antispam: AntiSpamConfig = Field(default_factory=AntiSpamConfig)
    ghostping: GhostPingConfig = Field(default_factory=GhostPingConfig)
    caps: ExcessiveCapsConfig = Field(default_factory=ExcessiveCapsConfig)

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

# ---------------------------------------------------------
# Server utility plugins
# ---------------------------------------------------------
class StarboardConfig(DictModel):
    status: bool = False
    allowNsfw: bool = False
    autoStar: List[Any] = Field(default_factory=list)
    channel: Optional[str] = None
    embedNsfwImages: bool = False
    emoji: Optional[str] = None
    ignore: List[Any] = Field(default_factory=list)
    jumpLink: bool = False
    limit: Optional[str] = None
    locked: bool = False
    selfStar: bool = False

# ---------------------------------------------------------
# Forms plugin
# ---------------------------------------------------------
class FormsConfig(DictModel):
    status: bool = False

# ---------------------------------------------------------
# Temporary channels plugin
# ---------------------------------------------------------
class HubPermissionsConfig(DictModel):
    manage_channels: bool = False
    manage_permissions: bool = False
    move_members: bool = False
    priority_speaker: bool = False

class HubConfig(DictModel):
    id: Optional[str] = None
    channel_id: Optional[str] = None
    hub_name: Optional[str] = None
    name: Optional[str] = None
    bitrate: Optional[int] = None
    user_limit: Optional[int] = None
    sync_hub_category: bool = False
    permissions: HubPermissionsConfig = Field(default_factory=HubPermissionsConfig)

class TemporaryChannelsConfig(DictModel):
    status: bool = False
    hubs: List[HubConfig] = Field(default_factory=list)

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

# ---------------------------------------------------------
# Statistics plugin
# ---------------------------------------------------------
class StatsCounterConfig(DictModel):
    channel_id: Optional[str] = None
    count: Optional[int] = None
    position: Optional[int] = None
    target: Optional[str] = None
    text: Optional[str] = None

class StatsConfig(DictModel):
    status: bool = False
    counters: List[StatsCounterConfig] = Field(default_factory=list)

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

# ---------------------------------------------------------
# Birthdays plugin
# ---------------------------------------------------------
class BirthdaysConfig(DictModel):
    status: bool = False
    birthday_role: Optional[str] = None
    channel_id: Optional[str] = None
    message: Optional[str] = None
    message_hour: Optional[Any] = None

# ---------------------------------------------------------
# Giveaways plugin
# ---------------------------------------------------------
class GiveawaysConfig(DictModel):
    status: bool = False

# ---------------------------------------------------------
# Economy plugin
# ---------------------------------------------------------
class EconomyConfig(DictModel):
    status: bool = False
    icon: Optional[str] = None
    name: Optional[str] = None
    MaxGambling: Optional[str] = None
    MaxPayment: Optional[str] = None
    shop: List[ShopItemConfig] = Field(default_factory=list)

class ShopItemConfig(DictModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    price: Optional[int] = None
    max_limit: Optional[int] = None
    type: Optional[str] = None

# =========================================================

# ---------------------------------------------------------
# Guild.premium / Guild.settings
# ---------------------------------------------------------
class PremiumConfig(DictModel):
    """Guild.premium 
    \nThis is written almost entirely by the Stripe webhook handlers in web_dashboard/blueprints/stripe.py.
    \nEvery field optional since a fresh/cancelled guild's premium is `{}` (an all-defaults PremiumConfig)."""

    id: Optional[str] = None
    status: bool = False
    active: bool = False
    plan: Optional[str] = None
    customer: Optional[str] = None
    user_id: Optional[Any] = None
    period_end: Optional[datetime] = None
    subscribed_at: Optional[datetime] = None
    code_expiry: Optional[datetime] = None

class SettingsConfig(DictModel):
    """Guild.settings - general server settings."""
    language: Optional[str] = None
    timezone: Optional[str] = None
    color: Optional[str] = None
    admin_roles: List[str] = Field(default_factory=list)
    bot_masters: List[str] = Field(default_factory=list)
    moderator_roles: List[str] = Field(default_factory=list)

# ---------------------------------------------------------
# Dashboard Config
# ---------------------------------------------------------
class DashConfig(BaseModel):
    """Embedded Dashboard configuration inside Guild document"""

    # Management
    welcome: WelcomeConfig = Field(default_factory=WelcomeConfig)
    moderation: ModerationConfig = Field(default_factory=ModerationConfig)
    verification: VerificationConfig = Field(default_factory=VerificationConfig)

    # Server utility
    starboard: StarboardConfig = Field(default_factory=StarboardConfig)
    forms: FormsConfig = Field(default_factory=FormsConfig)
    temporary_channels: TemporaryChannelsConfig = Field(default_factory=TemporaryChannelsConfig)
    ticketing: TicketingConfig = Field(default_factory=TicketingConfig)
    stats: StatsConfig = Field(default_factory=StatsConfig)

    # Engagement & economy
    leveling: LevelingConfig = Field(default_factory=LevelingConfig)
    birthdays: BirthdaysConfig = Field(default_factory=BirthdaysConfig)
    giveaways: GiveawaysConfig = Field(default_factory=GiveawaysConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)

    # sticky_messages: Dict[str, Any] = Field(default_factory=dict)

# =========================================================
# COLLECTIONS
# =========================================================
class Guild(Document):
    class Settings:
        name = "guilds"

    id: str = Field(alias="_id")  # Guild ID
    premium: PremiumConfig = Field(default_factory=PremiumConfig)
    settings: SettingsConfig = Field(default_factory=SettingsConfig)
    dashboard: DashConfig = Field(default_factory=DashConfig)
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

class StripeEvent(Document):
    """Record of a processed Stripe webhook event, used for idempotency."""

    class Settings:
        name = "stripe_events"

    id: str = Field(alias="_id")  # Stripe event ID (evt_...)
    type: str
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# =========================================================

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
    last_daily: Optional[datetime] = None
    daily_streak: int = 0

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
    channel_name: str
    message_id: str
    author_id: str
    embed_title: str
    embed_desc: str
    embed_color: int = 0x5865f2
    embed_fields: List[EmbedFieldConfig] = Field(default_factory=list)
    end_epoch: float
    end_timestamp: str
    winner_count: int = 1
    participants: List[str] = Field(default_factory=list)
    winners: List[str] = Field(default_factory=list)
    give_xp: Dict[str, Any] = Field(default_factory=dict)
    give_coins: Dict[str, Any] = Field(default_factory=dict)


class Form(Document):
    class Settings:
        name = "forms"

    id: str = Field(alias="_id")
    guild_id: str
    status: bool = True
    name: str
    description: Optional[str]
    questions: List[Dict[str, Any]] = Field(default_factory=list)
    settings: Dict[str, Any] = Field(default_factory=dict)

class FormResponse(Document):
    class Settings:
        name = "form_responses"

    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")  # Auto-generate ID
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

    id: str = Field(alias="_id")
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

    @field_validator("id", mode="before")
    @classmethod
    def _coerce_id(cls, value):
        # Older ticket docs were stored with an ObjectId _id.
        return str(value) if value is not None else value

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

class TempChannel(Document):
    class Settings:
        name = "temp_channels"
        indexes = ["guild_id", "channel_id", "creator_id", "hub_id"]

    guild_id: str
    channel_id: str
    creator_id: str
    hub_id: Optional[str] = None
    index: int = 1


# List of all models to pass to init
ALL_MODELS = [
    Guild,
    Notification,
    StripeEvent,

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