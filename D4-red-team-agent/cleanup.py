"""D4 cleanup: delete what 01 and 02 created in the shared project, and the local files.

Leaves the Foundry resource, project and deployments alone (other demos in this repo can share them).
Sources:
  evals.delete: https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-synthetic-conversations#get-the-results
  agents.delete: https://learn.microsoft.com/azure/foundry/tutorials/developer-journey-idea-to-prototype
  vector_stores.delete: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/file-search?pivots=python
  evaluation_taxonomies.delete: https://learn.microsoft.com/python/api/azure-ai-projects/azure.ai.projects.operations.betaevaluationtaxonomiesoperations
"""

import json
import os
import shutil
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential

HERE = Path(__file__).parent
STATE = HERE / ".d4_state.json"

state = json.loads(STATE.read_text()) if STATE.exists() else {}
endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]


def attempt(label, fn):
    try:
        fn()
        print(f"Deleted {label}")
    except HttpResponseError as e:
        print(f"Skipped {label}: {e.message}")


with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=endpoint, credential=credential) as project,
    project.get_openai_client() as openai,
):
    if "red_team_id" in state:
        attempt("red team (eval and its runs)", lambda: openai.evals.delete(eval_id=state["red_team_id"]))
    if "taxonomy_name" in state:
        attempt("taxonomy", lambda: project.beta.evaluation_taxonomies.delete(name=state["taxonomy_name"]))
    if "agent_name" in state:
        attempt("agent (all versions)", lambda: project.agents.delete(agent_name=state["agent_name"]))
    if "vector_store_id" in state:
        attempt("vector store", lambda: openai.vector_stores.delete(state["vector_store_id"]))

shutil.rmtree(HERE / "out", ignore_errors=True)
STATE.unlink(missing_ok=True)
print("Local state and out/ removed")
