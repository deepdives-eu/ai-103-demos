# D1 · Evaluation as a CI gate

deepdives.eu demo for AI-103 · our own material, not Microsoft Official Courseware.

Goes with the deepdives.eu video "Plan and manage Foundry solutions" in the AI-103 playlist.

**Goal:** a pull request changes an agent's instructions, GitHub Actions evaluates the new agent version against the current one, and the check goes red when quality drops below a threshold.

## Exam skill

AI-103, Plan and manage an Azure AI solution › Set up AI solutions in Foundry:

> Integrate Foundry projects with continuous integration and continuous deployment (CI/CD) pipelines

Also touches Implement generative AI and agentic solutions › Build agents by using Foundry: "Integrate monitoring into deployed agents, evaluate agent behavior, and perform error analysis".

## What it costs and why

Tokens only, all on the shared `gpt-5.4-mini` Global Standard deployment. It is an Azure-sold model, billed per token on your subscription. Nothing is billed by the hour. Delete the resources afterwards (see Cleanup).

Per workflow run:

| What | Calls |
| --- | --- |
| Action: both agent versions answer the 10 queries | 20 agent responses |
| Action: 2 evaluators judge every response | 40 judge calls |
| Gate: the candidate answers the 10 queries again | 10 agent responses |
| Gate: 1 evaluator judges them | 10 judge calls |

So roughly 30 short agent answers and 50 judge calls per run. Plan for 2 to 4 runs in total (one run on `main`, one failing PR, maybe a repeat). Ways it stays small:

- Two LLM-judge quality evaluators in the report, one in the gate, all judged by your own deployment. No risk and safety evaluators.
- 10 rows, inline in the request, so no dataset upload.
- The workflow runs only on pull requests that touch `agent/`, `eval/` or the workflow, plus manual runs. Learn's tip: don't evaluate on every commit.
- A prompt agent is a definition on the shared deployment; nothing runs between evaluations.
- GitHub Actions minutes: a private repo uses the minutes included in your plan; each run is a few minutes on `ubuntu-latest`.

## What's in this folder

```
README.md          this guide
setup_oidc.sh      Entra app + federated credential + Foundry User role + GitHub environment, secrets, variables
cleanup.sh         removes the role assignment, the app and the agent
delete_agent.py    deletes the agent and all its versions (called by cleanup.sh)
bad-pr/            the worse instructions for the failing pull request
repo/              everything that goes into the demo GitHub repo
  .github/workflows/agent-eval.yml
  agent/instructions.md       the good instructions (version 1, the baseline)
  eval/data.json              10 queries + evaluators, in the format the Action reads
  scripts/create_agent.py     creates a new agent version, prints name:version
  scripts/gate.py             runs one cloud evaluation and exits 1 below the pass rate
  requirements.txt
```

## Why there's a separate gate step

The Learn article for `microsoft/ai-agent-evals` documents its inputs and its output (a report in the job summary with scores, confidence intervals and a pairwise comparison). It doesn't document a threshold input or an output that fails the job. `evaluator_parameters` in the data file sets evaluator thresholds, which changes pass/fail labels in the report, not the job result.

Learn's own gate is the azd evaluation extension (`azd ai eval run show ... --fail-on pass-rate=0.8`). This demo doesn't use it because it needs an azd project and `evals/azure.eval.yaml`, and Learn says `azd ai eval run start` targets the agent by name and doesn't pin a version. We want to gate one exact version.

So `scripts/gate.py` is the smallest extra step: one cloud evaluation of the candidate `name:version` with the Foundry SDK (`azure_ai_target_completions` with an `azure_ai_agent` target), one evaluator (intent resolution), then it reads `result_counts` and exits 1 if `passed / total` is below 0.8. That's the same pass-rate definition the azd gate uses. A non-zero exit fails the step, the job and the PR check.

## Prerequisites

- The shared project from `../common/setup.sh`, and `../common/demo.env` filled in.
- Azure CLI signed in as someone who can register an app in Entra ID and create role assignments on the Foundry resource (`Microsoft.Authorization/roleAssignments/write`, for example Owner or Role Based Access Control Administrator).
- GitHub CLI signed in as an admin of the demo repo (to create the environment, secrets and variables).
- Python 3 with a venv.
- An empty GitHub repo for the demo, e.g. `<your-account>/ai103-d1-eval-gate` (private). The workflow has to sit at the repo root, so it can't live in this demos repo.

No local tools? Azure Cloud Shell (Bash) works too. It has the Azure CLI, Git, the GitHub CLI and Python, and the Azure CLI is already signed in. Things to know:

- Run `gh auth login` first. Cloud Shell signs you in to Azure, not to GitHub.
- Use Cloud Shell with a storage account, so the venv and the clone are still there next time. Without one, files go when the session ends.
- The session closes after 20 minutes without input. Keep the tab active while `gh run watch` is waiting.
- Check `python3 --version`. The current Azure SDK packages need Python 3.10 or later. On an older Python, pip falls back to older versions, and if the install fails, run the setup locally instead.

## Setup

```bash
cd D1-eval-ci-gate
DEMO_DIR=$(pwd)
python3 -m venv .venv && source .venv/bin/activate
pip install -r repo/requirements.txt
set -a; source ../common/demo.env; set +a

# 1. Demo repo with the files from repo/
gh repo create <your-account>/ai103-d1-eval-gate --private
git clone https://github.com/<your-account>/ai103-d1-eval-gate ~/work/ai103-d1-eval-gate
cp -R repo/. ~/work/ai103-d1-eval-gate/
(cd ~/work/ai103-d1-eval-gate && git add -A && git commit -m "Cost assistant agent, eval data and gate workflow" && git push)

# 2. Baseline agent, version 1, from the good instructions
python repo/scripts/create_agent.py --instructions repo/agent/instructions.md
# prints d1-cost-assistant:1  (if it prints another version, pass that number below)

# 3. OIDC, role assignment, GitHub environment d1-eval with secrets and variables
GH_REPO=<your-account>/ai103-d1-eval-gate ./setup_oidc.sh 1

# 4. First run on main: should pass (same instructions, so it evaluates version 1 only)
gh workflow run agent-eval.yml --repo <your-account>/ai103-d1-eval-gate
gh run watch --repo <your-account>/ai103-d1-eval-gate
```

What `setup_oidc.sh` does, in order:

1. `az ad app create` and `az ad sp create`: an app registration with a service principal. No client secret.
2. `az ad app federated-credential create`: trust tokens from `https://token.actions.githubusercontent.com` with audience `api://AzureADTokenExchange` and subject `repo:<owner>@<owner_id>/<repo>@<repo_id>:environment:d1-eval`. A new repo gets GitHub's immutable subject format (owner and repo IDs), so the script reads both IDs with `gh api`. For an older repo that hasn't opted in, set `SUBJECT=repo:<owner>/<repo>:environment:d1-eval` first.
3. `az role assignment create`: Foundry User (role ID `53ca6127-db72-4b80-b1b0-d745d6d5456d`) on the Foundry resource. Learn says evaluations that call a model deployment need it at account scope; a project-only assignment doesn't authorise inference. It also covers creating agent versions.
4. GitHub environment `d1-eval`, environment secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `FOUNDRY_PROJECT_ENDPOINT`, and variables `CHAT_DEPLOYMENT`, `BASELINE_VERSION`. They are secrets so the endpoint and IDs are masked in the logs.

Prepare the failing branch, but don't push it yet:

```bash
cd ~/work/ai103-d1-eval-gate
git switch -c shorter-answers
cp "$DEMO_DIR/bad-pr/instructions.md" agent/instructions.md
git commit -am "Shorter answers, send cost questions to sales"
```

Optional: in the repo's branch rules, make the "evaluate" check required on `main`, so the merge button is blocked, not just red.

If a step fails:

- **The run is rejected when it starts the evaluation.** `gate.py` combines inline data (`file_content`) with an agent target (`azure_ai_target_completions`). Learn shows both, but its agent-target example uses `file_id`. If the run is rejected, upload the queries with `project.datasets.upload_file(...)` and use `{"type": "file_id", "id": ...}`.
- **The report step fails with "missing required parameters for evaluators".** The judge deployment is missing. The action is supposed to look up what each evaluator needs and fill in `deployment-name`, but with current versions of the Azure SDK that lookup fails ("Could not fetch metadata ... Using defaults" in the log), so nothing gets filled in. That's why `eval/data.json` sets `deployment_name` for each evaluator under `evaluator_parameters`. If your deployment has a different name, change it there too.
- **The evaluators error out.** Learn says AI-assisted evaluators need a judge deployment that supports structured outputs. The demos use `gpt-5.4-mini` for that. Check that the deployment exists and that `CHAT_DEPLOYMENT` names it.
- **`azure/login` is rejected.** The immutable subject with an environment is built from the Learn pattern (`repo:<owner>@<owner_id>/<repo>@<repo_id>:...`). Compare the credential's subject with the one GitHub shows in the repo's OIDC settings and fix the credential.
- **The good instructions fail the gate, or the bad ones pass.** The good instructions should pass at 0.80 and the bad ones clearly fail. If not, change the bad instructions, not the threshold.

## Steps

1. **Look at the repo.** Open `agent/instructions.md`, then `eval/data.json`.
   The agent is a small prompt agent that answers Azure cost questions. Its instructions live in the repo, like any other code. The data file holds ten test questions. One of them is off topic on purpose.

2. **Look at the workflow.** Open `.github/workflows/agent-eval.yml` and read it top to bottom.
   It runs on pull requests that touch the agent or the test data, not on every commit, because every run costs tokens. First it creates a new agent version from the instructions in the PR. Then the Foundry evaluation action compares it with version 1, the baseline. Then the gate script decides pass or fail.

3. **Check there are no secrets.** Find `id-token: write` and the `azure/login` step in the workflow. Then open the app in the Entra admin center, under **Certificates & secrets › Federated credentials**. You see the subject and no client secret.
   GitHub hands the job a token, and Entra trusts it because of this federated credential. It only matches jobs in this repo, in the `d1-eval` environment. The app has one role: Foundry User on the Foundry resource.

4. **Read the gate script.** Open `scripts/gate.py` and find the `result_counts` and `return 1` lines.
   The action gives you a report, but it doesn't fail the build on a score. The gate evaluates the new version on the same questions, works out the pass rate, and exits with an error below 80 percent. That error is what turns the check red.

5. **Open the bad PR.**
   ```bash
   git push -u origin shorter-answers
   gh pr create --fill
   ```
   Open the PR and look at the diff. The change sounds harmless: shorter answers, and send people to sales.

6. **Watch the run.** Open the check from the PR. The step "Create candidate agent version" prints `d1-cost-assistant:N`. The evaluation takes a few minutes.
   The pipeline created version N of the agent. Now both versions answer the same ten questions, and a judge model scores them.

7. **Read the report.** Open the run's **Summary** and find the ai-agent-evals table.
   It compares intent resolution and task adherence for version 1 and the new version, with confidence intervals. With only ten questions the intervals are wide. For a real gate you want more rows.

8. **Read the gate result.** Scroll to the gate lines in the summary, then go back to the PR.
   The new version passes far fewer rows than the gate requires. The step fails, so the check is red, and this agent version should not be merged. Nobody had to read thirty answers to catch it.

9. **Close the PR without merging.**
   If a change passes, you merge it and promote that version as the new baseline. Production stays pinned to a version you've tested.

## Expected output

"Create candidate agent version" step:

```
d1-cost-assistant:2
```

Foundry only adds a version when the definition changes. The run on `main` uses the same instructions as the baseline, so it gets version 1 back. The workflow then passes only version 1 to the action (it can't compare a version with itself), and the report has no comparison. The failing PR makes version 2. A retake with different instructions makes the next number.

"Quality gate" step and job summary, failing PR (numbers will vary):

```
Waiting for the evaluation run... in_progress
...
**Quality gate for d1-cost-assistant:2**
Intent resolution: 2 of 10 rows passed, pass rate 0.20 (minimum 0.80)
[Open the run in Foundry](https://ai.azure.com/...)
Result: **failed**. Don't merge this agent version.
Error: Process completed with exit code 1.
```

Run on `main`: pass rate at or above 0.80 and `Result: **passed**.` The off-topic question should still pass intent resolution, because the agent recognises it and says where to ask instead. If the run on `main` lands below 0.80, look at the failed rows in Foundry before changing the threshold.

The ai-agent-evals summary shows one table per evaluator with both agent IDs, scores, confidence intervals and the pairwise comparison against the baseline.

## Cleanup

```bash
cd D1-eval-ci-gate && source .venv/bin/activate
./cleanup.sh
```

Removes the Foundry User assignment, the service principal and app registration (with its federated credential), and the `d1-cost-assistant` agent with all versions. The evaluation runs stay in the project's evaluation list; delete them in the portal if you want it tidy. Archive or delete the GitHub repo yourself. The shared project stays for the other demos.

## Sources

Microsoft Learn:

- How to run an evaluation in GitHub Action (preview): https://learn.microsoft.com/azure/foundry/how-to/evaluation-github-action
- Run agent evaluations with the azd CLI (preview), "Gate a build": https://learn.microsoft.com/azure/foundry/observability/how-to/azure-developer-cli-evaluation
- Cloud evaluation, SDK client setup (`azure-ai-projects>=2.2.0`): https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation
- Evaluate model and agent targets: https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-targets
- Provide data inline: https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-datasets#provide-data-inline
- Get cloud evaluation results (polling, `result_counts`, pass rate): https://learn.microsoft.com/azure/foundry/observability/how-to/cloud-evaluation-results
- Azure Cloud Shell overview (signed in, 20-minute timeout): https://learn.microsoft.com/azure/cloud-shell/overview
- Cloud Shell preinstalled tools: https://learn.microsoft.com/azure/cloud-shell/features#preinstalled-tools
- Cloud Shell FAQ (files without a storage account): https://learn.microsoft.com/azure/cloud-shell/faq-troubleshooting
- Agent evaluators (intent resolution, task adherence): https://learn.microsoft.com/azure/foundry/concepts/evaluation-evaluators/agent-evaluators
- Permissions for evaluation workflows: https://learn.microsoft.com/azure/foundry/observability/how-to/evaluation-permissions
- Role-based access control for Foundry (role IDs, Foundry User): https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry
- Create an agent (`agents.create_version`, `PromptAgentDefinition`): https://learn.microsoft.com/azure/foundry/agents/concepts/runtime-components#create-an-agent
- Delete agent versions: https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code#clean-up-resources
- Azure Login action with OpenID Connect: https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect
- Configure an app to trust an external identity provider (Azure CLI): https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust?pivots=identity-wif-apps-methods-azcli
- Immutable GitHub subjects: https://learn.microsoft.com/entra/workload-id/workload-identities-github-immutable-subjects
- AI-103 study guide: https://learn.microsoft.com/credentials/certifications/resources/study-guides/ai-103

Other:

- The action: https://github.com/microsoft/ai-agent-evals
- GitHub OIDC reference (subject claim): https://docs.github.com/actions/reference/security/oidc
- GitHub CLI (`gh repo create`, `gh secret set`, `gh variable set`, `gh api`): https://cli.github.com/manual/

Checked against Learn on 2026-11-07.
