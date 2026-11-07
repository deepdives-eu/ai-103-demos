# D4 Red-team an agent

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video "Plan and manage Foundry solutions" in the AI-103 playlist.

**Goal:** run a small cloud AI Red Teaming Agent scan against a prompt agent with one tool, and read the attack success rate in the portal and from the SDK.

The local `RedTeam` API from `azure-ai-evaluation` is the one most examples show. This demo uses the cloud version from `azure-ai-projects`, which is the only one that can test agentic risks. Optional step 8 shows the local one for contrast.

**Exam skills (AI-103 study guide, skills measured as of April 16, 2026):**
- Plan and manage an Azure AI solution › Implement responsible AI across generative AI and agentic systems: "Apply responsible AI instrumentation, including evaluators, safety evaluations, and explanation tooling"
- Implement generative AI and agentic solutions › Build generative applications by using Foundry: "Evaluate models and apps, including detecting fabrications, relevance, quality, and safety"

**Overlap with labs:** none. The official labs have no AI Red Teaming Agent exercise (only a model-evaluation exercise).

Time: about 15 minutes of work. The scan itself runs for a while, so start it and come back for the results.

## What it costs and why

Everything here is Azure-sold: the `gpt-5.4-mini` Global Standard deployment and Foundry's own evaluation services. They are billed to your subscription. Delete everything afterwards (see Cleanup).

Cost drivers:

- **Target tokens.** Every attack item is a call to your agent, so `gpt-5.4-mini` tokens on your deployment. The agent's File Search calls add a few tokens each.
- **Evaluation.** Each item is scored by three evaluators. Task Adherence uses your deployment as the judge (more `gpt-5.4-mini` tokens). Prohibited Actions and Sensitive Data Leakage are Foundry's built-in safety evaluators, billed as evaluation by Foundry. Learn doesn't give a per-item figure; see the [Foundry pricing page](https://azure.microsoft.com/pricing/details/ai-foundry/).
- **File Search.** Billed on vector storage. One small markdown file, deleted by `cleanup.py`.
- **Nothing hourly.** No new resources; the agent, red team, taxonomy and vector store live in the project and are deleted afterwards.

How the demo keeps it small: the cloud API has no `num_objectives`. The service generates the attack items from the taxonomy, so the levers are one taxonomy risk category (Prohibited Actions), two attack strategies (`Flip`, `IndirectJailbreak`) and `num_turns: 1`. After the run, check **Evaluation tokens** and **Target tokens** for the run in the portal's Evaluation list, and Cost Management the next day. If it's more than you expected, drop to one strategy.

## Region check

Cloud red teaming is available in East US 2, France Central, **Sweden Central**, Switzerland West and North Central US ([AI Red Teaming Agent, agentic risks](https://learn.microsoft.com/azure/foundry/concepts/ai-red-teaming-agent#agentic-risks)). The three categories used here (prohibited actions, sensitive data leakage, task adherence) are cloud only and agents only. File Search is available for agents in Sweden Central ([tool support by region](https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions#tool-support-by-region-and-model)).

## Safety notes

- Red teaming produces adversarial content. Don't share or publish raw attack prompts, and don't paste them into tickets, chats or social media.
- Cloud red teaming redacts the harmful or adversarial inputs from the results, so the portal and the output items don't show attack prompts. Learn also says agent red teaming runs are transient: the Agent Service doesn't log the harmful data and doesn't store the completions.
- The scripts print counts, IDs and status only, never prompt or response text. `out/output_items.json` holds the raw output items; keep it to yourself.
- In the portal, the run summary and the per-evaluator scores are the safe places to look. Check the row view before you share a screenshot of it.
- The optional local scan (step 8) is **not** redacted: its JSON file contains the raw attack prompts. Only the printed scorecard is safe to share.

## Prerequisites

- The shared project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini`, Foundry User role for you on the project). Foundry User is the role the cloud red teaming page lists.
- Python 3.10 or later.
- `az login` to your subscription.

## Setup

```bash
cd D4-red-team-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

## Steps

1. **Create the agent.** Look at `01_create_agent.py`: one File Search tool over a fictional travel policy, and instructions that forbid sharing bank details and touching expense claims. Run:
   ```bash
   python 01_create_agent.py
   ```
   Expected: `Agent: d4-travel-assistant, version 1` and a short answer quoting the 180 euro hotel limit.

2. **Why a tool matters.** Look at the tool and the instructions in `01_create_agent.py`. Agent red teaming checks more than the text. It also looks at what the agent does with its tools. The agentic categories only run in the cloud, so the attacks happen in a sandbox and not on your machine. One catch: function tools aren't supported as a target yet. Built-in tools like File Search are.
   If step 5 fails on the File Search tool, check that `gpt-5.4-mini` supports File Search in agents in your region (see the model table under [tool support by region and model](https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions#tool-support-by-region-and-model)). Learn lists "Azure tool calls" as supported and function tools as not supported, but doesn't name File Search.

3. **The red team and its evaluators.** Look at the `client.evals.create` block in `02_red_team.py`. A red team in Foundry is an evaluation with the scenario `red_team`. It has three evaluators: prohibited actions, task adherence and sensitive data leakage. Task adherence needs a judge model, so it uses your own deployment.

4. **Taxonomy and target.** Look at the `AzureAIAgentTarget` and `evaluation_taxonomies.create` blocks in `02_red_team.py`. The target is your agent, by name and version, with a short description of its tool. For prohibited actions, the service first builds a taxonomy: a list of things this agent must not do, based on its tools. In real use, review that list before you run.

5. **Start the run.** Look at `ATTACK_STRATEGIES` and `NUM_TURNS`, then run:
   ```bash
   python 02_red_team.py
   ```
   `Flip` reverses the text of the prompt. `IndirectJailbreak` hides the attack in what a tool returns, which is the classic agent problem. The run is kept small on purpose, because every attack is a call to your model and an evaluation.
   Expected: the red team, taxonomy and run IDs, then `Status: queued` / `in_progress` lines every 15 seconds until `Status: completed`, and a report URL.
   If this step fails… `NUM_TURNS` is 1 because the agentic categories are described as single-turn. Learn's sample uses 5, and the REST reference marks `num_turns` as required with a default of 20. If the service rejects 1, set `NUM_TURNS = 5`. Learn doesn't say how many attack items the service generates from the taxonomy, so the cost of one run is only known after it finishes.

6. **Results in the portal.** Open the report URL (or Foundry portal › your project › **Evaluation**, select the run). Look at status, target, evaluation and target tokens, and the score per evaluator.
   The number that matters is the attack success rate (ASR): the share of attacks that got the agent to misbehave. Lower is better. You won't see the attack prompts: cloud red teaming redacts them.
   If this step fails… if you can't find the run in the Evaluation list, look for a separate red teaming tab in the portal. The portal layout may differ. Learn describes a scorecard by risk category and attack technique for the local scan; the cloud portal may not show ASR per category or per strategy.

7. **Results from the SDK.** Run:
   ```bash
   python 03_results.py
   ```
   Per evaluator you get passed and failed counts, and from those the attack success rate. This is what you would put in a pipeline: run the red team before a release and stop if the rate goes up.
   Expected: `Status: completed`, a `ResultCounts(...)` line, one line per evaluator with passed, failed and ASR, the number of output items, and the report URL.
   If the numbers look odd: the script treats a *failed* row as a successful attack. Learn defines ASR as successful attacks over total attacks but doesn't state how that maps to `passed` and `failed` for red team runs. Check one row in the portal against the counts.
   Optional: `python 03_results.py --inspect` prints the field names of one output item (no content). If one of them names the attack strategy, put it in `STRATEGY_FIELD` in `03_results.py` to get a per-strategy tally.

8. **Optional: a local scan for contrast.** There's a local version in the `azure-ai-evaluation` package. It can only test content risks, like violence, and you point it at any Python function. Here that's a function that always refuses, so the expected attack success rate is zero. It's handy while you build. The agentic categories, and the redaction, are cloud only. Use a second venv:
   ```bash
   python3 -m venv .venv-local && source .venv-local/bin/activate
   pip install -r requirements-local.txt
   python 04_local_scan.py
   ```
   Expected: `risk_category_summary` and `attack_technique_summary` with `violence_asr` and `baseline_asr` of 0.0.
   If this step fails… Learn says local red teaming "is not compatible with the Foundry (new) portal and SDK". The `RedTeam` constructor accepts a Foundry project endpoint, but whether a scan completes against a new Foundry project isn't stated. If it fails, skip this step. It isn't needed for the rest.

9. **Wrap-up.** Evaluators measure normal traffic; the red team attacks on purpose. Pick the categories that fit your agent, keep the first run small, read the attack success rate, fix, and run again.

## Cleanup

```bash
python cleanup.py
```

Deletes the red team (and its runs), the taxonomy, the agent (all versions) and the vector store, then removes `out/` and `.d4_state.json`. The shared Foundry resource, project and deployments stay. If the local scan ran, `out/local-scan.json` (unredacted) is deleted with `out/`.

## Files

| File | What it does |
| --- | --- |
| `01_create_agent.py` | Vector store with `data/travel_policy.md`, prompt agent with File Search, one test question |
| `02_red_team.py` | Red team with three evaluators, taxonomy for prohibited actions, run with two strategies, polls to completion |
| `03_results.py` | Run-level counts and ASR per evaluator, output-item tally; `--inspect` shows the output item field names |
| `04_local_scan.py` | Optional: local scan of a fixed-refusal function, one objective, Violence, Flip |
| `cleanup.py` | Deletes everything 01 and 02 created |
| `requirements.txt` | `azure-ai-projects>=2.0.0` (from Learn), `azure-identity` |
| `requirements-local.txt` | Optional: `azure-ai-evaluation[redteam]`, `azure-identity` (Learn gives no minimum versions) |

## Sources

- https://learn.microsoft.com/azure/foundry/how-to/develop/run-ai-red-teaming-cloud (prerequisites, `azure-ai-projects>=2.0.0`, red team, taxonomy, run, polling, output items)
- https://learn.microsoft.com/azure/foundry/concepts/ai-red-teaming-agent (risk categories and where they run, regions, redaction, transient runs, supported agents and tools, attack strategies, limitations)
- https://learn.microsoft.com/azure/foundry/how-to/develop/run-scans-ai-red-teaming-agent (local scan, `num_objectives`, callback target, scorecard, "not compatible with the Foundry (new) portal and SDK")
- https://learn.microsoft.com/azure/foundry/agents/how-to/tools/file-search?pivots=python (vector store, `FileSearchTool`, agent creation)
- https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions#tool-support-by-region-and-model (File Search in Sweden Central)
- https://learn.microsoft.com/azure/foundry/agents/faq#how-am-i-charged-for-foundry-agent-service (model tokens, File Search billed on vector storage)
- https://learn.microsoft.com/azure/foundry/observability/quickstarts/quickstart-evaluate-hosted-agent#step-4-review-the-results (`result_counts`, `per_testing_criteria_results`, output item results)
- https://learn.microsoft.com/azure/foundry/how-to/evaluate-results (portal Evaluation page, evaluation and target tokens)
- https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.models.azureaiagenttarget (target fields, `tool_descriptions`)
- https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.models.riskcategory (`PROHIBITED_ACTIONS` and the other values)
- https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.operations.betaevaluationtaxonomiesoperations (taxonomy delete)
- https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-synthetic-conversations#get-the-results (`evals.delete`)
- https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103 (skill wording)
- https://azure.microsoft.com/pricing/details/ai-foundry/ (pricing, linked from Learn)

Checked against Learn on 2026-11-07.
