"""Shared bits for D9: the OpenAI client from the Foundry project, and the sample messages.

Keyless: DefaultAzureCredential picks up your `az login`. No API key, no api_version.
Env vars come from ../common/demo.env (see README).
"""
import json
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).parent

# Kept short on purpose: this is text classification, not hard reasoning.
# Reasoning tokens are billed as output tokens, so low effort keeps the cost down.
REASONING = {"effort": "low"}
MAX_OUTPUT_TOKENS = 4000

INSTRUCTIONS = (
    "You analyse customer messages for a small online shop. "
    "For every message, return one analysis with the same message_id. "
    "Only use facts that are in the message. "
    "If a value is not in the message, return null instead of guessing. "
    "The summary is one sentence for a support agent."
)


def get_openai_client():
    project = AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    return project.get_openai_client()


def deployment() -> str:
    return os.environ["CHAT_DEPLOYMENT"]


def load_messages() -> list[dict]:
    return json.loads((HERE / "messages.json").read_text(encoding="utf-8"))


def build_input(messages: list[dict], extra_instruction: str = "") -> str:
    """One text input: the task, then the customer messages as JSON (same shape as the Learn samples)."""
    task = INSTRUCTIONS + (" " + extra_instruction if extra_instruction else "")
    return f"{task}\n\nMessages:\n{json.dumps(messages, ensure_ascii=False, indent=2)}"


def check_finished(response) -> None:
    """Stop with a clear message if the response was cut off or refused."""
    if response.status != "completed":
        raise SystemExit(f"Response status {response.status}: {response.incomplete_details}")
    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if content.type == "refusal":
                    raise SystemExit(f"Model refused: {content.refusal}")


def print_usage(response) -> None:
    u = response.usage
    reasoning = u.output_tokens_details.reasoning_tokens if u.output_tokens_details else 0
    print(f"\nTokens: input {u.input_tokens}, output {u.output_tokens} (of which reasoning {reasoning})")
