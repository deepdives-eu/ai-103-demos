"""Delete the D1 agent and all its versions from the shared project.

Env: FOUNDRY_PROJECT_ENDPOINT, AGENT_NAME (optional).

Source:
https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code#clean-up-resources
"""
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

name = os.environ.get("AGENT_NAME", "d1-cost-assistant")
with (
    DefaultAzureCredential() as credential,
    AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential) as project,
):
    project.agents.delete(agent_name=name)
print(f"Deleted agent {name} and all its versions")
