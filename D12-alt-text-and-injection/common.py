"""Shared bits for D12: the OpenAI client from the Foundry project, image input, checks and token printout.

Keyless: DefaultAzureCredential picks up your `az login`. No API key, no api_version.
Env vars come from ../common/demo.env (see README).
"""
import base64
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).parent
IMAGES = HERE / "images"

# Describing an image is not a maths problem. Reasoning tokens are billed as output,
# so low effort keeps the cost down.
REASONING = {"effort": "low"}
MAX_OUTPUT_TOKENS = 4000


def get_openai_client():
    project = AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )
    return project.get_openai_client()


def deployment() -> str:
    return os.environ["CHAT_DEPLOYMENT"]


def image_path(name: str) -> Path:
    path = IMAGES / name
    if not path.exists():
        raise SystemExit(f"{path} not found. Run: python make_images.py")
    return path


def image_part(name: str, detail: str = "auto") -> dict:
    """An input_image content part with the PNG inlined as a base64 data URL (Responses API shape)."""
    b64 = base64.b64encode(image_path(name).read_bytes()).decode("utf-8")
    return {"type": "input_image", "image_url": f"data:image/png;base64,{b64}", "detail": detail}


def user_message(text: str, image: dict) -> list[dict]:
    return [{"role": "user", "content": [{"type": "input_text", "text": text}, image]}]


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
