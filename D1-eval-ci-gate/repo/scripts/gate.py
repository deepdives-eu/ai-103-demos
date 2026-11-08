"""Quality gate: evaluate one agent version and fail the job below a pass rate.

The microsoft/ai-agent-evals action writes a report but doesn't document a
threshold that fails the job. This script is the smallest step that does:
it runs a cloud evaluation of one agent version on the same queries
(eval/data.json), reads the pass rate and exits 1 when it's too low.

One evaluator only (intent resolution, 1-5 scale, pass at the default
threshold) to keep the judge cost down. Inline data, so no dataset upload.

Env: FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT (judge model).
Exit codes: 0 gate passed, 1 gate failed (quality), 2 run didn't complete.

Sources:
https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation#set-up-the-sdk-client
https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-targets#evaluate-an-agent-target
https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets#provide-data-inline
https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-results
"""
import argparse
import json
import os
import sys
import time

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import TestingCriterionAzureAIEvaluator
from azure.identity import DefaultAzureCredential
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    SourceFileContent,
    SourceFileContentContent,
)


def summary(line: str) -> None:
    """Print a line and add it to the GitHub job summary when running in Actions."""
    print(line)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as out:
            out.write(line + "\n\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, help="agent ID as name:version")
    parser.add_argument("--data", default="eval/data.json", help="ai-agent-evals data file")
    parser.add_argument("--min-pass-rate", type=float, default=0.8)
    args = parser.parse_args()

    name, _, version = args.agent.partition(":")
    queries = [row["query"] for row in json.load(open(args.data, encoding="utf-8"))["data"]]
    judge = os.environ["CHAT_DEPLOYMENT"]

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"], credential=credential) as project,
    ):
        client = project.get_openai_client()

        eval_object = client.evals.create(
            name="d1-quality-gate",
            data_source_config=DataSourceConfigCustom(
                type="custom",
                item_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                include_sample_schema=True,
            ),
            testing_criteria=[
                TestingCriterionAzureAIEvaluator(
                    type="azure_ai_evaluator",
                    name="intent_resolution",
                    evaluator_name="builtin.intent_resolution",
                    initialization_parameters={"deployment_name": judge},
                    data_mapping={
                        "query": "{{item.query}}",
                        "response": "{{sample.output_text}}",
                    },
                ),
            ],
        )

        run = client.evals.runs.create(
            eval_id=eval_object.id,
            name=f"gate-{name}-v{version}",
            data_source={
                "type": "azure_ai_target_completions",
                "source": SourceFileContent(
                    type="file_content",
                    content=[SourceFileContentContent(item={"query": q}) for q in queries],
                ),
                "input_messages": {
                    "type": "template",
                    "template": [
                        {
                            "type": "message",
                            "role": "user",
                            "content": {"type": "input_text", "text": "{{item.query}}"},
                        }
                    ],
                },
                "target": {"type": "azure_ai_agent", "name": name, "version": version},
            },
        )

        while run.status not in ("completed", "failed", "canceled"):
            time.sleep(10)
            run = client.evals.runs.retrieve(run_id=run.id, eval_id=eval_object.id)
            print(f"Waiting for the evaluation run... {run.status}")

    if run.status != "completed":
        print(f"Evaluation run ended in {run.status}: {run.error}")
        return 2

    data = run.to_dict()
    counts = data.get("result_counts") or {}
    total = counts.get("total") or len(queries)
    passed = counts.get("passed", 0)
    rate = passed / total if total else 0.0

    summary(f"**Quality gate for {args.agent}**")
    summary(f"Intent resolution: {passed} of {total} rows passed, pass rate {rate:.2f} (minimum {args.min_pass_rate:.2f})")
    if data.get("report_url"):
        summary(f"[Open the run in Foundry]({data['report_url']})")

    if rate < args.min_pass_rate:
        summary("Result: **failed**. Don't merge this agent version.")
        return 1
    summary("Result: **passed**.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
