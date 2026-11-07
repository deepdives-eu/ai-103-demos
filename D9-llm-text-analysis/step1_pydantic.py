"""Step 1: structured outputs with a Pydantic model and responses.parse."""
from analysis_model import MessageBatch
from common import (MAX_OUTPUT_TOKENS, REASONING, build_input, check_finished,
                    deployment, get_openai_client, load_messages, print_usage)

openai = get_openai_client()

response = openai.responses.parse(
    model=deployment(),
    input=build_input(load_messages()),
    text_format=MessageBatch,          # the SDK turns this into a strict JSON schema under text.format
    reasoning=REASONING,
    max_output_tokens=MAX_OUTPUT_TOKENS,
)
check_finished(response)

batch: MessageBatch = response.output_parsed   # a real Python object, not a string
for a in batch.analyses:
    print(f"\n{a.message_id}  sentiment={a.sentiment}  tone={', '.join(a.tone)}")
    print(f"  topics:   {', '.join(a.topics)}")
    print(f"  entities: {', '.join(f'{e.text} ({e.category})' for e in a.entities)}")
    print(f"  order:    {a.order_number}   personal data: {a.contains_personal_data}")
    print(f"  summary:  {a.summary}")

print_usage(response)
