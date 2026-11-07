#!/usr/bin/env bash
# D13 extras: one Azure AI Search service (Basic) in its own resource group, keys disabled,
# plus the roles you need to use it and to call the shared embedding deployment.
#
# BILLED BY THE HOUR while it exists (Basic is a dedicated tier). Run
# ./cleanup.sh the same day.
#
# Overrides (optional, in the environment):
#   SEARCH_LOCATION  default francecentral (EU, semantic ranker available). Learn flags
#                    Sweden Central as "high demand", which prevents new search services.
#                    The search service never calls Foundry here, so the region can differ.
#   SEARCH_SKU       default basic. See the README before trying free.
#   SEARCH_SERVICE   default <FOUNDRY>-d13, lower case (must be globally unique).
#
# Sources:
# https://learn.microsoft.com/azure/search/search-manage-azure-cli
# https://learn.microsoft.com/azure/search/search-security-enable-roles
# https://learn.microsoft.com/azure/search/search-security-rbac
# https://learn.microsoft.com/azure/search/search-region-support
# https://learn.microsoft.com/azure/foundry/openai/how-to/embeddings (Cognitive Services OpenAI User)
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a

SEARCH_RG=rg-ai103-d13
SEARCH_LOCATION=${SEARCH_LOCATION:-francecentral}
SEARCH_SKU=${SEARCH_SKU:-basic}
SEARCH_SERVICE=${SEARCH_SERVICE:-$(echo "$FOUNDRY-d13" | tr '[:upper:]' '[:lower:]')}

az group create -n "$SEARCH_RG" -l "$SEARCH_LOCATION" -o none

# Roles only: --disable-local-auth turns API keys off for data plane requests.
az search service create -n "$SEARCH_SERVICE" -g "$SEARCH_RG" -l "$SEARCH_LOCATION" \
  --sku "$SEARCH_SKU" --disable-local-auth true -o none

ME=$(az ad signed-in-user show --query id -o tsv)
SEARCH_ID=$(az search service show -n "$SEARCH_SERVICE" -g "$SEARCH_RG" --query id -o tsv)
for ROLE in "Search Service Contributor" "Search Index Data Contributor" "Search Index Data Reader"; do
  az role assignment create --role "$ROLE" --assignee-object-id "$ME" \
    --assignee-principal-type User --scope "$SEARCH_ID" -o none
done

# Embeddings are called on the shared Foundry resource (rg-ai103-demos), not in this group.
FOUNDRY_ID=$(az cognitiveservices account show -n "$FOUNDRY" -g "$RG" --query id -o tsv)
az role assignment create --role "Cognitive Services OpenAI User" --assignee-object-id "$ME" \
  --assignee-principal-type User --scope "$FOUNDRY_ID" -o none || true

echo "Search service: https://$SEARCH_SERVICE.search.windows.net ($SEARCH_SKU, $SEARCH_LOCATION)"
echo "Role assignments can take 5 to 10 minutes. Then: python create_index.py"
echo "Billed by the hour from now on. Run ./cleanup.sh when you're done today."
