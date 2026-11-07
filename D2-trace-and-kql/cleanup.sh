#!/usr/bin/env bash
# Remove everything D2 added: the demo agent, the Application Insights connection
# on the shared project, and the rg-ai103-d2 resource group.
# The shared Foundry project and its deployments stay.
# Usage: ./cleanup.sh <connection-name>|none
#   Without an argument it only lists the project's connections and stops, so you can
#   pick the one the portal created for appi-ai103-d2. "none" skips the connection.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a

if [ -z "${1:-}" ]; then
  az cognitiveservices account project connection list -n "$FOUNDRY" -g "$RG" \
    --project-name "$PROJECT" -o table
  echo "Re-run as ./cleanup.sh <name of the Application Insights connection> (or 'none')."
  exit 1
fi

python3 trace_one_run.py --delete-agent || echo "Agent not deleted (see message above)."

if [ "$1" != "none" ]; then
  az cognitiveservices account project connection delete -n "$FOUNDRY" -g "$RG" \
    --project-name "$PROJECT" --connection-name "$1"
fi

az group delete -n rg-ai103-d2 --yes --no-wait
echo "Deleting rg-ai103-d2 in the background. Check with: az group exists -n rg-ai103-d2"
