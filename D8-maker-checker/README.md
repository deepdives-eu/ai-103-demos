# D8 Maker-checker loop

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video 'Agents: memory, evaluation and orchestration' in the AI-103 playlist.

**Goal:** a writer agent and a reviewer agent go back and forth until the reviewer approves the text, with a cap on the number of reviews and a fallback when the cap is reached.

**Exam skills** (AI-103 study guide, skills measured as of April 16, 2026):

- Implement generative AI and agentic solutions > Optimize and operationalize generative AI systems: "Implement model reflection, chain-of-thought evaluations, and self-critique loops"
- Implement generative AI and agentic solutions > Build agents by using Foundry: "Implement orchestrated multi-agent solutions"

**How this differs from the course lab.** The official multi-agent lab with Microsoft Agent Framework (lab 2.8) chains three agents in a fixed order, each running once, with a sequential orchestration. Nothing goes back to an earlier agent and nobody reviews the result. This demo adds the part the lab leaves out: a reviewer with explicit acceptance criteria, a loop back to the writer, and a stop condition.

## What it costs and why

Tokens only, on the shared `gpt-5.4-mini` Global Standard deployment in your subscription.

- **One run** is at most 2 model calls per review (one draft, one review). With the default cap of 3 that is at most 6 calls, usually fewer. Each call gets the whole conversation so far, so later calls are a bit bigger, but the texts are under 40 words.
- **Step 4** runs once more with a cap of 1: 2 calls.
- **Nothing hourly, nothing to delete.** The agents are Agent Framework objects in your Python process, not agents in Foundry Agent Service. They call the model through the project endpoint.

The demo uses an Azure OpenAI model sold directly by Azure, on a Global Standard deployment only.

## Prerequisites

- The shared demo project from `../common/setup.sh` (Sweden Central, `gpt-5.4-mini`).
- You (the signed-in user) have Foundry User on the Foundry resource. `../common/setup.sh` does that.
- **Python 3.11 or later.** The repo's general minimum is 3.10, but Agent Framework no longer supports 3.10.
- Azure CLI signed in (`az login`).

## Setup

```bash
cd D8-maker-checker
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../common/demo.env; set +a
```

## Steps

1. **Read the code: two agents.** Open `maker_checker.py` and scroll to `make_agents()`.
   Both agents use one `FoundryChatClient`, which points at the project endpoint and the `gpt-5.4-mini` deployment. The writer only gets the brief. The reviewer gets the acceptance criteria: at most 40 words, both facts exact, no hype words, a call to action. The reviewer has `default_options={"response_format": Verdict}`, so every review comes back as structured output: `approved`, one check per criterion, and `feedback`. Scroll up to the `Verdict` class to see the schema.

2. **Read the code: the loop.** Look at `select_next`, `make_termination` and the `GroupChatBuilder` call in `run()`.
   This is a group chat orchestration with two participants. `selection_func` picks who speaks next: the writer starts, and after every draft the reviewer answers. `termination_condition` gets the whole conversation, parses the reviewer's last verdict and stops when it is approved. If not, it stops once the number of reviews reaches the cap. `is_approved` only accepts the verdict when `approved` is true and every check passed, so the decision is made in code, not by looking for the word "approved". `max_rounds` is a hard backstop on top of that.

3. **Run `python maker_checker.py run`.** The loop with a cap of 3 reviews.
   Expected: `[Writer]` with a first draft, `[Reviewer 1]` with a `PASS` or `FAIL` line per criterion and the feedback, a revised draft, and so on. The last lines are `Approved after n review(s). Final text:` and the approved text. Model output varies; a run can be approved after the first review, or need all three.
   If this step fails: with an authentication error, run `az login` and check that you have Foundry User on the Foundry resource (role assignments can take a few minutes). With `ModuleNotFoundError: agent_framework.orchestrations`, check that `pip install -r requirements.txt` ran in the active venv and that you are on Python 3.11 or later. With `no valid verdict` on every review, the model didn't return the schema; check that the deployment name in `CHAT_DEPLOYMENT` is the `gpt-5.4-mini` deployment.

4. **Run `python maker_checker.py run --max-reviews 1`.** The same loop, but the cap is one review.
   Expected: one draft, one review. If that review fails, the run ends with `Not approved after 1 review(s): cap reached.` and the fallback: the last draft and the open feedback go to a person. If the first draft happens to pass, run it again. This is the case every maker-checker loop needs an answer for: what happens when the checker never says yes.

5. **Wrap up, no command.** A maker, a checker with explicit criteria, a structured verdict, a cap and a fallback. That's the whole pattern. Agent Framework also has looping middleware with a judge (`AgentLoopMiddleware`) for the single-agent version; it is experimental.

## Cleanup

Nothing to delete. The agents exist only while the script runs. Leave the shared project and deployment; the other demos use them.

## Notes

- Why the reviewer doesn't rewrite the text: separate roles keep the feedback honest and the loop readable. The checker says what is wrong, the maker fixes it.
- Each extra review adds two model calls on a longer conversation. Keep the cap low and the criteria specific; vague criteria make the loop run to the cap.
- The group chat passes text only between participants. The reviewer's verdict reaches the writer as JSON text, which works fine as feedback.
- The Python API changed in 2026: the orchestration builders moved to `agent_framework.orchestrations`, and the builder options are constructor parameters now. Older samples with `.participants(...)` or `.with_max_rounds(...)` won't run on the current packages.

## Sources

Microsoft Learn:

- Group chat orchestration in Agent Framework (Python): https://learn.microsoft.com/agent-framework/workflows/orchestrations/group-chat
- Producing structured outputs with agents (Python, `response_format`, `default_options`): https://learn.microsoft.com/agent-framework/agents/structured-outputs
- Microsoft Foundry model provider (`FoundryChatClient`, `agent-framework-foundry`): https://learn.microsoft.com/agent-framework/integrations/by-component/model-providers/microsoft-foundry
- Python 2026 significant changes (builders in `agent_framework.orchestrations`, constructor parameters including `max_rounds`): https://learn.microsoft.com/agent-framework/support/upgrade/python-2026-significant-changes
- AI agent orchestration patterns, maker-checker loops: https://learn.microsoft.com/azure/architecture/ai-ml/guide/ai-agent-design-patterns#maker-checker-loops
- Agent looping (experimental): https://learn.microsoft.com/agent-framework/agents/looping
- Python version support: https://learn.microsoft.com/agent-framework/get-started/build-with-coding-agents
- Study guide for Exam AI-103: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Checked against Learn on 2026-11-07.
