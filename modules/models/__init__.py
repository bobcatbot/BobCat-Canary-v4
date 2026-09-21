from .core import (
    DictModel,
    EmbedFieldConfig,
    EmbedAuthorConfig,
    EmbedFooterConfig,
    EmbedConfig,
    PremiumConfig,
    SettingsConfig,
    DashConfig,
    Guild,
    Notification,
    StripeEvent,
    Maintenance,
)
from .welcome import (
    MessageConfig,
    WelcomeJoinConfig,
    WelcomeLeaveConfig,
    WelcomeDMConfig,
    WelcomeAutoRolesConfig,
    WelcomeConfig,
)
from .verification import (
    VerificationButtonConfig,
    VerificationMessageConfig,
    VerificationConfig,
)
from .moderation import (
    AntiLinkConfig,
    AntiSpamConfig,
    GhostPingConfig,
    ExcessiveCapsConfig,
    AutoModConfig,
    LoggingEventsConfig,
    ModerationLoggingConfig,
    ActionSettingsConfig,
    BanSettingsConfig,
    MuteSettingsConfig,
    ModerationSettingsConfig,
    ModerationConfig,
    Warning,
)
from .starboard import StarboardConfig, Starboard
from .forms import FormsConfig, Form, FormResponse
from .temporary_channels import (
    HubPermissionsConfig,
    HubConfig,
    TemporaryChannelsConfig,
    TempChannel,
)
from .ticketing import (
    TicketMessageConfig,
    PanelButtonConfig,
    TicketPanelConfig,
    TicketingConfig,
    Ticket,
    TicketMessage,
)
from .stats import StatsCounterConfig, StatsConfig
from .leveling import (
    LevelingLeaderboardConfig,
    LevelingMessageConfig,
    LevelingRoleRewardConfig,
    LevelingRoleRewardsConfig,
    LevelingConfig,
    Leveling,
)
from .birthdays import BirthdaysConfig, Birthday
from .giveaways import GiveawaysConfig, Giveaway
from .economy import ShopItemConfig, EconomyConfig, Economy
from .insights import InsightsDaily

# List of all models to pass to init
ALL_MODELS = [
    Guild,
    Notification,
    StripeEvent,
    Maintenance,

    Warning,
    Economy,
    Leveling,
    Starboard,
    Giveaway,
    Form,
    FormResponse,
    Ticket,
    TicketMessage,
    TempChannel,
    Birthday,
    InsightsDaily,
]
