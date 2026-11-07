"""D4 step 3: read the red teaming results from the SDK.

Run-level counts per evaluator, then a tally of the output items. Prints counts only,
never prompt or response text, so nothing adversarial is printed.

  python 03_results.py            # run counts and ASR per evaluator
  python 03_results.py --inspect  # print the field names of one output item

Sources:
  https://learn.microsoft.com/azure/foundry/how-to/develop/run-ai-red-teaming-cloud#list-red-teaming-run-output-items-and-results
  https://learn.microsoft.com/azure/foundry/observability/quickstarts/quickstart-evaluate-hosted-agent#step-4-review-the-results
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).parent
STATE = HERE / ".d4_state.json"
OUT = HERE / "out"

# Run with --inspect to find the datasource_item field that names the attack
# strategy. Learn doesn't document it. Leave as None to skip the per-strategy tally.
STRATEGY_FIELD = None

endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
state = json.loads(STATE.read_text())

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=endpoint, credential=credential) as project,
    project.get_openai_client() as client,
):
    run = client.evals.runs.retrieve(run_id=state["run_id"], eval_id=state["red_team_id"])
    print(f"Status: {run.status}")
    print(f"Totals: {run.result_counts}")

    print("\nPer evaluator:")
    for c in run.per_testing_criteria_results or []:
        total = c.passed + c.failed
        # A failed row is treated as an attack that got through (ASR = failed / scored).
        asr = c.failed / total if total else 0.0
        print(f"  {c.testing_criteria:<24} passed {c.passed:>3}  failed {c.failed:>3}  ASR {asr:.0%}")

    items = list(client.evals.runs.output_items.list(run_id=state["run_id"], eval_id=state["red_team_id"]))
    print(f"\nOutput items: {len(items)}")

    if "--inspect" in sys.argv and items:
        first = items[0]
        print("item fields:", sorted(first.model_dump().keys()))
        print("datasource_item fields:", sorted((first.datasource_item or {}).keys()))
        sys.exit(0)

    if STRATEGY_FIELD:
        tally = Counter()
        for item in items:
            strategy = (item.datasource_item or {}).get(STRATEGY_FIELD, "unknown")
            for result in item.results:
                tally[(strategy, result.name, result.passed)] += 1
        print("\nPer strategy and evaluator:")
        for (strategy, name, passed), n in sorted(tally.items(), key=str):
            print(f"  {strategy:<20} {name:<24} {'passed' if passed else 'failed'} {n}")

    # Keep the raw items for inspection. Cloud results redact the adversarial inputs,
    # but don't share this file.
    OUT.mkdir(exist_ok=True)
    (OUT / "output_items.json").write_text(json.dumps([i.model_dump() for i in items], indent=2, default=str))

    print(f"\nReport: {run.report_url}")
