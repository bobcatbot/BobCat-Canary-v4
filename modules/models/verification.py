from pydantic import Field
from typing import Optional, Any
from .core import DictModel, EmbedConfig

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
