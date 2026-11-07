"""Step 3: the two-step route. Transcribe with gpt-4o-mini-transcribe, then analyse the text
with gpt-5.4-mini and strict structured outputs (responses.parse, as in D9)."""
import json
import os

from call_analysis import CallAnalysis
from common import CALL_WAV, INSTRUCTIONS, TRANSCRIBE_API_VERSION, azure_openai, project_openai, save

# 3a: speech to text. One request for the whole file.
with open(CALL_WAV, "rb") as audio_file:
    transcript = azure_openai(TRANSCRIBE_API_VERSION).audio.transcriptions.create(
        file=audio_file,
        model=os.environ["TRANSCRIBE_DEPLOYMENT"],
    ).text
print("Transcript:\n" + transcript)
save("step3_transcript.txt", transcript)

# 3b: text to analysis. The model only ever sees the transcript.
response = project_openai().responses.parse(
    model=os.environ["CHAT_DEPLOYMENT"],
    input=f"{INSTRUCTIONS}\n\nTranscript:\n{transcript}",
    text_format=CallAnalysis,          # strict JSON schema under text.format
    reasoning={"effort": "low"},
    max_output_tokens=4000,
)
if response.status != "completed":
    raise SystemExit(f"Response status {response.status}: {response.incomplete_details}")

analysis: CallAnalysis = response.output_parsed
print("\n" + json.dumps(analysis.model_dump(), indent=2, ensure_ascii=False))
print(f"\nSaved {save('step3_transcript_analysis.json', analysis.model_dump())}")
u = response.usage
print(f"\nTokens (analysis only): input {u.input_tokens}, output {u.output_tokens}")
