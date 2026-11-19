"""D3 Keyless by default: the same model call with an API key and with Microsoft Entra ID.

One script, one call per subcommand, so each step can be run and explained on screen:

  python auth_demo.py key              Responses call with the resource's API key (env FOUNDRY_KEY)
  python auth_demo.py keyless          the same call with DefaultAzureCredential, twice:
                                       on the resource's OpenAI v1 endpoint and through the Foundry project
  python auth_demo.py key --until denied     repeat the key call every 20 s until the service refuses it
  python auth_demo.py keyless --until ok     repeat the keyless call until it works again (role propagation)

The key is never printed. Env vars from ../common/demo.env: FOUNDRY, FOUNDRY_PROJECT_ENDPOINT,
CHAT_DEPLOYMENT. FOUNDRY_KEY only for `key`; README step 2 sets it in your shell, not in a file.

Clients follow Microsoft Learn:
  key and keyless on /openai/v1/: https://learn.microsoft.com/azure/foundry/openai/how-to/responses#generate-a-text-response
  both v1 host names:             https://learn.microsoft.com/azure/foundry/openai/api-version-lifecycle#code-changes
  keyless through the project:    https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview
  error handling:                 https://learn.microsoft.com/azure/foundry/openai/supported-languages?pivots=programming-language-python#error-handling
"""

import argparse
import os
import sys
import time

import openai
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

# Learn: base_url accepts <resource>.openai.azure.com and <resource>.services.ai.azure.com.
# https://learn.microsoft.com/azure/foundry/openai/api-version-lifecycle#code-changes
# The demo uses services.ai.azure.com: in the 19 November 2026 dry run, openai.azure.com kept
# answering a token whose Foundry User role had been removed, services.ai.azure.com refused it.
BASE_URL = f"https://{os.environ['FOUNDRY']}.services.ai.azure.com/openai/v1/"
MODEL = os.environ["CHAT_DEPLOYMENT"]
PROMPT = "In one short sentence: why should production apps avoid API keys?"
# gpt-5.4-mini is a reasoning model; low effort and a token cap keep each call cheap.
CALL = dict(model=MODEL, input=PROMPT, reasoning={"effort": "low"}, max_output_tokens=500)
POLL_SECONDS = 20
# On a laptop DefaultAzureCredential gets the token from `az`, which can take longer than the default 10 s.
AZ_TIMEOUT = 30


def key_client():
    key = os.environ.get("FOUNDRY_KEY")
    if not key:
        raise SystemExit("FOUNDRY_KEY is not set. Run README step 2 first.")
    return OpenAI(api_key=key, base_url=BASE_URL)


def keyless_client():
    # Learn passes the token provider itself, so the client refreshes the token when it expires.
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(process_timeout=AZ_TIMEOUT), "https://ai.azure.com/.default"
    )
    return OpenAI(base_url=BASE_URL, api_key=token_provider)


def project_client():
    project = AIProjectClient(
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(process_timeout=AZ_TIMEOUT),
    )
    return project.get_openai_client()


def call(label, client):
    """One Responses call. Returns True if it worked, False if the service refused it."""
    try:
        response = client.responses.create(**CALL)
    except openai.APIStatusError as e:
        print(f"[{label}] refused: HTTP {e.status_code}: {e.message}")
        return False
    print(f"[{label}] OK ({response.usage.total_tokens} tokens): {response.output_text}")
    return True


def run(calls, until, minutes):
    """Run the calls once, or repeat them until every call is `ok` or every call is `denied`."""
    deadline = time.time() + minutes * 60
    # One client per endpoint for the whole run, so a repeat reuses the token instead of asking `az` again.
    clients = [(label, make()) for label, make in calls]
    while True:
        results = [call(label, client) for label, client in clients]
        if until is None:
            return
        if (until == "ok" and all(results)) or (until == "denied" and not any(results)):
            print(f"Reached '{until}'.")
            return
        if time.time() > deadline:
            print(f"Not '{until}' after {minutes} minutes. Propagation can take longer; run it again later.")
            sys.exit(1)
        print(f"  waiting {POLL_SECONDS} s ...", flush=True)
        time.sleep(POLL_SECONDS)


STEPS = {
    "key": [("api key, /openai/v1", key_client)],
    "keyless": [("Entra ID, /openai/v1", keyless_client), ("Entra ID, project", project_client)],
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=STEPS)
    parser.add_argument("--until", choices=("ok", "denied"), help="repeat every 20 s until this state")
    parser.add_argument("--minutes", type=int, default=15, help="give up after this many minutes (default 15)")
    args = parser.parse_args()
    run(STEPS[args.step], args.until, args.minutes)
