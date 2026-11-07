# D9 Text analysis with a model

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video "Text and speech: what the exam adds" in the AI-103 playlist.

**Goal:** turn four short customer messages into sentiment, tone, entities, topics and a one-line summary, in a JSON schema the model has to follow, with structured outputs through the Responses API.

## Exam skill

AI-103, "Implement text analysis solutions (10–15%)" > "Apply language model text analysis":

> Implement solutions to extract entities, topics, summaries, and structured JSON outputs by using generative prompting and Foundry Tools

> Configure detection of sentiment, tone, safety issues, and sensitive content

This demo covers the generative-prompting half of both bullets. It does not cover safety issues. The Foundry Tools half, Azure Language, is not part of this demo either.

## What it costs and why

Tokens only, nothing billed by the hour. Three model calls (steps 2 and 3: one in step 2, two in step 3), each with four short messages in and a small JSON answer out. Step 4 runs locally and costs nothing.

What drives the cost:

- **Input tokens:** the instructions plus the four messages, sent once per call.
- **Output tokens:** the JSON answer. gpt-5.4-mini is a reasoning model, and reasoning tokens are billed as output tokens even though you don't see them. The scripts set `reasoning={"effort": "low"}` and print the token counts after each call, so you can see the cost on screen.
- **Retries:** every re-run is a new call. Step 4 is offline, so run it as often as you like.

The total is small for your subscription. gpt-5.4-mini is a model sold directly by Azure, deployed as Global Standard (pay per token) by `../common/setup.sh`. No Marketplace model, no provisioned throughput (PTU).

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini` version 2026-03-17, Global Standard), and `../common/demo.env` filled in.
- `az login` with the account that has **Foundry User** on the project (setup.sh assigns it). No keys.
- Python 3.10 or later.

## Setup

```bash
cd D9-llm-text-analysis
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
python step4_local_check.py      # offline smoke test of the Pydantic install
```

## Files

| File | What it is |
| --- | --- |
| `messages.json` | Four made-up customer messages. msg-02 has mixed sentiment, msg-03 has fake personal data (example.com email, all-zero phone number, the well-known 4111 test card number, a made-up address) |
| `analysis_model.py` | The Pydantic model: `MessageAnalysis` inside `MessageBatch` |
| `message_analysis.schema.json` | The same schema written out by hand as JSON Schema |
| `common.py` | Client from the Foundry project, the instructions, status and refusal check, token printout |
| `step1_pydantic.py` | `responses.parse` with `text_format=MessageBatch` |
| `step2_json_schema.py` | `responses.create` with `text.format` of type `json_schema`, `strict: true`. `--ask-for-extra` is step 3 |
| `step4_local_check.py` | Offline: Pydantic rejecting an answer with a field the schema forbids |

## Steps

### 1. The messages and the schema (no call yet)

Open `messages.json`, then `analysis_model.py`.

The four messages are made up. The second one is mixed: a nice driver, a broken grinder. The third one is full of personal data, all fake.

For each message the model returns: sentiment from a fixed list, tone from a fixed list, entities, topics, an order number, a yes or no for personal data, and a one-line summary.

Look at the order number. It is not optional, it is string or null. With structured outputs every field must be required. If a value can be missing, you allow null.

### 2. Pydantic and `responses.parse`

Read the call in `step1_pydantic.py`, then run:

```bash
python step1_pydantic.py
```

The client comes from the Foundry project. No key, no API version. `responses.parse` takes your Pydantic model as `text_format`. The SDK turns the class into a JSON schema and sends it along. What comes back in `output_parsed` is a Python object, not a string you have to parse. The call asks for low reasoning effort: this is classification, not a maths problem, and reasoning tokens are billed as output.

Expected output, one block per message, along these lines (the wording will differ per run):

```text
msg-02  sentiment=mixed  tone=friendly, frustrated, impatient
  topics:   product defect, delivery, repeat issue
  entities: coffee grinder (product)
  order:    None   personal data: False
  summary:  Customer praises the driver but reports a second faulty coffee grinder this year.
```

- msg-01: positive, order `NL-48213`.
- msg-02: mixed, `order_number` null, because the message has no order number. The instruction says to return null and not to guess, and the schema allows null.
- msg-03: `contains_personal_data` true, entities include the fake name, phone, email and address as `person`, `contact_detail` or `location`.
- msg-04: neutral or positive, businesslike, Tampere as a location.

If this step fails, see "If a step fails" below.

### 3. The same schema as raw JSON, and a field the schema doesn't have

Open `message_analysis.schema.json` and the `text={"format": ...}` block in `step2_json_schema.py`. Then run:

```bash
python step2_json_schema.py
python step2_json_schema.py --ask-for-extra
```

The JSON file is what the SDK built for you in step 2, written out by hand. It has `additionalProperties: false` on every object, which structured outputs require. The format is type `json_schema`, a name, and `strict: true`. This time you get JSON text back and parse it yourself.

In the second run, the prompt asks for an extra field, `internal_priority`. The schema doesn't have it.

Expected output, both runs, at the end:

```text
msg-01: keys outside the schema: none
msg-02: keys outside the schema: none
msg-03: keys outside the schema: none
msg-04: keys outside the schema: none
```

There is no `internal_priority`. The prompt asked for it, the schema said no, and the schema wins. That is the difference with JSON mode. JSON mode promises valid JSON. Structured outputs promise your schema. If you want a new field, change the schema, not the prompt.

### 4. The same rule in your own code (offline)

```bash
python step4_local_check.py
```

Expected output:

```text
1 validation error for MessageAnalysis
internal_priority
  Extra inputs are not permitted [type=extra_forbidden, ...]

The schema the SDK sends for this model:
False
```

This step does not call Azure. It checks a hand-made answer with the extra field against the same Pydantic model, and Pydantic refuses it. Keep a check like this for JSON that did not come through strict structured outputs: an older JSON-mode call, a file, another service.

### 5. When Azure Language is still the better choice

No code in this step. Look at msg-03 in your output.

The model said there is personal data and listed it. But it did not redact anything, and you can't prove it found everything. Azure Language PII detection is built for that. It gives you redacted text, entity categories, offsets and confidence scores, and you pick the redaction policy: mask characters or replace with the entity type.

PII detection and named entity recognition also stay in Azure Language. Sentiment, key phrases and summarization retire there on 31 March 2029, and Microsoft points you to Foundry models for those. That is what you did in this demo.

## If a step fails

- **gpt-5.4-mini and structured outputs.** The model catalogue lists "Structured outputs" as a capability of `gpt-5.4-mini` (2026-03-17). The "Supported models" list on the structured outputs page doesn't include it yet (it stops at the gpt-5.1 family). If the call is rejected for the schema or the format, check that page again and that your deployment is `gpt-5.4-mini` version 2026-03-17.
- **openai package version.** The structured outputs page says "OpenAI Python 2.x" for `responses.parse`. The Foundry SDK page asks for `openai>=3.0.0` with `azure-ai-projects>=2.3.0`. `requirements.txt` follows the SDK page (the newer requirement). If `responses.parse(text_format=...)` fails or behaves differently from this guide, check the installed versions with `pip list`.
- **Reasoning effort.** Learn says `low` is accepted by all reasoning models except o1-mini. It doesn't list per-model defaults for gpt-5.4-mini, so `low` is set explicitly.
- **Instructions in the input.** The task and the messages go in one text `input`, the same shape as the Learn samples. The scripts don't use a developer or system message or the `instructions` parameter, because there is no Learn sample for them with the Responses API.
- **Step 4 error text.** The expected output comes from Pydantic 2 behaviour (`extra="forbid"`), not from Learn. The exact wording can differ between Pydantic versions. The step is offline, so you can re-run it for free.

## Cleanup

Nothing to delete for D9. It adds no resources: it only calls the existing `gpt-5.4-mini` deployment in the shared project. Leave `rg-ai103-demos` in place if you want to run the other demos. Delete `.venv` locally if you like.

## Sources

Microsoft Learn:

- Structured outputs (Responses API in Python, `text.format`, schema rules, JSON mode difference): https://learn.microsoft.com/azure/foundry/openai/how-to/structured-outputs
- Responses API: https://learn.microsoft.com/azure/foundry/openai/how-to/responses
- Raw JSON schema with `responses.create` in Python (`text={"format": {"type": "json_schema", ...}}`): https://learn.microsoft.com/azure/developer/ai/how-to/azure-openai-to-responses
- Foundry SDK, `project.get_openai_client()`, `azure-ai-projects>=2.3.0`, `openai>=3.0.0`, Python 3.10+, Foundry User role, Azure Language features continuing and retiring on 31 March 2029: https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview?pivots=programming-language-python
- gpt-5.4-mini capabilities (Responses API, structured outputs): https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure#gpt-54
- Reasoning tokens billed as output, reasoning effort values, `output_tokens_details.reasoning_tokens`: https://learn.microsoft.com/azure/foundry/openai/how-to/reasoning
- Azure Language PII detection and redaction policies: https://learn.microsoft.com/azure/ai-services/language-service/personally-identifiable-information/how-to/redact-text-pii
- Sentiment analysis retirement on 31 March 2029: https://learn.microsoft.com/azure/ai-services/language-service/sentiment-opinion-mining/overview
- AI-103 study guide: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Other:

- Pydantic `extra="forbid"` (step 4): https://docs.pydantic.dev/latest/concepts/models/#extra-data

Checked against Learn on 2026-11-07.
