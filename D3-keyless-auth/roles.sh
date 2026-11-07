#!/usr/bin/env bash
# D3: show, remove or add your Foundry User role on the shared Foundry resource.
#
# Usage: ./roles.sh show | remove | add
#   show    lists every role you hold directly on the Foundry resource
#   remove  deletes your Foundry User assignment there (keyless calls start failing with 403)
#   add     assigns it again, the same way ../common/setup.sh does
#
# Foundry User is role ID 53ca6127-db72-4b80-b1b0-d745d6d5456d (formerly Azure AI User). Learn
# recommends the ID because of the rename. Role changes can take up to 10 minutes to apply.
# You need Owner or User Access Administrator on the resource to change role assignments.
#
# Sources:
#   https://learn.microsoft.com/azure/foundry/concepts/authentication-authorization-foundry#set-up-microsoft-entra-id
#   https://learn.microsoft.com/azure/foundry/concepts/rbac-foundry#manage-role-assignments
#   https://learn.microsoft.com/azure/role-based-access-control/troubleshooting#azure-role-assignments
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a
FOUNDRY_USER=53ca6127-db72-4b80-b1b0-d745d6d5456d

ACCOUNT_ID=$(az cognitiveservices account show -n "$FOUNDRY" -g "$RG" --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)

show() {
  echo "Your roles directly on $FOUNDRY:"
  az role assignment list --assignee "$ME" --scope "$ACCOUNT_ID" \
    --query "[].{role:roleDefinitionName, roleId:roleDefinitionId}" -o table
}

case "${1:-show}" in
  show) show ;;
  remove)
    az role assignment delete --assignee-object-id "$ME" --role "$FOUNDRY_USER" --scope "$ACCOUNT_ID"
    echo "Removed Foundry User. Takes up to 10 minutes to apply."; show ;;
  add)
    az role assignment create --role "$FOUNDRY_USER" --assignee-object-id "$ME" \
      --assignee-principal-type User --scope "$ACCOUNT_ID" -o none
    echo "Assigned Foundry User. Takes up to 10 minutes to apply."; show ;;
  *) echo "Usage: $0 show | remove | add" >&2; exit 2 ;;
esac
