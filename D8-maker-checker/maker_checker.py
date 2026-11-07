"""D8 Maker-checker loop: a writer and a reviewer in an Agent Framework group chat.

The writer (maker) drafts a short product text. The reviewer (checker) scores the draft
against explicit acceptance criteria and returns a structured verdict. The loop goes
writer -> reviewer -> writer ... until the reviewer approves or the review cap is reached.

  python maker_checker.py run                   loop with a cap of 3 reviews
  python maker_checker.py run --max-reviews 1   same loop, cap of 1: shows the fallback

Nothing is created in the Foundry project: the agents live in this process and call the
model deployment through the project's Responses endpoint. Keyless (DefaultAzureCredential).
Env vars from ../common/demo.env: FOUNDRY_PROJECT_ENDPOINT, CHAT_DEPLOYMENT.

Follows https://learn.microsoft.com/agent-framework/workflows/orchestrations/group-chat (Python)
and https://learn.microsoft.com/agent-framework/agents/structured-outputs (Python).
"""

import argparse
import asyncio
import os

from agent_framework import Agent, AgentResponseUpdate
from agent_framework.foundry import FoundryChatClient
from agent_framework.orchestrations import GroupChatBuilder, GroupChatState
from azure.identity import DefaultAzureCredential
from pydantic import BaseModel, ValidationError

WRITER = "Writer"
REVIEWER = "Reviewer"

# The brief goes to both agents. Only the reviewer holds the acceptance criteria,
# so the first draft usually misses some and the loop has something to do.
TASK = (
    "Write the product text for a web shop: a 750 ml steel water bottle that keeps "
    "drinks cold for 24 hours and weighs 340 grams."
)

CRITERIA = [
    "At most 40 words.",
    "States both facts exactly: 24 hours cold and 340 grams.",
    "No superlatives or hype words such as best, ultimate, revolutionary or perfect.",
    "Ends with a call to action.",
]


class CriterionCheck(BaseModel):
    criterion: str
    passed: bool
    comment: str


class Verdict(BaseModel):
    """What the reviewer must return. The code decides on this, not on the wording."""

    approved: bool
    checks: list[CriterionCheck]
    feedback: str


def make_agents():
    client = FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=os.environ["CHAT_DEPLOYMENT"],
        credential=DefaultAzureCredential(),
    )
    writer = Agent(
        client=client,
        name=WRITER,
        description="Drafts and revises the product text.",
        instructions="You write short product texts for a web shop. "
        "If the last message is feedback from the Reviewer, revise your latest draft "
        "and fix every check that failed. Reply with the product text only.",
    )
    criteria = "\n".join(f"{i}. {c}" for i, c in enumerate(CRITERIA, 1))
    reviewer = Agent(
        client=client,
        name=REVIEWER,
        description="Checks the latest draft against the acceptance criteria.",
        instructions="You review the Writer's latest draft against these acceptance criteria:\n"
        f"{criteria}\n"
        "Check each criterion separately and say why it passed or failed. "
        "Set approved to true only if every criterion passed. "
        "In feedback, tell the Writer exactly what to change. Don't rewrite the text yourself.",
        # Structured output: every reviewer turn is a JSON Verdict.
        default_options={"response_format": Verdict},
    )
    return writer, reviewer


def parse_verdict(text):
    try:
        return Verdict.model_validate_json(text)
    except ValidationError:
        return None  # treated as "not approved"


def is_approved(verdict):
    # Belt and braces: approved only if the flag and every single check agree.
    return verdict is not None and verdict.approved and all(c.passed for c in verdict.checks)


def select_next(state: GroupChatState) -> str:
    """Strict turns: the writer starts, and the reviewer always answers the writer."""
    last = state.conversation[-1] if state.conversation else None
    if last is not None and last.author_name == WRITER:
        return REVIEWER
    return WRITER


def make_termination(max_reviews):
    def done(conversation) -> bool:
        reviews = [m for m in conversation if m.role == "assistant" and m.author_name == REVIEWER]
        if not reviews:
            return False
        if is_approved(parse_verdict(reviews[-1].text)):
            return True
        return len(reviews) >= max_reviews  # the iteration cap

    return done


def print_turn(author, text, review_no):
    if author == REVIEWER:
        verdict = parse_verdict(text)
        print(f"\n[{REVIEWER} {review_no}]")
        if verdict is None:
            print("  (no valid verdict, counts as not approved)")
            return
        for c in verdict.checks:
            print(f"  {'PASS' if c.passed else 'FAIL'}  {c.criterion} - {c.comment}")
        print(f"  approved: {is_approved(verdict)}")
        if not is_approved(verdict):
            print(f"  feedback: {verdict.feedback}")
    else:
        print(f"\n[{author}]\n{text.strip()}")


async def run(max_reviews):
    writer, reviewer = make_agents()
    workflow = GroupChatBuilder(
        participants=[writer, reviewer],
        selection_func=select_next,
        termination_condition=make_termination(max_reviews),
        max_rounds=2 * max_reviews + 2,  # hard backstop; the termination condition is the real cap
        intermediate_output_from=[writer, reviewer],
    ).build()

    print(f"Task: {TASK}\nReview cap: {max_reviews}")

    # Stream the turns, as in the Learn sample, and print each one when it is complete.
    turns, author, buffer = [], None, []
    stream = workflow.run(TASK, stream=True)
    async for event in stream:
        if event.type in ("intermediate", "output") and isinstance(event.data, AgentResponseUpdate):
            if event.data.author_name != author:
                if author is not None:
                    turns.append((author, "".join(buffer)))
                author, buffer = event.data.author_name, []
            buffer.append(event.data.text or "")
    if author is not None:
        turns.append((author, "".join(buffer)))
    await stream.get_final_response()

    drafts, verdicts = [], []
    for who, text in turns:
        if who == WRITER:
            drafts.append(text)
        elif who == REVIEWER:
            verdicts.append(parse_verdict(text))
        print_turn(who, text, len(verdicts))

    print("\n" + "=" * 72)
    if verdicts and is_approved(verdicts[-1]):
        print(f"Approved after {len(verdicts)} review(s). Final text:\n{drafts[-1].strip()}")
    else:
        # Fallback when the cap is reached: don't ship it, hand the best draft to a person.
        print(f"Not approved after {len(verdicts)} review(s): cap reached.")
        print("Fallback: send the last draft and the open feedback to a human reviewer.")
        if drafts:
            print(f"Last draft:\n{drafts[-1].strip()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["run"])
    parser.add_argument("--max-reviews", type=int, default=3)
    args = parser.parse_args()
    asyncio.run(run(args.max_reviews))
