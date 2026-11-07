# D7 Model router

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video 'Agents: memory, evaluation and orchestration' in the AI-103 playlist.

**Goal:** send easy and hard prompts to one model router deployment, see which underlying model answered each one, and compare tokens and cost with a single fixed model.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Implement generative AI and agentic solutions > Optimize and operationalize generative AI systems: "Orchestrate multiple models, flows, or hybrid LLM and rules engines"
- Plan and manage an Azure AI solution > Choose the appropriate Foundry services for generative AI and agents: "Choose an appropriate model for each task, including large language models (LLMs), small language models, multimodal models, and Foundry Tools"
- Plan and manage an Azure AI solution > Manage, monitor, and secure AI systems: "Manage quotas, scaling, rate limits, and cost footprints for model and agent workloads"

**Preview.** Model router version `2025-11-18` is the current version. The per-request routing metadata in step 6 (`model_selection_details`, opted in with the `Foundry-Features: ModelRouterControls=V1Preview` header) is in preview, and Learn says its presence and schema "can vary by request and service version". The deployment call uses the management API version `2025-10-01-preview`, as Learn shows it.

## What it costs and why

Learn says: "Model router usage is charged for input prompts at the rate listed on the pricing page." The cost of a model router deployment is also "the sum of the costs incurred by the underlying models". So each prompt costs the router charge on its input tokens, plus the tokens of whichever model answered. No prices are given here; they are on the pricing page and can change.

Cost drivers, all pay-per-token, Global Standard:

- **Router step (`ask`)**: 4 prompts through the router. Two are one-liners. Two are short reasoning puzzles, capped at 4,000 output tokens each. Reasoning tokens are billed as output tokens.
- **Baseline step (`baseline`)**: the same 4 prompts on the shared `gpt-5.4-mini` deployment.
- **Trace step (`trace`)**: 1 more prompt through the router.
- **Optional mode change (step 7)**: 4 more prompts.
- **Nothing hourly.** The router is a Global Standard deployment, billed per token. `./cleanup.sh` deletes it anyway.

**Only models sold directly by Azure.** By default the router's pool for version `2025-11-18` includes models from OpenAI, DeepSeek, Meta, xAI, Fireworks and Anthropic. Anthropic's Claude models are partner models billed through Marketplace, which Azure credits don't cover; Learn says the router only uses them if you deploy them yourself first. This demo doesn't rely on that: `setup.sh` restricts the router to a **model subset** of four Azure OpenAI models (`gpt-5.4-nano`, `gpt-5.4-mini`, `gpt-5.4`, `o4-mini`). Learn: new models "are not included in your selection unless you explicitly add them", and the subset is also the failover set, so prompts don't go to models you didn't approve.

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini`). Sweden Central supports model router `2025-11-18` as Global Standard, and all four subset models are available there as Global Standard.
- You (the signed-in user) have Foundry User on the Foundry resource. `../common/setup.sh` does that.
- Permission to create and delete deployments on the Foundry resource (`setup.sh`, `cleanup.sh`). If you created the shared resource group yourself with `../common/setup.sh`, you have it.
- If your organisation uses the built-in Azure Policy for model deployment, its allowed publishers must include `Microsoft` (the publisher of model router). Otherwise the deployment is blocked.
- Python 3.10 or later, Azure CLI signed in (`az login`), `curl`.

## Setup

```bash
cd D7-model-router
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
cp prices.example.json prices.json   # optional: fill in prices per 1M tokens from the pricing page
```

The deployment is created in step 2. To use another deployment name, set `ROUTER_DEPLOYMENT` before running `setup.sh`, `route_demo.py` and `cleanup.sh`; the default is `model-router`.

## Steps

1. **Read the code: the deployment.** Open `setup.sh` and scroll to the `curl` call.
   Model router is deployed like any other model: name `model-router`, version `2025-11-18`, SKU `GlobalStandard`. The `routing` block has two settings. `mode` is the routing mode: Balanced (the default), Cost or Quality. `models` is the model subset: four Azure OpenAI models, from a nano model to a reasoning model. The Azure CLI deployment command has no routing options, so the script uses the management REST call from Learn.

2. **Run `./setup.sh`.** This creates the deployment in Balanced mode and waits until it is ready.
   Expected: the deployment JSON with your `routing` block, then `Deployment model-router: Succeeded, routing mode balanced`.
   If this step fails: check that the Foundry resource is in a supported region (Sweden Central is). If the error points at the routing models, compare each name and version with the supported models table on Learn and with the Global Standard region table for your region. If it mentions a policy, an Azure Policy blocks the publisher (see Prerequisites). If `curl` says the token expired, run `az login` again.

3. **Run `python route_demo.py ask`.** Four prompts to the one deployment: two easy, two hard. For each prompt the script prints the `model` field of the response: the underlying model that answered.
   Expected: the easy prompts answered by a small model (for example `gpt-5.4-nano-...`), the hard ones by a bigger or reasoning model (for example `gpt-5.4-...` or `o4-mini-...`), always one of the four in the subset. Which model the router picks is its decision and can change between runs.
   If this step fails: with a 404 or `DeploymentNotFound`, the deployment isn't ready yet; wait a minute. With a 401 or 403, check your Foundry User role assignment. If a hard prompt shows status `incomplete`, it ran out of output tokens; raise `MAX_OUTPUT_TOKENS` in the script.

4. **Read the table.** Under the answers the script prints one line per prompt: input tokens, output tokens, reasoning tokens (part of output), seconds and, if `prices.json` is filled in, the cost including the router charge on input.
   Expected: the easy prompts use a few dozen tokens and few or no reasoning tokens; the hard ones use far more, mostly reasoning. That's where the money goes.

5. **Run `python route_demo.py baseline`.** The same four prompts straight to the shared `gpt-5.4-mini` deployment, no router.
   Expected: every line says `gpt-5.4-mini-...`. Compare tokens, time and cost with step 4. With only four prompts this is an illustration, not a benchmark. Learn recommends comparing the router with your current model on your own workload before switching.

6. **Run `python route_demo.py trace`** (preview). One hard prompt through Chat Completions with the preview header that asks for routing metadata.
   Expected: `Routed to model: ...`, `Routing mode: balanced`, and one routing decision with its attempts, for example `Attempt 1: <model> - HTTP 200 (selected)`. Two attempts with the first one failed means the router fell back to another model in the subset.
   If this step fails or shows `No model selection details were returned.`: the metadata is optional during preview. The `model` field still shows the answering model. Learn's sample uses an API key and the `AZURE_OPENAI_ENDPOINT`; this script uses Entra ID and `https://<FOUNDRY>.openai.azure.com`. If you get a 401, check that `FOUNDRY` in `../common/demo.env` is your resource name.

7. **Optional: run `./setup.sh cost`, wait five minutes, then `python route_demo.py ask` again.** The same deployment, now in Cost mode. Learn: a routing mode change can take up to five minutes to take effect.
   Expected: more prompts go to the cheaper models in the subset. With four prompts you may see no difference at all. `./setup.sh` without an argument switches back to Balanced.

8. **Wrap up, no command.** One deployment, a model per prompt, and the `model` field tells you which. The subset decides which models are allowed, the mode decides how hard the router tries to save money. Where you need the same model on every request, use a direct deployment next to the router.

## Cleanup

```bash
./cleanup.sh
```

This deletes the model router deployment. Leave the shared project and deployments; the other demos use them.

## Notes

- The context window of a model router deployment is that of the smallest model in the subset. Long prompts only work if they happen to go to a larger model. Use the subset to leave out small models if you need a long context.
- Chat Completions is stateless, so each turn can go to another model. The session affinity preview (not used here) asks the router to try the same model across related turns.
- Rate limits: one tokens-per-minute setting for the whole router deployment (`capacity` 10 here), not per underlying model.
- To see where tokens go over time: Azure portal, the Foundry resource, Monitoring > Metrics, filter by the router deployment and split by underlying model. For cost: Cost analysis, filter by the tag Deployment with the router deployment name.
- Reasoning models ignore `temperature` and `top_p`. The script doesn't set them.

## Sources

Microsoft Learn:

- Model router for Microsoft Foundry, concepts, supported models, regions, routing mode, model subset, billing: https://learn.microsoft.com/azure/foundry/openai/concepts/model-router
- Use model router for Microsoft Foundry, deployment REST call, Responses and Chat Completions samples, cost monitoring: https://learn.microsoft.com/azure/foundry/openai/how-to/model-router
- How model router works, routing modes, when to use a direct deployment: https://learn.microsoft.com/azure/foundry/openai/concepts/model-router-how-it-works
- Monitor model router, `model_selection_details` and routing trace (preview): https://learn.microsoft.com/azure/foundry/openai/how-to/monitor-model-router
- Region availability for Foundry Models sold by Azure, Global Standard: https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability#global-standard
- Foundry Models sold by Azure: https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure
- Deploy and use Claude models in Microsoft Foundry, subscription types: https://learn.microsoft.com/azure/foundry/foundry-models/how-to/use-foundry-models-claude#subscription-type-and-region-support
- Products and services that Azure credits don't cover: https://learn.microsoft.com/azure/cost-management-billing/benefits/credits/mca-check-azure-credits-balance#products-and-services-that-azure-credits-don't-cover
- Keyless Chat Completions with `get_bearer_token_provider`: https://learn.microsoft.com/azure/foundry/openai/how-to/chatgpt#work-with-chat-completion-models
- `az cognitiveservices account deployment`: https://learn.microsoft.com/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest
- Study guide for Exam AI-103: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Checked against Learn on 2026-11-07.
