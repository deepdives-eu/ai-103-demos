"""Create a new version of the D1 prompt agent from an instructions file.

Prints the agent ID in name:version format, which is what the
microsoft/ai-agent-evals action expects. In GitHub Actions it also writes
agent_id and version to $GITHUB_OUTPUT so later steps can use them.

Env: FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT, AGENT_NAME (optional).
Auth: DefaultAzureCredential (az login locally, OIDC via azure/login in CI).

Sources:
https://learn.microsoft.com/azure/foundry/agents/concepts/runtime-components#create-an-agent
"""
import argparse
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instructions", required=True, help="path to the instructions file")
    parser.add_argument("--name", default=os.environ.get("AGENT_NAME", "d1-cost-assistant"))
    args = parser.parse_args()

    instructions = Path(args.instructions).read_text(encoding="utf-8").strip()

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential) as project,
    ):
        agent = project.agents.create_version(
            agent_name=args.name,
            definition=PromptAgentDefinition(
                model=os.environ["CHAT_DEPLOYMENT"],
                instructions=instructions,
            ),
        )

    agent_id = f"{agent.name}:{agent.version}"
    print(agent_id)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as out:
            out.write(f"agent_id={agent_id}\n")
            out.write(f"version={agent.version}\n")


if __name__ == "__main__":
    main()
