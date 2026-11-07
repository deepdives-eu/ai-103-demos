#!/usr/bin/env bash
# D3: show or change key (local) authentication on the shared Foundry resource.
#
# Usage: ./local_auth.sh status | off | on
#   status  prints properties.disableLocalAuth (true = keys refused; empty or false = keys accepted)
#   off     sets disableLocalAuth=true  (API keys stop working; Entra ID only)
#   on      sets disableLocalAuth=false (API keys work again)
#
# The change is immediate on the control plane, but the gateway can keep accepting keys
# for a few minutes up to several hours. Check with: python auth_demo.py key --until denied
#
# Sources:
#   disableLocalAuth property, propagation, re-enable: https://learn.microsoft.com/azure/ai-services/disable-local-auth
#   az resource show for the account:                  https://learn.microsoft.com/azure/foundry/foundry-models/how-to/configure-entra-id?pivots=programming-language-cli
#   az resource update --set properties.disableLocalAuth (shown on Learn for Cosmos DB, same ARM property name):
#     https://learn.microsoft.com/azure/cosmos-db/how-to-connect-role-based-access-control#disable-key-based-authentication
#   Learn's documented route for Foundry is PowerShell:
#     Set-AzCognitiveServicesAccount -ResourceGroupName <rg> -Name <name> -DisableLocalAuth $true
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a
TYPE=Microsoft.CognitiveServices/accounts

status() {
  echo -n "disableLocalAuth on $FOUNDRY: "
  az resource show -g "$RG" -n "$FOUNDRY" --resource-type "$TYPE" --query properties.disableLocalAuth -o tsv
}

case "${1:-status}" in
  status) status ;;
  off) az resource update -g "$RG" -n "$FOUNDRY" --resource-type "$TYPE" --set properties.disableLocalAuth=true -o none; status ;;
  on)  az resource update -g "$RG" -n "$FOUNDRY" --resource-type "$TYPE" --set properties.disableLocalAuth=false -o none; status ;;
  *) echo "Usage: $0 status | off | on" >&2; exit 2 ;;
esac
