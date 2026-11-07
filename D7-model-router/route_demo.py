"""D7 Model router: one deployment, easy and hard prompts, which model answered and what it cost.

One script, one step per subcommand, so each step can be run and explained on screen:

  python route_demo.py ask       send two easy and two hard prompts to the model router deployment
  python route_demo.py baseline  send the same prompts straight to the shared gpt-5.4-mini deployment
  python route_demo.py trace     one Chat Completions call with the preview routing metadata (mode, attempts)

Keyless (DefaultAzureCredential). Env vars from ../common/demo.env:
FOUNDRY, FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT. Optional: ROUTER_DEPLOYMENT (default model-router).

Cost: copy prices.example.json to prices.json and fill in the prices from the Azure OpenAI
pricing page (per 1 million tokens, in your currency). Without prices.json the script shows tokens only.

Calls follow:
  https://learn.microsoft.com/azure/foundry/openai/how-to/model-router (Foundry Responses, Python)
  https://learn.microsoft.com/azure/foundry/openai/how-to/monitor-model-router (routing metadata)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

HERE = Path(__file__).parent
ROUTER = os.environ.get("ROUTER_DEPLOYMENT", "model-router")
MAX_OUTPUT_TOKENS = 4000  # caps the cost of the hard prompts; reasoning tokens count as output

PROMPTS = [
    ("easy-1", "What is the capital of Sweden? Answer with one word."),
    ("easy-2", "Translate into French: 'Good morning, see you tomorrow.'"),
    (
        "hard-1",
        "Three boxes are labelled 'apples', 'oranges' and 'apples and oranges'. Every label is wrong. "
        "You may take one fruit from one box without looking inside. Which box do you pick from, "
        "and how do you then relabel all three boxes? Explain step by step, briefly.",
    ),
    (
        "hard-2",
        "Train A leaves a station at 09:40, travels 210 km at an average of 84 km/h, waits 12 minutes, "
        "then travels another 95 km at 76 km/h. Train B leaves the same station at 10:05 on the same "
        "route and averages 100 km/h without stopping. Does train B catch up with train A? "
        "If so, at which kilometre and at what time? Show your working briefly.",
    ),
]


def load_prices():
    path = HERE / "prices.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def model_price(prices, served_model):
    """The response names the model with its version, e.g. gpt-5.4-mini-2026-03-17. Longest prefix wins."""
    keys = [k for k in prices["models"] if served_model.startswith(k)]
    return prices["models"][max(keys, key=len)] if keys else None


def cost(prices, served_model, usage, via_router):
    if not prices:
        return None
    p = model_price(prices, served_model)
    if not p or p.get("input") is None or p.get("output") is None:
        return None
    total = (usage["input"] * p["input"] + usage["output"] * p["output"]) / 1_000_000
    if via_router:
        # Learn: model router usage is charged for input prompts at the rate on the pricing page.
        total += usage["input"] * (prices.get("router_input") or 0) / 1_000_000
    return total


def usage_of(response):
    u = response.usage
    details = getattr(u, "output_tokens_details", None)
    return {
        "input": u.input_tokens,
        "output": u.output_tokens,
        "reasoning": getattr(details, "reasoning_tokens", 0) or 0,
    }


def run(deployment, via_router):
    prices = load_prices()
    currency = prices.get("currency", "") if prices else ""
    rows = []
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential) as project_client,
        project_client.get_openai_client() as openai_client,
    ):
        for prompt_id, text in PROMPTS:
            start = time.perf_counter()
            response = openai_client.responses.create(
                model=deployment, input=text, max_output_tokens=MAX_OUTPUT_TOKENS
            )
            seconds = time.perf_counter() - start
            usage = usage_of(response)
            # The "model" field reveals which underlying model was selected.
            c = cost(prices, response.model, usage, via_router)
            rows.append((prompt_id, response.model, usage, seconds, c))
            answer = " ".join((response.output_text or "").split())
            print(f"[{prompt_id}] > {text[:70]}{'...' if len(text) > 70 else ''}")
            print(f"[{prompt_id}]   answered by {response.model}, status {response.status}")
            print(f"[{prompt_id}] < {answer[:200]}{'...' if len(answer) > 200 else ''}\n")

    print(f"{'prompt':<8} {'model':<28} {'in':>6} {'out':>6} {'reason':>7} {'sec':>6} {'cost':>10}")
    for prompt_id, model, u, seconds, c in rows:
        shown = f"{c:.5f}" if c is not None else "-"
        print(f"{prompt_id:<8} {model:<28} {u['input']:>6} {u['output']:>6} {u['reasoning']:>7} {seconds:>6.1f} {shown:>10}")
    totals = [c for *_, c in rows if c is not None]
    if len(totals) == len(rows):
        print(f"Total: {sum(totals):.5f} {currency}".rstrip())
    else:
        print("Cost: fill in prices.json (see prices.example.json) to see it per prompt.")


def ask():
    print(f"Deployment: {ROUTER} (model router)\n")
    run(ROUTER, via_router=True)


def baseline():
    chat = os.environ["CHAT_DEPLOYMENT"]
    print(f"Deployment: {chat} (one fixed model, no router)\n")
    run(chat, via_router=False)


def trace():
    # Preview: per-request routing metadata, Chat Completions only, opt in with the
    # Foundry-Features header. Learn's sample uses an API key; this uses Entra ID instead.
    from openai import AzureOpenAI

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        azure_endpoint=f"https://{os.environ['FOUNDRY']}.openai.azure.com",
        azure_ad_token_provider=token_provider,
        api_version="2024-10-21",
        default_headers={"Foundry-Features": "ModelRouterControls=V1Preview"},
    )
    prompt_id, text = PROMPTS[3]
    response = client.chat.completions.create(
        model=ROUTER,
        messages=[{"role": "user", "content": text}],
    )
    u = response.usage
    print(f"[{prompt_id}] Usage: {u.prompt_tokens} prompt + {u.completion_tokens} completion = {u.total_tokens} total tokens")
    print(f"Routed to model: {response.model}")
    print("--- Model Selection Details ---")
    # Optional during preview: parse defensively, as Learn does.
    model_selection_details = getattr(response, "model_selection_details", None)
    if not model_selection_details:
        print("No model selection details were returned.")
        return
    model_router_details = model_selection_details.get("model_router_details", {})
    print(f"Routing mode: {model_router_details.get('mode', 'unknown')}")
    routing_trace = model_router_details.get("routing_trace", [])
    if not routing_trace:
        print("No routing trace was returned.")
    for decision_number, routing_decision in enumerate(routing_trace, start=1):
        latency_ms = routing_decision.get("latency_ms")
        latency = f"{latency_ms} ms" if latency_ms is not None else "not reported"
        print(f"Routing decision {decision_number} (latency: {latency})")
        for attempt_number, attempt in enumerate(routing_decision.get("attempts", []), start=1):
            result = attempt.get("result", {})
            status = result.get("status", "unknown")
            outcome = "selected" if isinstance(status, int) and 200 <= status < 300 else "failed"
            print(f"  Attempt {attempt_number}: {attempt.get('model', 'unknown')} - HTTP {status} ({outcome})")
            error = result.get("error")
            if error:
                print(f"    Error: {error.get('code', 'unknown')} - {error.get('message', 'No message')}")


STEPS = {"ask": ask, "baseline": baseline, "trace": trace}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=STEPS)
    STEPS[parser.parse_args().step]()
    sys.exit(0)
