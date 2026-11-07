#!/usr/bin/env bash
# D7 extra: one model router deployment (Global Standard) in the shared Foundry resource,
# restricted to a subset of four Azure OpenAI models so every routed request stays on
# models sold directly by Azure. Pay per token, nothing hourly. ./cleanup.sh deletes it.
#
# Usage: ./setup.sh [balanced|cost|quality]   (default balanced)
#   Re-running with another mode updates the same deployment. Learn: changes to the
#   routing mode or the model subset can take up to five minutes to take effect.
#
# The Azure CLI deployment command has no routing options, so this uses the management
# REST call exactly as Learn shows it (PUT on the deployment, api-version 2025-10-01-preview).
#
# Sources:
# https://learn.microsoft.com/azure/foundry/openai/how-to/model-router#configure-custom-settings-with-the-rest-api
# https://learn.microsoft.com/azure/foundry/openai/concepts/model-router#supported-regions
# https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability#global-standard
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a

MODE=${1:-balanced}
case "$MODE" in balanced|cost|quality) ;; *) echo "Mode must be balanced, cost or quality"; exit 1 ;; esac
ROUTER_DEPLOYMENT=${ROUTER_DEPLOYMENT:-model-router}

SUB=$(az account show --query id -o tsv)
export AZURE_AI_AUTH_TOKEN=$(az account get-access-token --resource https://management.azure.com --query accessToken -o tsv)

# Model subset: names and versions from the model router supported-models table.
# All four are Azure OpenAI models, Global Standard in Sweden Central.
# No Claude (Marketplace-billed, and Learn says Claude must be deployed separately anyway),
# no other providers: the subset is the guarantee, not the default pool.
curl -sS --fail-with-body -X PUT \
  "https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$FOUNDRY/deployments/$ROUTER_DEPLOYMENT?api-version=2025-10-01-preview" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AZURE_AI_AUTH_TOKEN" \
  -d '{
    "sku": {"name": "GlobalStandard", "capacity": 10},
    "properties": {
      "model": {"format": "OpenAI", "name": "model-router", "version": "2025-11-18"},
      "routing": {
        "mode": "'"$MODE"'",
        "models": [
          {"format": "OpenAI", "name": "gpt-5.4-nano", "version": "2026-03-17"},
          {"format": "OpenAI", "name": "gpt-5.4-mini", "version": "2026-03-17"},
          {"format": "OpenAI", "name": "gpt-5.4",      "version": "2026-03-05"},
          {"format": "OpenAI", "name": "o4-mini",      "version": "2025-04-16"}
        ]
      }
    }
  }'
echo

# The PUT returns before the deployment is ready. Wait for it.
for _ in $(seq 1 30); do
  STATE=$(az cognitiveservices account deployment show -n "$FOUNDRY" -g "$RG" \
    --deployment-name "$ROUTER_DEPLOYMENT" --query properties.provisioningState -o tsv 2>/dev/null || true)
  [ "$STATE" = "Succeeded" ] && break
  [ "$STATE" = "Failed" ] && { echo "Deployment failed"; exit 1; }
  sleep 10
done
echo "Deployment $ROUTER_DEPLOYMENT: ${STATE:-unknown}, routing mode $MODE"
echo "Show it: az cognitiveservices account deployment show -n $FOUNDRY -g $RG --deployment-name $ROUTER_DEPLOYMENT"
