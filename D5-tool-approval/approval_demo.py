"""D5 Human approval for a tool: an MCP tool with per-tool require_approval.

One script, one step per subcommand, so each step can be run and explained on screen:

  python approval_demo.py setup    create a prompt agent with the Microsoft Learn MCP server as a tool:
                                   search runs without approval, fetch always needs approval
  python approval_demo.py ask      ask a question; a person approves or denies each approval request (y/N)
  python approval_demo.py log      show the local audit log of every decision
  python approval_demo.py cleanup  delete the agent and the local audit log

Run `ask` twice: answer y the first time and n the second, and compare the answers.

Keyless (DefaultAzureCredential). Env vars from ../common/demo.env:
FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT.

The approval loop follows the Python prompt-agent sample in
https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol
(conversation flow, McpApprovalResponse, y/N prompt). The per-tool require_approval shape is from
"Set up the MCP connection" on the same page and the MCPToolRequireApproval / MCPToolFilter SDK reference.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MCPTool,
    MCPToolFilter,
    MCPToolRequireApproval,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from openai.types.responses.response_input_param import McpApprovalResponse

AGENT_NAME = "d5-approval-agent"
SERVER_LABEL = "microsoft_learn"
SERVER_URL = "https://learn.microsoft.com/api/mcp"  # public, no key, no charge
SEARCH = "microsoft_docs_search"  # finds pages: no approval
FETCH = "microsoft_docs_fetch"  # reads a whole page: a person decides
MAX_ROUNDS = 5  # stop after this many approval rounds, so a confused agent can't loop forever

QUESTION = (
    "In Foundry Agent Service, how do I make only some tools of an MCP server require approval? "
    "Search first, then read the most relevant page in full before you answer."
)

LOG = Path(__file__).parent / "out" / "approvals.jsonl"

project = AIProjectClient(
    endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    credential=DefaultAzureCredential(),
    allow_preview=True,  # as in the Learn MCP sample
)
CHAT = os.environ["CHAT_DEPLOYMENT"]


def setup():
    tool = MCPTool(
        server_label=SERVER_LABEL,
        server_url=SERVER_URL,
        # Tool-access control: the agent sees only these two tools. Learn: an empty list allows all tools.
        allowed_tools=[SEARCH, FETCH],
        # Approval per tool. Without this the default is "always" for every tool.
        require_approval=MCPToolRequireApproval(
            never=MCPToolFilter(tool_names=[SEARCH]),
            always=MCPToolFilter(tool_names=[FETCH]),
        ),
    )
    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=CHAT,
            instructions=(
                "You answer questions about Microsoft Foundry with the Microsoft Learn tools. "
                f"Use {SEARCH} first, then {FETCH} on the best page. "
                "If a tool call is denied, don't ask for it again. Answer from what you have, "
                "and say that you couldn't read the full page. "
                "Keep answers under 80 words and name the URL you used."
            ),
            tools=[tool],
        ),
    )
    print(f"Agent: {agent.name}, version {agent.version}")
    print("MCP tool as sent to the service:")
    print(json.dumps(tool.as_dict(), indent=2))


def log_decision(conversation_id, item, approved, reason):
    LOG.parent.mkdir(exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "conversation": conversation_id,
        "server": item.server_label,
        "tool": getattr(item, "name", None),
        "arguments": getattr(item, "arguments", None),
        "approved": approved,
        "reason": reason,
        "decided_by": os.environ.get("USER", "unknown"),
    }
    with LOG.open("a") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def show(response):
    """Print the MCP items in a response, so you can see what ran with and without approval."""
    for item in response.output:
        kind = getattr(item, "type", "?")
        if kind == "mcp_list_tools":
            names = [t.name for t in getattr(item, "tools", []) or []]
            print(f"  mcp_list_tools  {item.server_label}: {names}")
        elif kind == "mcp_call":
            error = getattr(item, "error", None)
            print(f"  mcp_call        {item.name} {'error: ' + str(error) if error else 'ran'}")
        elif kind == "mcp_approval_request":
            print(f"  mcp_approval_request  {item.name} (waiting for a person)")


def ask():
    with project.get_openai_client(agent_name=AGENT_NAME) as openai:
        conversation = openai.conversations.create()
        print(f"Conversation {conversation.id}")
        print(f"> {QUESTION}")
        response = openai.responses.create(conversation=conversation.id, input=QUESTION)
        show(response)

        for _ in range(MAX_ROUNDS):
            requests = [i for i in response.output if i.type == "mcp_approval_request" and i.id]
            if not requests:
                break
            answers = []
            for item in requests:
                print("\nApproval requested")
                print(f"  Server:    {item.server_label}")
                print(f"  Tool:      {getattr(item, 'name', '<unknown>')}")
                print(f"  Arguments: {json.dumps(getattr(item, 'arguments', None), default=str)}")
                approved = input("Approve this MCP tool call? (y/N): ").strip().lower() == "y"
                reason = None
                if not approved:
                    reason = input("Reason for the denial (optional): ").strip() or None
                log_decision(conversation.id, item, approved, reason)
                answer = McpApprovalResponse(
                    type="mcp_approval_response",
                    approve=approved,
                    approval_request_id=item.id,
                )
                if reason:
                    answer["reason"] = reason  # optional field in the Responses API schema
                answers.append(answer)
            # Same conversation, as Learn says, not previous_response_id.
            response = openai.responses.create(conversation=conversation.id, input=answers)
            show(response)
        else:
            print(f"\nStopped after {MAX_ROUNDS} approval rounds.")

        print(f"\n< {response.output_text}")
        openai.conversations.delete(conversation_id=conversation.id)


def show_log():
    if not LOG.exists():
        print("No decisions logged yet. Run `ask` first.")
        return
    for line in LOG.read_text().splitlines():
        e = json.loads(line)
        verdict = "APPROVED" if e["approved"] else "DENIED"
        reason = f" ({e['reason']})" if e["reason"] else ""
        print(f"{e['time']}  {verdict:8}  {e['tool']}  by {e['decided_by']}{reason}")
        print(f"    arguments: {e['arguments']}")


def cleanup():
    try:
        project.agents.delete(agent_name=AGENT_NAME)  # the agent and all its versions
        print(f"Deleted agent {AGENT_NAME}")
    except Exception as e:
        print(f"Agent: {e}")
    if LOG.exists():
        LOG.unlink()
        print(f"Deleted {LOG.relative_to(LOG.parent.parent)}")


STEPS = {"setup": setup, "ask": ask, "log": show_log, "cleanup": cleanup}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=STEPS)
    STEPS[parser.parse_args().step]()
    sys.exit(0)
