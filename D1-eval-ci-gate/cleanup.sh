#!/usr/bin/env bash
# D1 cleanup: role assignment, Entra app (with its federated credential and
# service principal) and the D1 agent. Leaves the shared Foundry project and the
# GitHub repo alone; archive or delete the repo yourself.
#
# Usage: ./cleanup.sh   (needs az login and the same ../common/demo.env)
#
# Sources:
#   https://learn.microsoft.com/azure/foundry/how-to/evaluation-github-action#verify-the-gate
#   https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code#clean-up-resources
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a
APP_NAME=ai103-d1-eval-gate

APP_ID=$(az ad app list --display-name "$APP_NAME" --query "[0].appId" -o tsv)
if [ -n "$APP_ID" ]; then
  SP_OBJECT_ID=$(az ad sp show --id "$APP_ID" --query id -o tsv 2>/dev/null || true)
  ACCOUNT_ID=$(az cognitiveservices account show -n "$FOUNDRY" -g "$RG" --query id -o tsv)
  if [ -n "$SP_OBJECT_ID" ]; then
    az role assignment delete --assignee "$SP_OBJECT_ID" --scope "$ACCOUNT_ID" || true
    az ad sp delete --id "$SP_OBJECT_ID"
  fi
  az ad app delete --id "$APP_ID"
  echo "Deleted app registration $APP_NAME"
fi

python3 delete_agent.py
