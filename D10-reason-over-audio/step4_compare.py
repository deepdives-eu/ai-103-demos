"""Step 4: no Azure call. Put the two answers side by side."""
import json

from common import OUT

try:
    a = json.loads((OUT / "step2_audio.json").read_text(encoding="utf-8"))
    t = json.loads((OUT / "step3_transcript_analysis.json").read_text(encoding="utf-8"))
except FileNotFoundError as e:
    raise SystemExit(f"Run steps 2 and 3 first ({e.filename} is missing).")

print(f"{'':24}{'LISTENED TO THE AUDIO':40}READ THE TRANSCRIPT")
for key in ["order_number", "caller_sentiment_start", "caller_sentiment_end", "caller_tone"]:
    av, tv = a[key], t[key]
    av, tv = (", ".join(v) if isinstance(v, list) else str(v) for v in (av, tv))
    print(f"{key:24}{av:40}{tv}")
print(f"{'action items':24}{len(a['action_items']):<40}{len(t['action_items'])}")

for label, d in (("Audio", a), ("Transcript", t)):
    print(f"\n{label}, tone evidence:\n  {d['tone_evidence']}")
    for item in d["action_items"]:
        print(f"  - {item['owner']}: {item['task']} (due: {item['due']})")

print("\nNow open out/step3_transcript.txt: one block of text, no speaker labels, no sighs, no pauses.")
