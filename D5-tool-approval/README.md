# D5 Human approval for a tool

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video 'Plan and manage: monitor, secure and govern' in the AI-103 playlist.

**Goal:** an agent uses an MCP server where one tool runs freely and another waits for a person. The person approves the call once and denies it once, and you compare what the agent does in each case.

The official lab on MCP integration (lab 2.3) already sets `require_approval="always"` on an MCP tool and approves every request automatically in a loop. This demo goes further: approval is set per tool, a person answers y or n at a prompt, a denied call shows what the model does without the tool, and every decision is written to an audit log.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Plan and manage an Azure AI solution > Implement responsible AI across generative AI and agentic systems: "Implement auditing through trace logging, provenance metadata, and approval workflows"
- Plan and manage an Azure AI solution > Implement responsible AI across generative AI and agentic systems: "Govern agent behavior with oversight modes, constraints, and tool-access controls"
- Implement generative AI and agentic solutions > Build agents by using Foundry: "Build autonomous or semiautonomous workflows with safeguards and approval flow controls"

## What it costs and why

Learn says that with the MCP tool "you only pay for tokens used when importing tool definitions or making tool calls—there are no additional fees involved". The Microsoft Learn MCP server is public, needs no key, and Learn says "There's no charge to use the MCP server."

Cost drivers, all pay-per-token on the shared Global Standard deployment in your subscription:

- **Agent responses**: two runs of `ask` on `gpt-5.4-mini`, each with two or three model calls (the question, then one call per approval round). The instructions cap answers at 80 words.
- **Tool definitions and tool results**: the two MCP tool definitions and the search and fetch results go into the model's input as tokens. A full Learn page from `microsoft_docs_fetch` is the largest single input in this demo; it only happens when you approve.
- **Nothing hourly.** A prompt agent has no idle cost, but delete it anyway (see Cleanup).

The demo uses an Azure OpenAI model sold directly by Azure, on a Global Standard deployment only. Delete what you created afterwards.

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini`). Learn's tool support table lists MCP as supported in Sweden Central and for `gpt-5.4-mini`.
- You (the signed-in user) have Foundry User on the Foundry resource. `../common/setup.sh` does that. Learn lists Foundry User as the role to create and test agents with the MCP tool. No project connection is needed, because the Learn MCP server needs no authentication.
- Python 3.10 or later, Azure CLI signed in (`az login`).

## Setup

```bash
cd D5-tool-approval
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

## Steps

1. **Read the code: one MCP server, two approval rules.** Open `approval_demo.py` and scroll to `setup()`, the `MCPTool` part.
   The agent gets the Microsoft Learn MCP server as one tool. `allowed_tools` limits it to two of the server's tools: `microsoft_docs_search` and `microsoft_docs_fetch`. `require_approval` is set per tool: `never` for search, `always` for fetch. Without it, the default is `always` for every tool. That is the setting the lab uses.

2. **Run `python approval_demo.py setup`.** This creates a prompt agent with the tool attached and prints the tool definition as it goes to the service.
   Expected: `Agent: d5-approval-agent, version 1`, then JSON with `"type": "mcp"`, `allowed_tools`, and `require_approval` containing `never` with `microsoft_docs_search` and `always` with `microsoft_docs_fetch`.

3. **Run `python approval_demo.py ask` and approve.** The question asks how to make only some MCP tools require approval, and tells the agent to search first and then read the page.
   The script prints the MCP items in each response. The search runs straight away (`mcp_call microsoft_docs_search ran`). The fetch doesn't; you get an `mcp_approval_request` with the server, tool and arguments, which here is the URL it wants to read. Check the URL, then type `y`.
   Expected: `mcp_call microsoft_docs_fetch ran`, then a short answer that names `require_approval` with a per-tool list and cites a Learn URL.
   If this step fails: if the first response already contains the answer and no approval request, the model skipped the fetch. Run `ask` again; the question asks for it explicitly. If the agent stops after you approve, Learn's troubleshooting says to send the approval in the same conversation with the request's ID as `approval_request_id`, which the script does. If the agent never calls a tool, check the tool names in the `mcp_list_tools` line. Learn says the Learn MCP server's tool list can change over time, and that names in `allowed_tools` must match what the server exposes.

4. **Run `python approval_demo.py ask` again and deny.** The same question in a new conversation. When the approval request for `microsoft_docs_fetch` comes, type `n`, and give a short reason, for example `Search results only in this session`.
   Expected: no `mcp_call` for the fetch. The agent answers from the search results and says it couldn't read the full page, as its instructions tell it to. The wording varies from run to run. Compare it with step 3: shorter, and based on search results only.
   If the agent asks for the fetch again: the script answers every new request the same way, with the same y/N prompt, and stops after 5 rounds.

5. **Run `python approval_demo.py log`.** Every decision from steps 3 and 4, with time, tool, arguments, who decided, and the reason for the denial.
   Expected: one `APPROVED` and one `DENIED` line for `microsoft_docs_fetch`, each with the URL it wanted to read. Search calls don't appear: they never needed a decision.
   Learn recommends logging approvals and tool calls for auditing. The log here is a local file (`out/approvals.jsonl`); in production it would go to your own audit store, next to the traces.

6. **Wrap up, no command.** Three controls in one tool definition and one loop. `allowed_tools` decides which tools the agent can see at all. `require_approval` decides which of those need a person. The loop in your application is where the person decides, and where you log it. The service only pauses; the approval itself is your code. For function tools in Microsoft Agent Framework, the same idea is `approval_mode` on the tool: `always_require` or `never_require`.

## Cleanup

```bash
python approval_demo.py cleanup
```

This deletes the agent (all versions) and the local audit log. Each `ask` run already deletes its own conversation. Leave the shared project and deployment; the other demos use them.

## Notes

- Learn's how-to page writes the per-tool form as `{"never": [<tool names>]}`. The Python SDK models it as `MCPToolRequireApproval(never=MCPToolFilter(tool_names=[...]))`, which serialises as `{"never": {"tool_names": [...]}}`. The script uses the SDK classes, and step 2 prints what is actually sent.
- `MCPToolFilter` also has `read_only`, which matches tools the server annotates as read-only. That would let you write "no approval for read-only tools" without naming them. This demo names the tools, so it doesn't depend on how the server annotates them.
- The lab continues after an approval with `previous_response_id`. This demo sends the approval in the same conversation, as Learn's current prompt-agent samples do. Learn says `previous_response_id` isn't supported with the Microsoft Copilot harness.
- The optional `reason` on a denial is a field of `mcp_approval_response` in the Responses API reference. Whether the model uses it in its answer isn't documented.
- An unanswered prompt counts as a denial (`y/N`, the default is no), as in the Learn sample.

## Sources

Microsoft Learn:

- Connect agents to Model Context Protocol servers (approval loop, `require_approval` values, `allowed_tools`, best practices, troubleshooting): https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol
- MCPTool class, Python (`require_approval`, `allowed_tools`): https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.models.mcptool
- MCPToolRequireApproval class, Python: https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.models.mcptoolrequireapproval
- MCPToolFilter class, Python (`tool_names`, `read_only`): https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.models.mcptoolfilter
- Use the Azure OpenAI Responses API, remote MCP servers and approvals (MCP cost): https://learn.microsoft.com/azure/foundry/openai/how-to/responses#using-remote-mcp-servers
- Azure OpenAI responses REST reference (`mcp_approval_response`, `reason`, `mcp_list_tools`, `mcp_call`): https://learn.microsoft.com/rest/api/microsoft-foundry/azureopenai/responses
- Microsoft Learn MCP Server overview (endpoint, no authentication, no charge): https://learn.microsoft.com/training/support/mcp
- Microsoft Learn MCP Server developer reference (tool names): https://learn.microsoft.com/training/support/mcp-developer-reference
- Foundry Agent Service limits, quotas, and regional support (MCP by region and model): https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions#tool-support-by-region-and-model
- Microsoft Foundry SDKs and endpoints (package versions): https://learn.microsoft.com/azure/foundry/how-to/develop/sdk-overview
- Using function tools with human in the loop approvals, Agent Framework (`approval_mode`): https://learn.microsoft.com/agent-framework/agents/tools/tool-approval
- Study guide for Exam AI-103: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Checked against Learn on 2026-11-07.
