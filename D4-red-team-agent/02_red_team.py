"""D4 step 2: cloud AI Red Teaming Agent run against the agent from step 1.

Follows https://learn.microsoft.com/azure/foundry/how-to/develop/run-ai-red-teaming-cloud :
a red team (eval with scenario red_team), a taxonomy for prohibited actions, a run with
attack strategies, then poll until it finishes.
"""

import json
import os
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentTaxonomyInput,
    AzureAIAgentTarget,
    EvaluationTaxonomy,
    RiskCategory,
    ToolDescription,
)
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).parent
STATE = HERE / ".d4_state.json"

# Keep the run small. Both names come from the Learn sample.
ATTACK_STRATEGIES = ["Flip", "IndirectJailbreak"]
# Agentic categories are single-turn per Learn; the Learn sample uses 5. If 1 is rejected, use 5.
NUM_TURNS = 1

endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
judge_deployment = os.environ["CHAT_DEPLOYMENT"]
state = json.loads(STATE.read_text())

with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=endpoint, credential=credential) as project,
    project.get_openai_client() as client,
):
    # 1. The red team: holds the runs and the evaluators that score them.
    red_team = client.evals.create(
        name="D4 red team: travel assistant",
        data_source_config={"type": "azure_ai_source", "scenario": "red_team"},
        testing_criteria=[
            {
                "type": "azure_ai_evaluator",
                "name": "Prohibited Actions",
                "evaluator_name": "builtin.prohibited_actions",
                "evaluator_version": "1",
            },
            {
                "type": "azure_ai_evaluator",
                "name": "Task Adherence",
                "evaluator_name": "builtin.task_adherence",
                "evaluator_version": "1",
                "initialization_parameters": {"deployment_name": judge_deployment},
            },
            {
                "type": "azure_ai_evaluator",
                "name": "Sensitive Data Leakage",
                "evaluator_name": "builtin.sensitive_data_leakage",
                "evaluator_version": "1",
            },
        ],
    )
    print(f"Red team: {red_team.id}")

    # 2. The target: our agent, and what its tool does.
    target = AzureAIAgentTarget(
        name=state["agent_name"],
        version=state["agent_version"],
        tool_descriptions=[
            ToolDescription(
                name="file_search",
                description="Searches the Example Ltd travel and expense policy document.",
            )
        ],
    )

    # 3. The taxonomy: the service generates prohibited actions for this agent and its tools.
    taxonomy = project.beta.evaluation_taxonomies.create(
        name=state["agent_name"],
        body=EvaluationTaxonomy(
            description="D4 taxonomy for the travel assistant",
            taxonomy_input=AgentTaxonomyInput(
                risk_categories=[RiskCategory.PROHIBITED_ACTIONS],
                target=target,
            ),
        ),
    )
    print(f"Taxonomy: {taxonomy.id}")

    # 4. The run: attack prompts from the taxonomy, converted by the attack strategies.
    eval_run = client.evals.runs.create(
        eval_id=red_team.id,
        name="D4 run: Flip + IndirectJailbreak",
        data_source={
            "type": "azure_ai_red_team",
            "item_generation_params": {
                "type": "red_team_taxonomy",
                "attack_strategies": ATTACK_STRATEGIES,
                "num_turns": NUM_TURNS,
                "source": {"type": "file_id", "id": taxonomy.id},
            },
            "target": target.as_dict(),
        },
    )
    print(f"Run: {eval_run.id}, status: {eval_run.status}")

    state.update({
        "red_team_id": red_team.id,
        "run_id": eval_run.id,
        "taxonomy_name": state["agent_name"],
    })
    STATE.write_text(json.dumps(state, indent=2))

    # 5. Poll. The run is processed server-side.
    while True:
        run = client.evals.runs.retrieve(run_id=eval_run.id, eval_id=red_team.id)
        print(f"Status: {run.status}")
        if run.status in ("completed", "failed", "canceled"):
            break
        time.sleep(15)

    print(f"Report: {run.report_url}")
