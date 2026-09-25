from pydantic import Field
from typing import List, Literal
from .core import DictModel

# ---------------------------------------------------------
# Custom Commands plugin
# ---------------------------------------------------------
class CustomCommand(DictModel):
    trigger: str
    match: Literal["exact", "contains", "startswith"] = "exact"
    reply: str

class CustomCommandsConfig(DictModel):
    status: bool = False
    commands: List[CustomCommand] = Field(default_factory=list)
