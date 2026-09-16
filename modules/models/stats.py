from pydantic import Field
from typing import List, Optional
from .core import DictModel

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
