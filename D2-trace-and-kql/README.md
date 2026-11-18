# D2 Trace one agent run

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video "Plan and manage Foundry solutions" in the AI-103 playlist.

**Goal:** run one agent call with a tool call, follow it as a trace in the Foundry portal, then find the same request in Application Insights and Log Analytics with KQL, by its trace ID.

Time needed: about 10 minutes, plus 2 to 5 minutes of waiting for the trace to show up.

## Exam skill

AI-103, "Plan and manage an Azure AI solution (25–30%)":

> Implement auditing through trace logging, provenance metadata, and approval workflows

AI-103, "Implement generative AI and agentic solutions (30–35%)" > "Optimize and operationalize generative AI systems":

> Set up observability by implementing tracing, token analytics, safety signals, and latency breakdowns

And, under "Build agents by using Foundry":

> Integrate monitoring into deployed agents, evaluate agent behavior, and perform error analysis

This demo covers tracing, token counts, latency per span and finding one request. Safety signals, evaluation and approval workflows are other demos (D1, D4, D5).

## What it costs and why

Tokens plus a very small amount of log ingestion. Nothing is billed by the hour.

- **Tokens:** one question, so two or three calls to `gpt-5.4-mini` (the question, then the answer after the tool result). The script prints the token counts. Every re-run is new tokens.
- **Log ingestion is the cost driver on the monitoring side.** Learn: log data ingestion is the largest part of Azure Monitor charges for most customers, billed per GB, with 31 days of analytics retention included. Application Insights tables (`AppDependencies`, `AppRequests` and so on) keep 90 days at no charge. Interactive queries on these tables aren't charged. One run is a handful of spans, kilobytes. Query 4 in `queries.kql` shows the billed size.
- **Content recording makes spans bigger.** The script turns it on so the prompt and tool arguments show in the trace. Fine for a demo, not for production.
- **Safety net:** `setup.sh` sets a daily ingestion cap of 0.1 GB on the workspace and 30 days retention. Learn: the cap is a safeguard against spikes, not exact, and data over it is still billed. When it's reached, collection stops for the day.
- The workspace and Application Insights resource have no charge of their own beyond what they ingest and retain. `cleanup.sh` deletes them anyway.

The cost on your subscription is small. `gpt-5.4-mini` is a model sold by Azure, deployed as Global Standard by `../common/setup.sh`. No Marketplace model, no PTU. Delete everything afterwards (see Cleanup).

## Prerequisites

- The shared demo project from `../common/setup.sh` and `../common/demo.env` filled in. No new Foundry resource.
- `az login` with the account that has **Foundry User** on the project. No keys.
- Azure CLI 2.80.0 or later (the `az cognitiveservices account project` commands), Python 3.10 or later.
- Learn lists **Contributor or higher on the Foundry project** for client-side tracing, and **Log Analytics Reader** on the connected Application Insights to query traces. `setup.sh` assigns Log Analytics Reader on `rg-ai103-d2`. If the script fails with a permissions error even though you have Foundry User, ask for the missing role on the project. Don't switch to keys.
- You need rights to add a connection on the project (the portal Connect step).

## Setup

### If you haven't done this before, do it now

Skip any part you already did for another demo.

1. **Python extension for VS Code.** Only if you use VS Code. Open the Extensions view (Cmd+Shift+X on a Mac, Ctrl+Shift+X on Windows and Linux), search for **Python** and install the one by Microsoft. Or from a terminal:

   ```bash
   code --install-extension ms-python.python
   ```

   You don't need it to run the demo. It gives you code completion, and it lets VS Code use the virtual environment from part 3.

2. **Sign in to Azure.** Check who you're signed in as:

   ```bash
   az account show --query "{user: user.name, subscription: name}" -o table
   ```

   If that fails, or shows the wrong account or subscription, sign in. Use the account that has **Foundry User** on the demo project.

   ```bash
   az login
   ```

   With several subscriptions, `az login` asks you to pick one. To switch later: `az account set --subscription "<subscription name or ID>"`. In Azure Cloud Shell you're already signed in.

3. **Create the virtual environment.** Once per demo folder. It keeps this demo's packages apart from your other Python projects.

   ```bash
   cd D2-trace-and-kql
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   In VS Code, open the Command Palette, run **Python: Select Interpreter** and pick the one in `.venv`. New terminals in VS Code then activate it for you.

### Create the D2 resources

From `D2-trace-and-kql`:

```bash
./setup.sh                                   # rg-ai103-d2: law-ai103-d2 + appi-ai103-d2
```

### In every new terminal

```bash
cd D2-trace-and-kql
source .venv/bin/activate
set -a; source ../common/demo.env; set +a
export APPLICATIONINSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show \
  -g rg-ai103-d2 --app appi-ai103-d2 --query connectionString -o tsv)
```

The last line is for step 4. The script asks the project for the Application Insights connection string first. When the portal created the connection with the project's managed identity, the SDK can't read it from there, and the script uses this variable instead. The connection string isn't a secret: Learn says it isn't a security token or key.

Open `trace_one_run.py` and `queries.kql` in your editor. You will read the code in step 3 and paste the queries in steps 6, 7 and 9.

## Files

| File | What it is |
| --- | --- |
| `setup.sh` | Log Analytics workspace (30 days, 0.1 GB/day cap) and workspace-based Application Insights in `rg-ai103-d2`, Log Analytics Reader for you |
| `trace_one_run.py` | Prompt agent with one local function tool (`get_exam_weight`), client-side tracing to Azure Monitor, prints trace ID, response IDs, conversation ID |
| `queries.kql` | 1: one trace in Application Insights. 2: the same in the Log Analytics schema. 3: which keys are in `customDimensions`. 4: billed ingestion |
| `query_trace.sh` | Query 2 from the command line with `az monitor log-analytics query` |
| `cleanup.sh` | Deletes the agent version and conversation, the Application Insights connection, and `rg-ai103-d2` |

## Steps

1. **Look at the monitoring resources.** Azure portal, `rg-ai103-d2`: the workspace and Application Insights. Open the workspace, **Usage and estimated costs**, and look at **Daily cap** and **Data retention**.

   Tracing needs somewhere to land. That's Application Insights, which stores its data in a Log Analytics workspace. What you pay for is ingestion, so the setup put a small daily cap on it. That cap is a safety net, not a budget.

2. **Connect Application Insights to the project.** Foundry portal (New Foundry toggle on), the demo project, **Agents**, **Traces** at the top, **Connect**, select `appi-ai103-d2`, **Connect**.

   If this step fails: if there's no Connect button, go to **Manage**, **Project details**, **Connected resources**, **Add connection**, **Application Insights**.

   One project has one Application Insights resource. Once it's connected, Foundry traces prompt agents on the server side without any code. Everything you add in code comes on top of that.

3. **Read the code.** Open `trace_one_run.py` and go through it top to bottom: `AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING`, content recording, `configure_azure_monitor` with the connection string from `project.telemetry`, `AIProjectInstrumentor().instrument()`, the function tool, `@trace_function`, the root span, the tool loop.

   Client-side tracing is opt-in, and it's preview. The flag must be set before you instrument. The connection string comes from the project, or from the Application Insights resource when the project's connection uses managed identity. Either way there's no secret in the code. Message content is recorded because this is a demo. In production you usually don't.

4. **Run it.**

   ```bash
   python trace_one_run.py
   ```

   The first line says where the Application Insights connection string came from. If the script stops with "Application Insights connection does not use API Key credentials", run the `export` line from "In every new terminal" and run it again.

   The agent can't know the exam weights, so it has to call the function. That's a round trip: the model asks for the tool, your code runs it, you send the result back. Note the trace ID at the end. You will search for it in the next steps.

5. **Find the trace in Foundry.** Wait 2 to 5 minutes. Go to **Agents**, **Traces**, and search by the trace ID or a response ID. Open it and step through the spans: the agent call, the model calls, the tool call. Look at the duration per span and the token counts. Open the **Conversation** to see ordered run steps and tool calls.

   If the trace doesn't show up after 10 minutes, or only some spans appear: search by response ID instead of trace ID. Learn says trace context propagation is on by default and links client and server spans. If they don't share the trace ID in your project, the response ID still finds the run. The function runs in your code, so the tool span may come only from `@trace_function`, not from the service.

   Each span is one step. The model asks for the tool, your function runs, the second model call follows. Each has its own latency, so you can see where the time goes. The tokens are on the span, so you can see where the cost goes.

6. **Find the same request in Application Insights.** Azure portal, `appi-ai103-d2`, **Logs**. Paste query 1 from `queries.kql` and put your trace ID in.

   If a column comes back empty: run query 3 to list the keys that are really in `customDimensions`, and use those. The token keys should be `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`. Also check whether `agent.id` shows as `name:version`.

   In Application Insights the trace ID is `operation_Id`. Everything in one request shares it. Agent spans land in `requests` or `dependencies`, and the GenAI details are in `customDimensions`. So: filter on the operation ID, pull out what you need.

7. **Find it in the workspace.** Open `law-ai103-d2`, **Logs**, and run query 2.

   Same data, other names. In the workspace the table is `AppDependencies`, `operation_Id` becomes `OperationId`, and `customDimensions` becomes `Properties`. Worth knowing for the exam, because a question can use either.

8. **Query from the command line.**

   ```bash
   ./query_trace.sh
   ```

   Same query from the CLI. Handy in a script or a pipeline.

9. **Check what it cost.** Run query 4 in the workspace.

   This is what your run ingested. Kilobytes. The cost of tracing scales with traffic and with what you record, so content recording and sampling are the two knobs to think about.

10. Optional: open the agent's **Monitor** tab (preview) for token usage, latency and success rate. It reads the same Application Insights data.

## Expected output

```text
Application Insights connection string: from the project connection
Agent: d2-trace-demo version 1 (id: d2-trace-demo:1)
Tool call: get_exam_weight({'skill_area': 'plan and manage'}) -> 25-30%
Answer: Planning and managing an Azure AI solution is 25-30% of the AI-103 exam.
Tokens (last response): input ..., output ...
Conversation ID: conv_...
Response IDs: resp_..., resp_...
Trace ID (operation_Id): 4bf92f3577b34da6a3ce929d0e0e4736
Spans sent. Traces typically take 2-5 minutes to show up.
```

With a managed-identity connection the first line says `from APPLICATIONINSIGHTS_CONNECTION_STRING` instead. The ID formats in the agent and trace ID lines are examples. In KQL, expect rows with `gen_ai.operation.name` values such as `invoke_agent`, `chat` and `execute_tool` (OpenTelemetry GenAI conventions), plus `lookup_exam_weight` from `@trace_function`, which records the parameter and return value as `code.function.parameter.skill_area` and `code.function.return.value`. Exact span names can differ between client-side and server-side spans.

## Cleanup

```bash
./cleanup.sh                     # lists the project's connections and stops
./cleanup.sh <connection-name>   # deletes agent + conversation, the connection, rg-ai103-d2
```

The portal picks the name of the Application Insights connection, and it may be on the project or on the Foundry resource. `cleanup.sh` only handles project connections. If the connection is on the resource, remove it in the portal (**Connected resources**) and run `./cleanup.sh none`. Don't leave a connection pointing at a deleted Application Insights, because later traces would go nowhere.

The shared project and its deployments stay for the other demos.

## Sources

Microsoft Learn:

- Set up tracing in Microsoft Foundry: https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-setup
- Add client-side tracing to Foundry agents (preview): https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-client-side
- Function calling with Foundry agents: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/function-calling?pivots=python
- Agent spans in `requests` or `dependencies`, `customDimensions` query: https://learn.microsoft.com/azure/foundry/control-plane/migrate-custom-to-external-agent#troubleshoot-missing-traces
- GenAI span types and attributes (`invoke_agent`, `chat`, `execute_tool`, token usage): https://learn.microsoft.com/azure/foundry/how-to/develop/langchain-traces#understand-trace-structure
- Agent monitoring dashboard: https://learn.microsoft.com/azure/foundry/observability/how-to/how-to-monitor-agents-dashboard
- Application Insights data model, `operation_Id` / `OperationId`: https://learn.microsoft.com/azure/azure-monitor/app/data-model-complete#context
- Workspace vs Application Insights table and column names: https://learn.microsoft.com/azure/azure-functions/functions-hosted-skills-monitor-troubleshoot#query-hosted-skill-execution
- W3C trace-id maps to Operation Id: https://learn.microsoft.com/power-platform/architecture/key-concepts/distributed-tracing-details#trace-id-and-operation-id-mapping
- Create a workspace-based Application Insights resource (CLI): https://learn.microsoft.com/azure/azure-monitor/app/create-workspace-resource
- `az monitor log-analytics workspace create` (`--quota`, `--retention-time`): https://learn.microsoft.com/cli/azure/monitor/log-analytics/workspace?view=azure-cli-latest
- `az monitor log-analytics query`: https://learn.microsoft.com/azure/azure-monitor/logs/api/overview
- `az cognitiveservices account project connection`: https://learn.microsoft.com/cli/azure/cognitiveservices/account/project/connection?view=azure-cli-latest
- Daily cap: https://learn.microsoft.com/azure/azure-monitor/logs/daily-cap
- Retention, 90 days free for Application Insights tables: https://learn.microsoft.com/azure/azure-monitor/logs/data-retention-configure#log-tables-with-90-day-default-retention
- Azure Monitor cost and usage (ingestion is the largest charge): https://learn.microsoft.com/azure/azure-monitor/fundamentals/cost-usage
- Logs cost, table plans (31 days included, queries on Analytics tables not charged): https://learn.microsoft.com/azure/azure-monitor/logs/cost-logs#table-plans
- Billed size per table query: https://learn.microsoft.com/azure/azure-monitor/logs/analyze-usage#query-application-insights-data-volume
- AI-103 study guide: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103
- Sign in with `az login`, subscription selector, `az account set`: https://learn.microsoft.com/cli/azure/authenticate-azure-cli-interactively?view=azure-cli-latest
- Python extension for VS Code: https://learn.microsoft.com/azure/developer/python/configure-python-web-app-local-environment#working-with-visual-studio-code
- `APPLICATIONINSIGHTS_CONNECTION_STRING`: https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-configuration#connection-string
- The connection string isn't a security token or key: https://learn.microsoft.com/azure/azure-monitor/app/javascript-sdk#get-started

Other:

- Python in VS Code, select an interpreter: https://code.visualstudio.com/docs/python/environments
- `venv`: https://docs.python.org/3/library/venv.html

- OpenTelemetry GenAI semantic conventions: https://github.com/open-telemetry/semantic-conventions-genai/tree/main/docs/gen-ai

Checked against Learn on 2026-11-07.
