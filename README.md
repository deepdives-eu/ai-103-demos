# AI-103 demos

deepdives.eu demos for the AI-103 exam (Develop AI apps and agents on Azure) · our own material, not Microsoft Official Courseware.

The official course labs cover a lot. These demos cover exam topics the labs don't: evaluation in a CI pipeline, tracing, red teaming, agent memory, text analysis with a language model, and hybrid and semantic search. Each one goes with a video on the [deepdives-eu YouTube channel](https://www.youtube.com/@deepdives-eu), and you can run every one yourself.

| Demo | What you do | Costs while it exists |
| --- | --- | --- |
| [D1 Evaluation as a CI gate](D1-eval-ci-gate/) | A GitHub Actions workflow evaluates a new agent version and blocks the pull request when the pass rate drops | tokens only |
| [D2 Trace one agent run](D2-trace-and-kql/) | Send agent traces to Application Insights and find one request with KQL | tokens, log ingestion |
| [D4 Red-team an agent](D4-red-team-agent/) | Run a cloud AI Red Teaming Agent scan against a Foundry agent and read the attack success rate | tokens, evaluation |
| [D6 Memory across sessions](D6-agent-memory/) | Give an agent long-term memory per user, then inspect and delete what it stored | tokens only |
| [D9 Text analysis with a model](D9-llm-text-analysis/) | Extract sentiment, tone, entities and a summary into a strict JSON schema | tokens only |
| [D13 Hybrid and semantic search](D13-hybrid-semantic-search/) | Run the same query as keyword, vector, hybrid and semantic search and compare the scores | **hourly** (AI Search Basic) |

## Before you start

You need an Azure subscription where you can create resources and assign roles, the Azure CLI (2.80 or later), Python 3.10 or later, and for D1 a GitHub account.

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
