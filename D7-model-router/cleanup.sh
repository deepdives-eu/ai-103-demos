#!/usr/bin/env bash
# Delete what D7 created: the model router deployment. Nothing else was added.
# The shared Foundry resource, project and the other deployments stay; the other demos use them.
#
# Source: https://learn.microsoft.com/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a
ROUTER_DEPLOYMENT=${ROUTER_DEPLOYMENT:-model-router}

az cognitiveservices account deployment delete -n "$FOUNDRY" -g "$RG" --deployment-name "$ROUTER_DEPLOYMENT"
echo "Deleted deployment $ROUTER_DEPLOYMENT. Remaining deployments:"
az cognitiveservices account deployment list -n "$FOUNDRY" -g "$RG" --query "[].name" -o tsv
