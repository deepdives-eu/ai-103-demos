"""D6 Memory across sessions: Foundry Agent Service memory (preview).

One script, one step per subcommand, so each step can be run and explained on screen:

  python memory_demo.py setup       create the memory store and a prompt agent with the memory search tool
  python memory_demo.py tell        Alice, conversation 1: state a preference, wait until it is stored
  python memory_demo.py recall      Alice, conversation 2: a new conversation that uses the preference
  python memory_demo.py other-user  Bob asks the same question and gets nothing from Alice's memory
  python memory_demo.py list        list the stored memory items per user scope
  python memory_demo.py forget      explicit forget command, then list again
  python memory_demo.py delete-item delete one memory item by ID (the admin route)
  python memory_demo.py cleanup     delete the agent and the memory store

Keyless (DefaultAzureCredential). Env vars from ../common/demo.env:
FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT, EMBED_DEPLOYMENT.

Every call follows https://learn.microsoft.com/azure/foundry/agents/how-to/memory-usage (Python).
"""

import argparse
import os
import sys
import time
from datetime import timedelta

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemorySearchPreviewTool,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential

MEMORY_STORE = "d6_memory_store"
AGENT_NAME = "d6-memory-agent"
USERS = ("alice", "bob")  # sent as x-memory-user-id; with scope {{$userId}} each user gets their own memory

PREFERENCE = "I'm vegetarian, and I really don't like mushrooms."
QUESTION = "Suggest one dinner I could cook tonight."
FORGET = "Forget that I don't like mushrooms."

project_client = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
)
CHAT = os.environ["CHAT_DEPLOYMENT"]
EMBED = os.environ["EMBED_DEPLOYMENT"]


def ask(user, text):
    """One turn in a brand-new conversation, as `user`."""
    openai_client = project_client.get_openai_client()
    conversation = openai_client.conversations.create()
    response = openai_client.responses.create(
        input=text,
        conversation=conversation.id,
        extra_body={"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
        extra_headers={"x-memory-user-id": user},
    )
    print(f"[{user}] conversation {conversation.id}")
    print(f"[{user}] > {text}")
    print(f"[{user}] < {response.output_text}")
    print(f"[{user}]   output items: {[getattr(i, 'type', '?') for i in response.output]}")
    return response


def list_items(scope):
    items = list(project_client.beta.memory_stores.list_memories(name=MEMORY_STORE, scope=scope))
    print(f"scope '{scope}': {len(items)} memory item(s)")
    for item in items:
        print(f"  - {item.memory_id} [{item.kind}]: {item.content}")
    return items


def setup():
    options = MemoryStoreDefaultOptions(
        user_profile_enabled=True,
        # Only user profile memory for this demo: fewer extraction calls, fewer tokens.
        chat_summary_enabled=False,
        procedural_memory_enabled=False,
        default_ttl_seconds=timedelta(days=1),  # Learn passes a timedelta here; 0 means no expiry
        user_profile_details="Food and drink preferences. Avoid sensitive data such as age, "
        "financials, precise location and credentials.",
    )
    store = project_client.beta.memory_stores.create(
        name=MEMORY_STORE,
        definition=MemoryStoreDefaultDefinition(chat_model=CHAT, embedding_model=EMBED, options=options),
        description="D6 demo, delete after the demo",
    )
    print(f"Memory store: {store.name}")

    tool = MemorySearchPreviewTool(
        memory_store_name=MEMORY_STORE,
        scope="{{$userId}}",  # resolved per call from the x-memory-user-id header
        update_delay=1,  # seconds of inactivity before memory is written; default 300
    )
    agent = project_client.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=CHAT,
            instructions="You are a cooking assistant. Answer in at most two sentences. "
            "Use what you know about the user.",
            tools=[tool],
        ),
    )
    print(f"Agent: {agent.name}, version {agent.version}")


def tell():
    ask(USERS[0], PREFERENCE)
    # update_delay is only the debounce; extraction itself can take about a minute.
    print("Waiting for the memory to be written", end="", flush=True)
    for _ in range(24):  # up to 2 minutes
        time.sleep(5)
        print(".", end="", flush=True)
        if list(project_client.beta.memory_stores.list_memories(name=MEMORY_STORE, scope=USERS[0])):
            print()
            list_items(USERS[0])
            return
    print("\nNothing stored yet. Run `list` again in a minute.")


def recall():
    ask(USERS[0], QUESTION)


def other_user():
    ask(USERS[1], QUESTION)


def list_all():
    for user in USERS:
        list_items(user)


def forget():
    # Direct remember-or-forget command, exactly as Learn shows it: the memory search tool
    # inline on a Responses call with an explicit scope. Applied immediately, no update delay.
    openai_client = project_client.get_openai_client()
    tools = [{"type": "memory_search_preview", "memory_store_name": MEMORY_STORE, "scope": USERS[0]}]
    response = openai_client.responses.create(model=CHAT, tools=tools, input=FORGET)
    print(f"> {FORGET}")
    for item in response.output:
        if getattr(item, "type", None) == "memory_command_call":
            print(f"  {item.type} {item.arguments} {item.status}")
    print(f"< {response.output_text}")
    list_items(USERS[0])


def delete_item():
    items = list_items(USERS[0])
    if not items:
        return
    project_client.beta.memory_stores.delete_memory(name=MEMORY_STORE, memory_id=items[0].memory_id)
    print(f"Deleted {items[0].memory_id}")
    list_items(USERS[0])


def cleanup():
    try:
        project_client.agents.delete(agent_name=AGENT_NAME)  # the agent and all its versions
        print(f"Deleted agent {AGENT_NAME}")
    except Exception as e:  # keep going so the store is deleted too
        print(f"Agent: {e}")
    result = project_client.beta.memory_stores.delete(MEMORY_STORE)
    print(f"Deleted memory store {MEMORY_STORE}: {result.deleted}")


STEPS = {
    "setup": setup,
    "tell": tell,
    "recall": recall,
    "other-user": other_user,
    "list": list_all,
    "forget": forget,
    "delete-item": delete_item,
    "cleanup": cleanup,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=STEPS)
    STEPS[parser.parse_args().step]()
    sys.exit(0)
