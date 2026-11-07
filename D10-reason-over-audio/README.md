# D10 Reason over audio

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video "Text and speech: what the exam adds" in the AI-103 playlist.

**Goal:** send a short support call recording to an audio model and get a summary, the caller's sentiment and tone, and the action items back in one call. Then do the same with two steps, transcribe first and analyse the text after, and compare what each route can see.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Implement text analysis solutions > Implement speech solutions: "Enable multimodal reasoning from audio inputs"
- Implement text analysis solutions > Implement speech solutions: "Implement workflows to convert speech to text and text to speech for agentic interactions"
- Implement text analysis solutions > Apply language model text analysis: "Configure detection of sentiment, tone, safety issues, and sensitive content"
- Plan and manage an Azure AI solution > Choose the appropriate Foundry services for generative AI and agents: "Choose an appropriate model for each task, including large language models (LLMs), small language models, multimodal models, and Foundry Tools"

This demo covers sentiment and tone from speech. It does not cover safety issues or sensitive content, and it doesn't use Azure Speech.

**Preview.** `gpt-4o-mini-transcribe` is marked preview in the model catalogue. `gpt-audio-mini` is not.

## What it costs and why

Tokens only, nothing billed by the hour. The recording is about a minute long.

What drives the cost:

- **Step 1, making the recording:** ten short calls to `gpt-audio-mini`, one per line of the script, each with a little text in and a few seconds of audio out. This is the only step that generates audio, and it's the step with the most calls. If you re-run the analysis, reuse `out/call.wav` instead of making a new one. `python make_call.py --say` (macOS) costs nothing.
- **Step 2, listening:** one call to `gpt-audio-mini` with about a minute of audio in and a small JSON answer out, as text only. The script prints the input tokens and how many of them are audio.
- **Step 3, transcribe then analyse:** one transcription of the same minute with `gpt-4o-mini-transcribe`, then one `gpt-5.4-mini` call with the transcript in and a small JSON answer out. `gpt-5.4-mini` is a reasoning model and reasoning tokens are billed as output tokens; the script sets `reasoning={"effort": "low"}`.
- **Step 4** runs locally and costs nothing.

For current prices per token and per audio token, see the Azure OpenAI pricing page linked under Sources. All three models are sold directly by Azure and deployed as Global Standard (pay per token). No Marketplace model, no provisioned throughput (PTU).

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini` version 2026-03-17, Global Standard), and `../common/demo.env` filled in.
- `az login` with an account that can create deployments and role assignments on the shared resource.
- Python 3.10 or later.
- Optional, macOS only: the built-in `say` and `afplay` commands, to make the recording offline and to listen to it.

## Setup

```bash
cd D10-reason-over-audio
./setup.sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; source out/d10.env; set +a
```

`setup.sh` adds two Global Standard deployments to the shared Foundry resource: `gpt-audio-mini` version 2025-12-15 and `gpt-4o-mini-transcribe` version 2025-12-15. Learn lists both as Global Standard in Sweden Central. It also gives you **Cognitive Services OpenAI User** on the resource, because the audio and transcription calls go to the resource's Azure OpenAI endpoint with your Entra ID token, not through the project. It writes `out/d10.env` with the endpoint and deployment names.

**If your shared resource is in another region.** `setup.sh` first asks Azure whether `gpt-audio-mini` 2025-12-15 is offered as Global Standard in `LOCATION`. If it isn't, the script creates a second, small Foundry resource named `<FOUNDRY>-d10` in its own resource group `rg-ai103-d10`, in `AUDIO_FALLBACK_LOCATION` (default `eastus2`, where Learn lists both models as Global Standard), and deploys there. Step 3 still uses `gpt-5.4-mini` in the shared project. `./cleanup.sh` deletes `rg-ai103-d10` completely. A Foundry resource costs nothing while idle. Set `AUDIO_USE_SHARED=1` to skip the check.

Role assignments can take a few minutes to apply. If the first call fails with 401 or 403, wait and try again.

## Files

| File | What it is |
| --- | --- |
| `call_script.json` | A made-up support call: ten lines, agent and caller, with a tone direction per line. The words stay polite; the tone carries the frustration |
| `make_call.py` | Step 1: speaks every line with `gpt-audio-mini` (two voices) and joins them into `out/call.wav`. `--say` uses macOS `say` instead |
| `call_analysis.py` | The Pydantic model: summary, order number, sentiment at start and end, tone, tone evidence, action items |
| `common.py` | Clients (keyless), the instructions, token printout |
| `step2_listen.py` | One chat completions call with an `input_audio` part. Schema in the prompt, checked locally |
| `step3_transcribe_then_analyse.py` | `audio.transcriptions.create`, then `responses.parse` with the same Pydantic model as a strict schema |
| `step4_compare.py` | Offline: both answers side by side |
| `setup.sh`, `cleanup.sh` | The two deployments and the role, and removing them |

## Steps

### 1. Make the recording

```bash
python make_call.py
afplay out/call.wav        # macOS; on other systems open the file in any player
```

We can't ship a real customer call, and this repo doesn't download audio, so the script makes one. `gpt-audio-mini` can take text in and give text and audio out. Each line from `call_script.json` goes in with a voice (`ash` for the agent, `coral` for the caller) and a tone direction: tired, sarcastic, hesitant. The model also returns a transcript of what it said. If that differs from the script line, the script prints a note.

Expected output:

```text
 1/10 agent  Thanks for calling Lumo Home support, this is Alex. How can I help?
 2/10 caller Hi. It's Robin. I'm calling about order LH-20417 again. ...
...
Wrote out/call.wav: 55 seconds, 2.6 MB
```

The length and size will differ a little. Listen to it before you go on. Line 6, "Great. Wonderful.", should sound sarcastic, and line 8 should sound hesitant. If a line sounds wrong, run the script again; each run is ten new paid calls.

If this step fails: a 404 or "deployment not found" means `AUDIO_DEPLOYMENT` or `AZURE_OPENAI_ENDPOINT` isn't loaded (re-run the `source` line). 401 or 403: wait for the role assignment. "Audio chunks differ in format": every chunk should come back in the same WAV format; run again, or use `--say`.

### 2. Let the model listen

Read the call in `step2_listen.py`, then run:

```bash
python step2_listen.py
```

This is the chat completions API with a user message that has two parts: a text part with the instructions, and an `input_audio` part with the WAV file, base64 encoded. There is no `modalities` and no `audio` parameter, so the answer is text only. You don't pay for audio output you don't need.

`gpt-audio` and `gpt-audio-mini` don't support structured outputs. So the JSON schema goes into the prompt as text, and the script checks the answer with the Pydantic model itself. That's the check D9 step 4 recommends for JSON that didn't come through strict structured outputs.

Expected output, along these lines (the wording differs per run):

```text
{
  "summary": "The caller reports that a replacement grinder for order LH-20417 never arrived although the courier marked it delivered. The agent opens a courier claim, sends a new one by express and refunds shipping.",
  "order_number": "LH-20417",
  "caller_sentiment_start": "negative",
  "caller_sentiment_end": "mixed",
  "caller_tone": ["tired", "frustrated", "sarcastic", "hesitant"],
  "tone_evidence": "The caller sighs, answers in short clipped sentences, says 'Great. Wonderful.' in a sarcastic voice and pauses before agreeing to Thursday.",
  "action_items": [
    {"owner": "agent", "task": "Open a claim with the courier", "due": null},
    {"owner": "agent", "task": "Send a replacement by express", "due": "today"},
    {"owner": "agent", "task": "Refund the shipping cost", "due": null},
    {"owner": "agent", "task": "Call the caller to confirm delivery", "due": "Thursday"},
    {"owner": "agent", "task": "Send a confirmation email", "due": "within the hour"}
  ]
}

Tokens: input ..., (of which audio ...), output ...
```

Look at `tone_evidence`. It talks about sighs, pauses and how something was said. Those aren't words in the call.

If this step fails: "The answer doesn't match the schema" means the model's JSON didn't fit. The raw answer is in `out/step2_raw.txt`. Nothing enforced the schema, so this can happen. Run it again. A 400 error about `input_audio` usually means the API version or the deployment is wrong: the script uses `2025-01-01-preview`, the version Learn gives for audio completions, and the deployment must be an audio model.

### 3. Transcribe, then analyse the text

```bash
python step3_transcribe_then_analyse.py
```

Two calls. First `gpt-4o-mini-transcribe` turns the WAV into text, with one `/audio/transcriptions` request for the whole file. Then `gpt-5.4-mini` analyses that text with `responses.parse` and the same Pydantic model as `text_format`, as in D9. This time the schema is enforced: strict structured outputs.

Expected output: the transcript first, one block of text, then the JSON.

```text
Transcript:
Thanks for calling Lumo Home support, this is Alex. How can I help? Hi. It's Robin. I'm calling about order LH-20417 again. ...
```

Look at the transcript before the JSON. There are no speaker labels: among the Azure OpenAI transcription models, Learn lists speaker diarization only for `gpt-4o-transcribe-diarize`. There are no sighs and no pauses. The text model only gets the words.

The facts usually come out the same: order number, the courier claim, the express replacement, the refund, Thursday, the email. The tone often doesn't. A text model can still guess sarcasm from "Great. Wonderful. That's the third time I've heard that." It can't hear the sigh before line 2 or the pause before "Thursday. Okay." Run it and see what you get.

If this step fails: a 404 on the transcription means `TRANSCRIBE_DEPLOYMENT` isn't loaded or the deployment doesn't exist (`az cognitiveservices account deployment list -n $AUDIO_ACCOUNT -g $AUDIO_RG -o table`). For errors in the `responses.parse` part, see "If a step fails" in D9; it's the same call.

### 4. Compare (offline)

```bash
python step4_compare.py
```

No Azure call. It prints the two answers next to each other: sentiment at the start and the end, tone, the number of action items, then the tone evidence and the action items of each.

Expected output, along these lines:

```text
                        LISTENED TO THE AUDIO                   READ THE TRANSCRIPT
order_number            LH-20417                                LH-20417
caller_sentiment_start  negative                                negative
caller_sentiment_end    mixed                                   neutral
caller_tone             tired, frustrated, sarcastic, hesitant  frustrated, sarcastic
action items            5                                       5
...
```

Your columns will differ. What to look for: the action items match, because they're in the words. The tone evidence differs. The audio answer can point at how things were said; the transcript answer can only point at words.

### 5. Which route when

No code in this step.

- **The question is about what was said:** summaries, action items, search, an archive of calls. Transcribe, keep the text, analyse the text. You can store, search and re-analyse the transcript without paying for audio again, and you get strict structured outputs.
- **The question is about how it was said:** tone, hesitation, sarcasm. Send the audio to an audio model, in one call. You lose strict structured outputs with `gpt-audio-mini`, so validate the JSON yourself.
- **You need speaker labels, custom vocabulary or high-volume batch transcription:** look at `gpt-4o-transcribe-diarize` or Azure Speech. Learn's comparison page lists those as cases for Azure Speech.
- **Real-time voice conversation:** that's the Realtime API or Voice Live, not this request and response pattern.

The official course lab for speech (lab 3.3) synthesizes speech with `gpt-4o-mini-tts` and transcribes it with `gpt-4o-mini-transcribe`. It never sends audio to a model to reason about it. This demo fills that gap.

## Cleanup

```bash
./cleanup.sh
```

This deletes the `gpt-audio-mini` and `gpt-4o-mini-transcribe` deployments from the shared resource, or the whole `rg-ai103-d10` resource group if `setup.sh` had to create the fallback resource, and removes `out/` with the recording, the transcript and the answers. The shared project and `gpt-5.4-mini` stay for the other demos. The Cognitive Services OpenAI User role on the shared resource also stays; it costs nothing and D13 uses the same role.

## Notes

- **Two clients.** The audio and transcription calls use `AzureOpenAI` with an `api_version`, exactly as the Learn samples for those calls do. Step 3's text analysis uses the OpenAI client from the Foundry project, as in D9. Both are keyless.
- **Text out only.** The Learn sample asks for `modalities=["text", "audio"]` and reads `message.audio.transcript`. Step 2 leaves out `modalities` and `audio` and reads `message.content`, because a spoken answer isn't needed. Learn's modality table lists audio in, text out as supported.
- **Responses API.** Learn documents audio input for `gpt-audio` models on the chat completions API. The Responses API page doesn't mention audio input, so this demo doesn't use it there.
- **Limits.** The audio completions quickstart gives a maximum audio file size of 20 MB. The transcription models take files up to 25 MB.
- **Voices.** Learn lists these voices for audio out: Alloy, Ash, Ballad, Coral, Echo, Sage, Shimmer, Verse, Marin and Cedar. Change `VOICES` in `make_call.py` to try others.
- **Why not gpt-4o-mini-tts for the recording.** Learn lists `gpt-4o-mini-tts` as Global Standard only in East US 2, so it would need a second resource. `gpt-audio-mini` in Sweden Central can speak text too.
- **The `say` fallback** is a macOS command, not an Azure feature. It's offline and free, but it reads every line in the same neutral voice, so step 4 has less to show.

## Sources

Microsoft Learn:

- Audio completions quickstart, Python (chat completions with `input_audio`, `gpt-audio-mini`, API version `2025-01-01-preview`, voices, 20 MB limit, modality table): https://learn.microsoft.com/azure/foundry/openai/audio-completions-quickstart?pivots=programming-language-python
- Foundry Models sold by Azure, audio models (`gpt-audio`, `gpt-audio-mini`, `gpt-audio-1.5`, transcription models and their preview status, `gpt-4o-mini-tts`): https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure#audio-models
- Region availability, Global Standard (`gpt-audio-mini` 2025-12-15 and `gpt-4o-mini-transcribe` 2025-12-15 in Sweden Central and East US 2; `gpt-4o-mini-tts` in East US 2): https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability?pivots=standard
- Structured outputs ("Currently, structured outputs aren't supported with ... gpt-audio and gpt-audio-mini"): https://learn.microsoft.com/azure/foundry/openai/how-to/structured-outputs
- Speech to text with Azure OpenAI transcription models, Python (`audio.transcriptions.create`, supported formats, 25 MB): https://learn.microsoft.com/azure/foundry/openai/whisper-quickstart?pivots=programming-language-python
- Transcriptions REST reference listing `gpt-4o-mini-transcribe-2025-12-15` (API version `2025-04-01-preview`): https://learn.microsoft.com/azure/foundry/openai/reference-preview#transcriptions---create
- Choose an Azure speech recognition and generation technology (chat completions audio "in a single model call", diarization, when to use Azure Speech): https://learn.microsoft.com/azure/architecture/data-guide/ai-services/speech-recognition-generation
- Role-based access control for Azure OpenAI (Cognitive Services OpenAI User makes inference calls with Entra ID): https://learn.microsoft.com/azure/foundry-classic/openai/how-to/role-based-access-control
- Structured outputs with `responses.parse` and the Foundry SDK client: see the D9 sources.
- Reasoning tokens billed as output, reasoning effort: https://learn.microsoft.com/azure/foundry/openai/how-to/reasoning
- AI-103 study guide: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Other:

- Azure OpenAI pricing: https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/
- The official lab this demo goes beyond (lab 3.3, generative AI speech): https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/03-gen-ai-speech.html

Checked against Learn on 2026-11-07.
