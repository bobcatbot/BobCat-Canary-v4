import discord
from beanie import Document
from pydantic import ConfigDict, Field, BaseModel, field_validator
from datetime import datetime, timezone
from typing import Optional, List, Any

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
# IMPORTANT: these imports must stay here, after the shared classes above
# and before DashConfig below - not hoisted to the top of the file. `core`
# and each plugin file import from each other (plugin files need EmbedConfig
# etc. from `core`; `core.DashConfig` needs every plugin's top-level config
# class), so this only resolves if DictModel/EmbedConfig/etc. are already
# defined on this module before a plugin file's `from .core import ...`
# runs. An import-sorter/formatter WILL try to move this to the top -
# don't let it, that reintroduces the circular-import failure.
# ---------------------------------------------------------
from .welcome import WelcomeConfig
from .moderation import ModerationConfig
from .verification import VerificationConfig
from .starboard import StarboardConfig
from .forms import FormsConfig
from .temporary_channels import TemporaryChannelsConfig
from .ticketing import TicketingConfig
from .stats import StatsConfig
from .leveling import LevelingConfig
from .birthdays import BirthdaysConfig
from .giveaways import GiveawaysConfig
from .economy import EconomyConfig

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
