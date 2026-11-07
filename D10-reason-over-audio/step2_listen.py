"""Step 2: one call to the audio model. The audio goes in, the analysis comes out as text.

gpt-audio and gpt-audio-mini don't support structured outputs, so the schema goes in the
prompt and we check the answer ourselves with the same Pydantic model.
"""
import json
import os

from pydantic import ValidationError

from call_analysis import CallAnalysis
from common import AUDIO_API_VERSION, INSTRUCTIONS, azure_openai, call_wav_base64, print_chat_usage, save

schema = json.dumps(CallAnalysis.model_json_schema())
client = azure_openai(AUDIO_API_VERSION)

completion = client.chat.completions.create(
    model=os.environ["AUDIO_DEPLOYMENT"],          # no modalities or audio: the answer is text only
    messages=[{
        "role": "user",
        "content": [
            {"type": "text",
             "text": f"{INSTRUCTIONS} Listen to how things are said, not only what is said. "
                     f"Answer with one JSON object that matches this JSON schema, and nothing else:\n{schema}"},
            {"type": "input_audio",
             "input_audio": {"data": call_wav_base64(), "format": "wav"}},
        ],
    }],
)

raw = completion.choices[0].message.content.strip()
if raw.startswith("```"):                           # the model may wrap JSON in a code fence
    raw = raw.strip("`").removeprefix("json").strip()

try:
    analysis = CallAnalysis.model_validate_json(raw)
except ValidationError as e:
    save("step2_raw.txt", raw)
    raise SystemExit(f"The answer doesn't match the schema (saved in out/step2_raw.txt):\n{e}")

print(json.dumps(analysis.model_dump(), indent=2, ensure_ascii=False))
print(f"\nSaved {save('step2_audio.json', analysis.model_dump())}")
print_chat_usage(completion)
