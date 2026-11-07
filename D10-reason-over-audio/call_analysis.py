"""The Pydantic model for one analysed call. Used by step 2 (validated locally) and
step 3 (sent as a strict schema with structured outputs)."""
from typing import Literal

from pydantic import BaseModel, ConfigDict

Sentiment = Literal["positive", "neutral", "negative", "mixed"]


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner: Literal["agent", "caller"]
    task: str
    due: str | None                    # nullable instead of optional: every field must be required


class CallAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    order_number: str | None
    caller_sentiment_start: Sentiment
    caller_sentiment_end: Sentiment
    caller_tone: list[Literal["calm", "friendly", "tired", "frustrated", "sarcastic", "hesitant", "relieved"]]
    tone_evidence: str                 # what in the call shows that tone
    action_items: list[ActionItem]
