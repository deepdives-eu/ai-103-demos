# AI-103 demos

deepdives.eu demos for the AI-103 exam (Develop AI apps and agents on Azure) · our own material, not Microsoft Official Courseware.

The official course labs cover a lot. These demos cover exam topics the labs don't: evaluation in a CI pipeline, tracing, keyless auth, red teaming, human approval for tools, agent memory, model routing, a maker-checker loop, text and audio analysis with a model, image editing, image safety, and hybrid and semantic search. Each one goes with a video on the [deepdives-eu YouTube channel](https://www.youtube.com/@deepdives-eu), and you can run every one yourself.

| Demo | What you do | Costs while it exists |
| --- | --- | --- |
| [D1 Evaluation as a CI gate](D1-eval-ci-gate/) | A GitHub Actions workflow evaluates a new agent version and blocks the pull request when the pass rate drops | tokens only |
| [D2 Trace one agent run](D2-trace-and-kql/) | Send agent traces to Application Insights and find one request with KQL | tokens, log ingestion |
| [D3 Keyless by default](D3-keyless-auth/) | Call Foundry with Entra ID, switch API keys off, and see what the Foundry User role does | tokens only |
| [D4 Red-team an agent](D4-red-team-agent/) | Run a cloud AI Red Teaming Agent scan against a Foundry agent and read the attack success rate | tokens, evaluation |
| [D5 Human approval for a tool](D5-tool-approval/) | Approve one MCP tool call and deny another, with approval set per tool and a log of every decision | tokens only |
| [D6 Memory across sessions](D6-agent-memory/) | Give an agent long-term memory per user, then inspect and delete what it stored | tokens only |
| [D7 Model router](D7-model-router/) | Send easy and hard prompts to one router deployment and see which model answered and what it cost | tokens only |
| [D8 Maker-checker loop](D8-maker-checker/) | A writer and a reviewer agent in Agent Framework iterate until the reviewer approves, with a cap | tokens only |
| [D9 Text analysis with a model](D9-llm-text-analysis/) | Extract sentiment, tone, entities and a summary into a strict JSON schema | tokens only |
| [D10 Reason over audio](D10-reason-over-audio/) | Ask an audio model about a call recording, then compare with transcribe-then-analyse | tokens only |
| [D11 Edit an image with a mask](D11-image-edit-mask/) | Generate an image, then edit part of it with a mask and with a prompt only | tokens only |
| [D12 Alt text and a hidden instruction](D12-alt-text-and-injection/) | Write alt text for an image, then catch an instruction hidden in an image's text | tokens, free-tier resources |
| [D13 Hybrid and semantic search](D13-hybrid-semantic-search/) | Run the same query as keyword, vector, hybrid and semantic search and compare the scores | **hourly** (AI Search Basic) |

## Before you start

You need an Azure subscription where you can create resources and assign roles, the Azure CLI (2.80 or later), Python 3.10 or later (3.11 for D8), and for D1 a GitHub account.

The demos only use models sold directly by Azure, deployed as Global Standard (pay per token). Partner and Marketplace models are billed separately and aren't needed here. Set a budget alert on your subscription first, and run each demo's cleanup when you're done.

## Shared setup

All demos use one Foundry resource and project in Sweden Central, with `gpt-5.4-mini` and `text-embedding-3-small`. Nothing in it costs money while idle.

```bash
git clone https://github.com/deepdives-eu/ai-103-demos.git
cd ai-103-demos
az login
cp common/demo.env.example common/demo.env   # set a globally unique FOUNDRY name
./common/setup.sh
```

Run D3 before D10, D11 and D13 if you can. Those three give you the Cognitive Services OpenAI User role as well, and with that role the call in D3 keeps working after you remove Foundry User.

Then, for each demo:

```bash
cd D9-llm-text-analysis        # or any other demo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

and follow that demo's README.

## When you're done

Each demo has its own cleanup. To remove the shared project too:

```bash
az group delete -n rg-ai103-demos --yes
```

## Keeping up to date

Foundry changes fast and several features here are in preview. Every README says when it was last checked against Microsoft Learn. If a command fails, check the linked Learn page first, then open an issue here.

## Licence

Code and text: [MIT](LICENSE). Microsoft, Azure and Foundry are trademarks of Microsoft; this repo isn't affiliated with or endorsed by Microsoft.
