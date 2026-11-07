"""Step 1: make the call recording ourselves, out/call.wav. Nothing is downloaded.

Default: the gpt-audio-mini deployment speaks each line of call_script.json (text in,
text + audio out, the "Generate audio from text input" pattern from the Learn quickstart),
with one voice for the agent and another for the caller, and a tone direction per line.
The lines are joined into one WAV with Python's wave module.

  python make_call.py          # gpt-audio-mini, about ten short calls
  python make_call.py --say    # macOS only, offline and free: the built-in `say` command

The `say` version has no tone of voice, so the contrast in step 4 is weaker. Use it when
you only want to test the plumbing.
"""
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from common import AUDIO_API_VERSION, CALL_WAV, HERE, OUT, azure_openai

VOICES = {"agent": "ash", "caller": "coral"}                  # from the voices Learn lists for audio out
SAY_VOICES = {"agent": os.environ.get("SAY_VOICE_AGENT", "Daniel"),
              "caller": os.environ.get("SAY_VOICE_CALLER", "Samantha")}
PAUSE_SECONDS = 0.5

lines = json.loads((HERE / "call_script.json").read_text(encoding="utf-8"))


def speak_with_model(client, line: dict) -> bytes:
    completion = client.chat.completions.create(
        model=os.environ["AUDIO_DEPLOYMENT"],
        modalities=["text", "audio"],
        audio={"voice": VOICES[line["speaker"]], "format": "wav"},
        messages=[{
            "role": "user",
            "content": (
                "You are a voice actor recording one line of a made-up support call. "
                f"Read the line aloud word for word. Tone: {line['tone']}. "
                "Don't add, drop or change any words, and say nothing else.\n\n"
                f"Line: {line['text']}"
            ),
        }],
    )
    audio = completion.choices[0].message.audio
    if audio.transcript.strip().lower() != line["text"].strip().lower():
        print(f"  note: the model said: {audio.transcript!r}")   # check it, re-run if it drifted
    return base64.b64decode(audio.data)


def speak_with_say(line: dict) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "line.wav"
        subprocess.run(["say", "-v", SAY_VOICES[line["speaker"]], "-o", str(path),
                        "--file-format=WAVE", "--data-format=LEI16@24000", line["text"]], check=True)
        return path.read_bytes()


def join(chunks: list[bytes]) -> None:
    params = None
    OUT.mkdir(exist_ok=True)
    with wave.open(str(CALL_WAV), "wb") as out:
        for chunk in chunks:
            with wave.open(io.BytesIO(chunk), "rb") as w:
                p = (w.getnchannels(), w.getsampwidth(), w.getframerate())
                if params is None:
                    params = p
                    out.setnchannels(p[0]); out.setsampwidth(p[1]); out.setframerate(p[2])
                elif p != params:
                    raise SystemExit(f"Audio chunks differ in format: {p} vs {params}")
                out.writeframes(w.readframes(w.getnframes()))
            out.writeframes(b"\x00" * int(params[2] * PAUSE_SECONDS) * params[0] * params[1])


use_say = "--say" in sys.argv
client = None if use_say else azure_openai(AUDIO_API_VERSION)
chunks = []
for i, line in enumerate(lines, 1):
    print(f"{i:2}/{len(lines)} {line['speaker']:6} {line['text']}")
    chunks.append(speak_with_say(line) if use_say else speak_with_model(client, line))
join(chunks)

with wave.open(str(CALL_WAV), "rb") as w:
    seconds = w.getnframes() / w.getframerate()
print(f"\nWrote {CALL_WAV.relative_to(HERE)}: {seconds:.0f} seconds, {CALL_WAV.stat().st_size / 1e6:.1f} MB")
print("Listen to it: afplay out/call.wav (macOS)")
