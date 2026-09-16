from beanie import Document
from bson import ObjectId
from pydantic import Field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .core import DictModel

# ---------------------------------------------------------
# Forms plugin
# ---------------------------------------------------------
class FormsConfig(DictModel):
    status: bool = False

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
