"""Step 4: no Azure call. What the Pydantic model does with an answer that has a field it forbids.

This is the check you'd keep in your own code for JSON that didn't come through strict
structured outputs (an older JSON-mode call, a cached file, another service).
"""
from pydantic import ValidationError

from analysis_model import MessageAnalysis

answer = {
    "message_id": "msg-02",
    "sentiment": "mixed",
    "tone": ["friendly", "impatient"],
    "entities": [{"text": "coffee grinder", "category": "product"}],
    "topics": ["product defect", "delivery"],
    "order_number": None,
    "contains_personal_data": False,
    "summary": "Customer liked the driver but the grinder is faulty again.",
    "internal_priority": "high",          # not in the schema
}

try:
    MessageAnalysis.model_validate(answer)
except ValidationError as e:
    print(e)

print("\nThe schema the SDK sends for this model:")
print(MessageAnalysis.model_json_schema()["additionalProperties"])
