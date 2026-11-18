"""D2: trace one agent run.

Creates a prompt agent with one local function tool on the shared Foundry project,
runs one question that needs the tool, and sends the client-side spans to the
Application Insights resource connected to the project. Prints the trace ID so the
same request can be found in the Foundry portal and with KQL.

Run:   python trace_one_run.py
Clean: python trace_one_run.py --delete-agent

Sources:
https://learn.microsoft.com/azure/foundry/observability/how-to/trace-agent-client-side
https://learn.microsoft.com/azure/foundry/agents/how-to/tools/function-calling?pivots=python
https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-configuration#connection-string
https://learn.microsoft.com/azure/azure-monitor/app/javascript-sdk#get-started (not a security token)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Tracing is an opt-in preview: the variable must be set before instrumentation.
os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "true"
# Demo only: record prompts, tool arguments and outputs in the spans.
# Learn: don't do this in production unless your compliance rules allow it.
os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")
# Shows up as cloud_RoleName / AppRoleName in Application Insights.
os.environ.setdefault("OTEL_SERVICE_NAME", "ai103-d2-trace-demo")

from azure.ai.projects import AIProjectClient  # noqa: E402
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition  # noqa: E402
from azure.ai.projects.telemetry import AIProjectInstrumentor, trace_function  # noqa: E402
from azure.identity import DefaultAzureCredential  # noqa: E402
from azure.monitor.opentelemetry import configure_azure_monitor  # noqa: E402
from openai.types.responses.response_input_param import FunctionCallOutput  # noqa: E402
from opentelemetry import trace  # noqa: E402
from opentelemetry._logs import get_logger_provider  # noqa: E402
from opentelemetry.metrics import get_meter_provider  # noqa: E402

AGENT_NAME = "d2-trace-demo"
STATE_FILE = Path(__file__).with_name(".last_run.json")  # local only, not committed
QUESTION = "How much of the AI-103 exam is about planning and managing an Azure AI solution?"

# Weights from the AI-103 study guide, skills measured as of April 16, 2026.
EXAM_WEIGHTS = {
    "plan and manage": "25-30%",
    "generative ai and agents": "30-35%",
    "computer vision": "10-15%",
    "text analysis": "10-15%",
    "information extraction": "10-15%",
}


@trace_function("lookup_exam_weight")
def get_exam_weight(skill_area: str) -> str:
    """Local function tool. @trace_function gives it its own span."""
    return EXAM_WEIGHTS.get(skill_area.lower(), "unknown skill area")


exam_weight_tool = FunctionTool(
    name="get_exam_weight",
    description="Get the exam weight of one AI-103 skill area.",
    parameters={
        "type": "object",
        "properties": {
            "skill_area": {
                "type": "string",
                "enum": list(EXAM_WEIGHTS),
                "description": "The AI-103 skill area.",
            },
        },
        "required": ["skill_area"],
        "additionalProperties": False,
    },
    strict=True,
)


def delete_agent(project: AIProjectClient) -> None:
    if not STATE_FILE.exists():
        print("Nothing to delete: no .last_run.json")
        return
    state = json.loads(STATE_FILE.read_text())
    with project.get_openai_client(agent_name=state["agent_name"]) as openai:
        try:
            openai.conversations.delete(conversation_id=state["conversation_id"])
        except Exception as err:  # already gone is fine
            print(f"Conversation not deleted: {err}")
    project.agents.delete_version(agent_name=state["agent_name"], agent_version=state["agent_version"])
    STATE_FILE.unlink()
    print(f"Deleted agent {state['agent_name']} version {state['agent_version']}")


def app_insights_connection_string(project: AIProjectClient) -> str:
    """The connection string of the Application Insights resource connected to the project.

    The SDK helper only reads connections that store the connection string as a key.
    The portal's Connect button can create the connection with the project's managed
    identity instead, and then the helper raises ValueError. In that case use
    APPLICATIONINSIGHTS_CONNECTION_STRING, the variable the Azure Monitor distro reads.
    Learn: the connection string isn't a security token or key.
    """
    try:
        conn = project.telemetry.get_application_insights_connection_string()
        print("Application Insights connection string: from the project connection")
        return conn
    except ValueError as err:
        conn = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")
        if conn:
            print(f"Application Insights connection string: from APPLICATIONINSIGHTS_CONNECTION_STRING ({err})")
            return conn
        sys.exit(
            f"{err}\nThe project connection uses managed identity. Set the connection string "
            "from the resource and run again:\n"
            "  export APPLICATIONINSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show "
            "-g rg-ai103-d2 --app appi-ai103-d2 --query connectionString -o tsv)"
        )


def run(project: AIProjectClient) -> None:
    # Client-side spans go to the Application Insights resource connected to the project.
    configure_azure_monitor(connection_string=app_insights_connection_string(project))
    AIProjectInstrumentor().instrument()
    tracer = trace.get_tracer(__name__)

    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=os.environ["CHAT_DEPLOYMENT"],
            instructions=(
                "You answer questions about the AI-103 exam. "
                "Always use the get_exam_weight tool for exam weights. Answer in one sentence."
            ),
            tools=[exam_weight_tool],
        ),
    )
    print(f"Agent: {agent.name} version {agent.version} (id: {agent.id})")

    # One root span around the whole run, so everything shares one trace ID.
    with tracer.start_as_current_span("d2-trace-one-run") as root:
        trace_id = format(root.get_span_context().trace_id, "032x")

        # Get the OpenAI client after instrument(), so trace context is propagated.
        with project.get_openai_client(agent_name=agent.name) as openai:
            conversation = openai.conversations.create()
            response = openai.responses.create(conversation=conversation.id, input=QUESTION)
            response_ids = [response.id]

            for _ in range(3):  # a few rounds at most; one is expected
                outputs = []
                for item in response.output:
                    if item.type == "function_call" and item.name == "get_exam_weight":
                        args = json.loads(item.arguments)
                        result = get_exam_weight(**args)
                        print(f"Tool call: get_exam_weight({args}) -> {result}")
                        outputs.append(
                            FunctionCallOutput(
                                type="function_call_output",
                                call_id=item.call_id,
                                output=json.dumps({"weight": result}),
                            )
                        )
                if not outputs:
                    break
                response = openai.responses.create(conversation=conversation.id, input=outputs)
                response_ids.append(response.id)

    print(f"Answer: {response.output_text}")
    if response.usage:
        print(f"Tokens (last response): input {response.usage.input_tokens}, output {response.usage.output_tokens}")
    print(f"Conversation ID: {conversation.id}")
    print(f"Response IDs: {', '.join(response_ids)}")
    print(f"Trace ID (operation_Id): {trace_id}")

    STATE_FILE.write_text(json.dumps({
        "agent_name": agent.name,
        "agent_version": agent.version,
        "conversation_id": conversation.id,
        "trace_id": trace_id,
    }))

    # Send the spans now instead of waiting for the batch exporter, then shut down.
    # Learn (troubleshooting OpenTelemetry in Python): shut down each provider.
    for provider in (trace.get_tracer_provider(), get_logger_provider(), get_meter_provider()):
        if hasattr(provider, "shutdown"):
            provider.shutdown()
    # The distro's logging handler flushes in a new thread when Python exits, which
    # fails at interpreter shutdown. Remove it; this script only sends traces.
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if type(handler).__module__.startswith("opentelemetry"):
            root_logger.removeHandler(handler)
    print("Spans sent. Traces typically take 2-5 minutes to show up.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-agent", action="store_true", help="delete the demo agent and conversation")
    args = parser.parse_args()

    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint or "CHANGEME" in endpoint:
        sys.exit("Set FOUNDRY_PROJECT_ENDPOINT: set -a; source ../common/demo.env; set +a")

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project,
    ):
        delete_agent(project) if args.delete_agent else run(project)


if __name__ == "__main__":
    main()
