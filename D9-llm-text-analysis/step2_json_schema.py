"""Step 2: the same task with a raw JSON schema and responses.create (text.format).

Run with --ask-for-extra for step 3: the instructions ask for a field the schema doesn't have.
"""
import json
import sys
from pathlib import Path

from common import (MAX_OUTPUT_TOKENS, REASONING, build_input, check_finished,
                    deployment, get_openai_client, load_messages, print_usage)

schema = json.loads((Path(__file__).parent / "message_analysis.schema.json").read_text())

extra = ""
if "--ask-for-extra" in sys.argv:
    extra = "Also add a field called internal_priority with the value high, medium or low to every analysis."
    print(f"Extra instruction: {extra}\n")

openai = get_openai_client()
response = openai.responses.create(
    model=deployment(),
    input=build_input(load_messages(), extra),
    text={
        "format": {
            "type": "json_schema",
            "name": "message_analysis",
            "strict": True,
            "schema": schema,
        }
    },
    reasoning=REASONING,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)
check_finished(response)

result = json.loads(response.output_text)   # plain JSON text: you parse it yourself
print(json.dumps(result, indent=2, ensure_ascii=False))

allowed = set(schema["properties"]["analyses"]["items"]["properties"])
for a in result["analyses"]:
    unexpected = set(a) - allowed
    print(f"{a['message_id']}: keys outside the schema: {sorted(unexpected) or 'none'}")

print_usage(response)
