#!/usr/bin/env bash
# Base for all AI-103 demos: one Foundry resource and project in Sweden Central,
# a chat model and an embedding model, Global Standard (pay per token, no idle cost).
# Per-demo extras (Application Insights, AI Search) go in their own resource group
# and are deleted when the demo is done. Run once; safe to re-run.
#
# Source: https://learn.microsoft.com/azure/foundry/how-to/create-projects
set -euo pipefail
cd "$(dirname "$0")"
[ -f demo.env ] || cp demo.env.example demo.env
source demo.env

az group create -n "$RG" -l "$LOCATION" -o none

az cognitiveservices account create -n "$FOUNDRY" -g "$RG" -l "$LOCATION" \
  --kind AIServices --sku S0 --custom-domain "$FOUNDRY" \
  --assign-identity --allow-project-management true --yes -o none

az cognitiveservices account project create -n "$FOUNDRY" -g "$RG" \
  --project-name "$PROJECT" -l "$LOCATION" -o none

deploy() {  # name model version capacity(thousands TPM)
  az cognitiveservices account deployment create -n "$FOUNDRY" -g "$RG" \
    --deployment-name "$1" --model-name "$2" --model-version "$3" --model-format OpenAI \
    --sku-name GlobalStandard --sku-capacity "$4" -o none
}
deploy "$CHAT_DEPLOYMENT" gpt-5.4-mini 2026-03-17 50
deploy "$EMBED_DEPLOYMENT" text-embedding-3-small 1 50

# Keyless: Foundry User (role ID, because the name changed) at the Foundry resource scope,
# which evaluations need, for you and for the project's managed identity (memory needs it).
ACCOUNT_ID=$(az cognitiveservices account show -n "$FOUNDRY" -g "$RG" --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --role 53ca6127-db72-4b80-b1b0-d745d6d5456d \
  --assignee-object-id "$ME" --assignee-principal-type User --scope "$ACCOUNT_ID" -o none || true
PROJECT_MI=$(az cognitiveservices account project show -n "$FOUNDRY" -g "$RG" --project-name "$PROJECT" \
  --query identity.principalId -o tsv)  # empty? enable the project identity in the portal (Resource Management > Identity) and re-run
az role assignment create --role 53ca6127-db72-4b80-b1b0-d745d6d5456d \
  --assignee-object-id "$PROJECT_MI" --assignee-principal-type ServicePrincipal --scope "$ACCOUNT_ID" -o none || true

echo "FOUNDRY_PROJECT_ENDPOINT=https://$FOUNDRY.services.ai.azure.com/api/projects/$PROJECT"
