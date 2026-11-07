#!/usr/bin/env bash
# D2 extras: a Log Analytics workspace and a workspace-based Application Insights
# resource in their own resource group, next to the shared Foundry project.
# Ingestion is what costs money here, so the workspace gets a small daily cap
# (a safety net, not exact: data over the cap is still billed) and 30 days retention.
# Connecting Application Insights to the Foundry project is done on screen in the portal.
#
# Sources:
# https://learn.microsoft.com/azure/azure-monitor/app/create-workspace-resource
# https://learn.microsoft.com/cli/azure/monitor/log-analytics/workspace?view=azure-cli-latest
# https://learn.microsoft.com/azure/azure-monitor/logs/daily-cap
set -euo pipefail
cd "$(dirname "$0")"
source ../common/demo.env

D2_RG=rg-ai103-d2
LAW=law-ai103-d2
APPI=appi-ai103-d2

az extension add --name application-insights --only-show-errors 2>/dev/null || true

az group create -n "$D2_RG" -l "$LOCATION" -o none

# --quota is the workspace daily ingestion cap in GB (minimum 0.023, default -1 = unlimited).
LAW_ID=$(az monitor log-analytics workspace create -g "$D2_RG" -n "$LAW" -l "$LOCATION" \
  --retention-time 30 --quota 0.1 --query id -o tsv)

APPI_ID=$(az monitor app-insights component create --app "$APPI" -g "$D2_RG" -l "$LOCATION" \
  --kind web --application-type web --workspace "$LAW_ID" --query id -o tsv)

# Learn: querying traces needs Log Analytics Reader on the connected resources.
ME=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --role "Log Analytics Reader" \
  --assignee-object-id "$ME" --assignee-principal-type User \
  --scope "$(az group show -n "$D2_RG" --query id -o tsv)" -o none || true

echo "Application Insights: $APPI_ID"
echo "Next: Foundry portal > project $PROJECT > Agents > Traces > Connect > select $APPI."
