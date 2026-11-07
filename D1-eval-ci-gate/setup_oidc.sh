#!/usr/bin/env bash
# D1 setup: an Entra app that GitHub Actions signs in as with OIDC (no secret),
# Foundry User on the shared Foundry resource, and the GitHub environment,
# secrets and variables the workflow reads.
#
# Usage: GH_REPO=<your-account>/ai103-d1-eval-gate ./setup_oidc.sh [baseline-version]
# Needs: az login (rights to register an app and to assign roles on the Foundry
# resource), gh auth login (admin on the repo), ../common/demo.env.
#
# Sources:
#   https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect
#   https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust?pivots=identity-wif-apps-methods-azcli
#   https://learn.microsoft.com/entra/workload-id/workload-identities-github-immutable-subjects
#   https://learn.microsoft.com/azure/foundry/observability/how-to/evaluation-permissions
#   https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry#manage-role-assignments
set -euo pipefail
cd "$(dirname "$0")"
source ../common/demo.env
: "${GH_REPO:?set GH_REPO=owner/repo}"
BASELINE_VERSION=${1:-1}
ENV_NAME=d1-eval
APP_NAME=ai103-d1-eval-gate
FOUNDRY_USER=53ca6127-db72-4b80-b1b0-d745d6d5456d   # Foundry User, by ID because the name changed

# 1. App registration and service principal
APP_ID=$(az ad app create --display-name "$APP_NAME" --sign-in-audience AzureADMyOrg --query appId -o tsv)
az ad sp create --id "$APP_ID" -o none
APP_OBJECT_ID=$(az ad app show --id "$APP_ID" --query id -o tsv)
SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv)

# 2. Federated credential for jobs that run in the d1-eval environment.
# Repos created after 15 July 2026 get GitHub's immutable subject format with
# owner and repo IDs. For an older repo that hasn't opted in, set
# SUBJECT=repo:<owner>/<repo>:environment:d1-eval before running this script.
OWNER=${GH_REPO%/*}; REPO=${GH_REPO#*/}
OWNER_ID=$(gh api "repos/$GH_REPO" --jq .owner.id)
REPO_ID=$(gh api "repos/$GH_REPO" --jq .id)
SUBJECT=${SUBJECT:-"repo:$OWNER@$OWNER_ID/$REPO@$REPO_ID:environment:$ENV_NAME"}
CRED=$(mktemp)
cat > "$CRED" <<JSON
{
  "name": "github-$REPO-$ENV_NAME",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "$SUBJECT",
  "description": "AI-103 demo D1, GitHub Actions environment $ENV_NAME",
  "audiences": ["api://AzureADTokenExchange"]
}
JSON
az ad app federated-credential create --id "$APP_OBJECT_ID" --parameters "$CRED" -o none
rm -f "$CRED"
echo "Federated credential subject: $SUBJECT"

# 3. Foundry User on the Foundry resource (account scope). Evaluations that call a
# model deployment need it there; a project-only assignment doesn't cover inference.
ACCOUNT_ID=$(az cognitiveservices account show -n "$FOUNDRY" -g "$RG" --query id -o tsv)
az role assignment create --role "$FOUNDRY_USER" \
  --assignee-object-id "$SP_OBJECT_ID" --assignee-principal-type ServicePrincipal \
  --scope "$ACCOUNT_ID" -o none

# 4. GitHub environment, secrets and variables (GitHub CLI)
gh api -X PUT "repos/$GH_REPO/environments/$ENV_NAME" > /dev/null
gh secret set AZURE_CLIENT_ID          --repo "$GH_REPO" --env "$ENV_NAME" --body "$APP_ID"
gh secret set AZURE_TENANT_ID          --repo "$GH_REPO" --env "$ENV_NAME" --body "$(az account show --query tenantId -o tsv)"
gh secret set AZURE_SUBSCRIPTION_ID    --repo "$GH_REPO" --env "$ENV_NAME" --body "$(az account show --query id -o tsv)"
gh secret set FOUNDRY_PROJECT_ENDPOINT --repo "$GH_REPO" --env "$ENV_NAME" --body "$FOUNDRY_PROJECT_ENDPOINT"
gh variable set CHAT_DEPLOYMENT  --repo "$GH_REPO" --env "$ENV_NAME" --body "$CHAT_DEPLOYMENT"
gh variable set BASELINE_VERSION --repo "$GH_REPO" --env "$ENV_NAME" --body "$BASELINE_VERSION"

echo "Done. App (client) ID: $APP_ID. Role assignments can take a few minutes to apply."
