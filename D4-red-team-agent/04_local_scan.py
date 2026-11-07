"""D4 optional step 8: a local scan against a fixed callback, for contrast.

Runs in its own venv (requirements-local.txt). One risk category, one objective, one strategy:
two attack-response pairs (baseline + Flip). The callback never calls a model.

Learn says local red teaming "is not compatible with the Foundry (new) portal and SDK", so
nothing shows up in the portal. Prints only the scorecard summaries. The JSON file also holds
the raw, unredacted attack prompts: don't open or share it; cleanup.py deletes it.

Source: https://learn.microsoft.com/azure/foundry/how-to/develop/run-scans-ai-red-teaming-agent
"""

import asyncio
import json
import os
from pathlib import Path

from azure.ai.evaluation.red_team import AttackStrategy, RedTeam, RiskCategory
from azure.identity import DefaultAzureCredential

OUT = Path(__file__).parent / "out" / "local-scan.json"


def fixed_refusal(query: str) -> str:
    # Stands in for an app. Always refuses, so we expect an ASR of 0.
    return "I'm a travel policy assistant. I can't help with that."


async def main() -> None:
    OUT.parent.mkdir(exist_ok=True)
    red_team = RedTeam(
        azure_ai_project=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
        risk_categories=[RiskCategory.Violence],
        num_objectives=1,
    )
    await red_team.scan(
        target=fixed_refusal,
        scan_name="D4 local contrast",
        attack_strategies=[AttackStrategy.Flip],
        output_path=str(OUT),
    )
    scorecard = json.loads(OUT.read_text())["redteaming_scorecard"]
    for key in ("risk_category_summary", "attack_technique_summary"):
        print(key, json.dumps(scorecard[key], indent=2))


asyncio.run(main())
