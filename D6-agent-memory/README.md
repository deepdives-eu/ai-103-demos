# D6 Memory across sessions

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video 'Agents: memory, evaluation and orchestration' in the AI-103 playlist.

**Goal:** an agent remembers a user's preference in a new conversation, keeps it away from a second user, and forgets it on request.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Implement generative AI and agentic solutions > Build agents by using Foundry: "Build agents that integrate retrieval, function-calling, and conversation memory"
- Plan and manage an Azure AI solution > Choose the appropriate Foundry services: "Choose appropriate memory, tool, and knowledge integration services for agent solutions"

**Preview.** Memory in Foundry Agent Service and the Memory Store API are in preview, under the Supplemental Terms of Use for Microsoft Azure Previews.

## What it costs and why

Learn says: "You're billed for usage of the underlying chat and embedding models you configure", and pricing "can change during preview". No separate price is stated, so none is given here.

Cost drivers, all pay-per-token on the shared Global Standard deployments in your subscription:

- **Agent responses**: 4 short turns on `gpt-5.4-mini` (tell, recall, other user, forget). The instructions cap answers at two sentences.
- **Memory extraction and consolidation**: the service calls the store's chat model after each conversation. This demo turns off chat summary and procedural memory and keeps only user profile memory, so there is less to extract.
- **Embeddings**: `text-embedding-3-small` for storing and searching memory items. A handful of short items.
- **Nothing hourly.** Learn states no idle charge for the memory store or the agent, but delete them anyway (see Cleanup). Listing and deleting items calls no model.

The demo uses Azure OpenAI models sold directly by Azure, on Global Standard deployments only. Delete what you created afterwards.

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini` and `text-embedding-3-small`). Sweden Central is on Learn's memory region list. Memory needs Azure OpenAI chat and embedding deployments; both are.
- You (the signed-in user) have Foundry User on the Foundry resource. `../common/setup.sh` does that.
- The project's managed identity has Foundry User on the Foundry resource. Learn lists this as a prerequisite for memory. `../common/setup.sh` does that too. Foundry User is role ID `53ca6127-db72-4b80-b1b0-d745d6d5456d` (formerly Azure AI User); Learn recommends the role ID because of the rename.
  If the project has no system-assigned identity yet, the script cannot assign the role. In that case, open the portal, go to your project, then **Resource Management > Identity**, switch the system-assigned identity on, and re-run `../common/setup.sh`.
- Python 3, Azure CLI signed in (`az login`).

## Setup

```bash
cd D6-agent-memory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

Role assignments can take a few minutes to apply. If the first call fails with a permission error, wait a few minutes and try again.

## Steps

1. **Read the code: memory store.** Open `memory_demo.py` and scroll to `setup()`, the `MemoryStoreDefaultOptions` and `MemoryStoreDefaultDefinition` part.
   Long-term memory lives in a memory store. It needs two models: a chat model to pull facts out of conversations, and an embedding model to find them again. Only user profile memory is switched on. Chat summary and procedural memory stay off. `user_profile_details` tells the service what is worth keeping: food preferences, nothing sensitive.

2. **Read the code: the tool.** Look at the `MemorySearchPreviewTool` lines.
   The agent gets memory through one tool. Two settings matter. `scope` is the user ID placeholder, so every user gets their own memory. `update_delay` is how long the service waits after the last activity before it writes memory. The default is 300 seconds; the demo sets it to 1.

3. **Run `python memory_demo.py setup`.** This creates the store and a prompt agent with the tool attached.
   Expected: `Memory store: d6_memory_store` and `Agent: d6-memory-agent, version 1`.

4. **Run `python memory_demo.py tell`.** Conversation 1, as user `alice`: she says she is vegetarian and doesn't like mushrooms. The script then waits until the memory is written. The write isn't instant: the service extracts and consolidates in the background, which can take up to a minute.
   Expected: a short reply, then dots, then `scope 'alice': 1 memory item(s)` (or 2) with a `user_profile` item about vegetarian and mushrooms.
   If this step fails or nothing is stored: the script gives up after 2 minutes. Run `python memory_demo.py list` again after a minute. If calls fail with a preview or permission error, check both role assignments first (your user and the project's managed identity). Some Learn samples create the client with `AIProjectClient(..., allow_preview=True)` before calling `beta.memory_stores`; the memory how-to doesn't. Add it if the SDK asks for it.

5. **Run `python memory_demo.py recall`.** A brand-new conversation, same user. Compare the conversation ID with the one in step 4: it is different, so there is no chat history.
   Expected: a vegetarian suggestion with no mushrooms. That came from memory, not from the conversation. The script also prints the output item types of the response; one of them is the memory tool call.

6. **Run `python memory_demo.py other-user`.** The same question as user `bob`. Same agent, same store, but Bob's scope is empty.
   Expected: an ordinary suggestion, possibly with meat or mushrooms.

7. **Run `python memory_demo.py list`.** Memory is data you can inspect, per user.
   Expected: `scope 'alice': n memory item(s)` with the content, and `scope 'bob': 0 memory item(s)`.
   If this step shows 0 items for both users although `recall` worked: with scope `{{$userId}}`, Learn says the `x-memory-user-id` header value "is used as the user ID". The script assumes the stored scope is exactly that string, so `list_memories(scope="alice")` finds it. If your store keeps it differently, use a static scope instead (`scope="alice"` in the tool, one agent version per user).

8. **Run `python memory_demo.py forget`.** Users can ask the agent to forget. When a request is an explicit remember or forget command, the tool applies it straight away, with no update delay.
   Expected: `memory_command_call {"action": "forget", "content": "..."} completed`, then the list without the mushroom item. If the item was stored together with "vegetarian" as one memory, the remaining item may be rewritten rather than gone. Read whatever the list shows.
   This step uses the memory tool inline on a plain Responses call with an explicit scope, exactly as the Learn sample does, rather than the agent.

9. **Run `python memory_demo.py delete-item`** (optional, only if anything is left). As the developer you can delete items directly by ID. That is what you would build a "delete my data" button on. There is also a call to wipe a whole user scope.
   Expected: `Deleted <id>`, then `scope 'alice': 0 memory item(s)`.

10. **Wrap up, no command.** A memory store, one tool on the agent, a scope per user. Short-term memory is the conversation. Long-term memory is this. It is in preview, so check the docs before you build on it.

## Cleanup

```bash
python memory_demo.py cleanup
```

This deletes the agent (all versions) and the memory store with all memories in all scopes. Leave the shared project and deployments; the other demos use them. Optionally remove the project identity's role assignment if no other demo needs it.

## Notes

- `default_ttl_seconds` gets a `timedelta`, as in the Learn sample, despite the name.
- Default options (TTL, which memory types) can only be set when the store is created. To change them, run `cleanup` and `setup` again.
- Quotas: 100 scopes per store, 10,000 memories per scope.

## Sources

Microsoft Learn:

- Create and use memory in Foundry Agent Service (preview), Python: https://learn.microsoft.com/azure/foundry/agents/how-to/memory-usage
- Memory in Microsoft Foundry Agent Service (preview), concepts, types, regions, pricing, quotas: https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-memory
- Role-based access control for Microsoft Foundry (Foundry User for the project managed identity): https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry#minimum-role-assignments-to-get-started
- Authentication and authorization in Microsoft Foundry (role IDs): https://learn.microsoft.com/azure/foundry/concepts/authentication-authorization-foundry#set-up-microsoft-entra-id
- Delete an agent, Python: https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code#clean-up-resources
- Study guide for Exam AI-103: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Checked against Learn on 2026-11-07.
