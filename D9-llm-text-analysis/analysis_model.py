"""The Pydantic model for one analysed message. Used by step 1 and by the local check in step 4."""
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    category: Literal["person", "organization", "product", "location", "order_number", "contact_detail", "other"]


class MessageAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: str
    sentiment: Literal["positive", "neutral", "negative", "mixed"]
    tone: list[Literal["appreciative", "calm", "frustrated", "impatient", "urgent", "businesslike", "friendly"]]
    entities: list[Entity]
    topics: list[str]
    order_number: str | None          # nullable instead of optional: every field must be required
    contains_personal_data: bool
    summary: str


class MessageBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analyses: list[MessageAnalysis]
