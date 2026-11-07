"""Shared bits for D10: clients, the instructions, file paths, token printout.

Keyless everywhere: DefaultAzureCredential picks up your `az login`.
- Audio model and transcription: AzureOpenAI on the Foundry resource's Azure OpenAI
  endpoint, exactly as the Learn audio and transcription samples do it.
- Text analysis of the transcript (step 3): the shared gpt-5.4-mini deployment through the
  Foundry project, as in D9.

Env vars: ../common/demo.env (FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT) and out/d10.env,
which ./setup.sh writes (AZURE_OPENAI_ENDPOINT, AUDIO_DEPLOYMENT, TRANSCRIBE_DEPLOYMENT).
"""
import base64
import json
import os
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

HERE = Path(__file__).parent
OUT = HERE / "out"
CALL_WAV = OUT / "call.wav"

# Audio completions were added in 2025-01-01-preview (the version the Learn quickstart uses).
AUDIO_API_VERSION = "2025-01-01-preview"
# The transcription reference that lists gpt-4o-mini-transcribe-2025-12-15.
TRANSCRIBE_API_VERSION = "2025-04-01-preview"

INSTRUCTIONS = (
    "You analyse a recorded customer support call for an online shop. "
    "Two people speak: a support agent and a caller. Refer to them only as 'the agent' and 'the caller'. "
    "Only use facts from the call. If a value is not in the call, return null instead of guessing. "
    "The summary is two sentences for a team lead. "
    "For tone_evidence, say what in the call shows the caller's tone. "
    "List every promise or next step as an action item with its owner and due date."
)

_credential = DefaultAzureCredential()


def azure_openai(api_version: str) -> AzureOpenAI:
    token_provider = get_bearer_token_provider(_credential, "https://ai.azure.com/.default")
    return AzureOpenAI(
        azure_ad_token_provider=token_provider,
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=api_version,
    )


def project_openai():
    """OpenAI client from the Foundry project (Responses API), as in D9."""
    from azure.ai.projects import AIProjectClient
    project = AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=_credential)
    return project.get_openai_client()


def call_wav_base64() -> str:
    if not CALL_WAV.exists():
        raise SystemExit(f"{CALL_WAV} not found. Run step 1 first: python make_call.py")
    return base64.b64encode(CALL_WAV.read_bytes()).decode("utf-8")


def save(name: str, data) -> Path:
    OUT.mkdir(exist_ok=True)
    path = OUT / name
    text = data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False)
    path.write_text(text, encoding="utf-8")
    return path


def print_chat_usage(completion) -> None:
    u = completion.usage
    details = getattr(u, "prompt_tokens_details", None)
    audio_in = getattr(details, "audio_tokens", None) if details else None
    extra = f" (of which audio {audio_in})" if audio_in is not None else ""
    print(f"\nTokens: input {u.prompt_tokens}{extra}, output {u.completion_tokens}")
