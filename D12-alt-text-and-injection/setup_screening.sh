#!/usr/bin/env bash
# D12 extras for step 5, in their own resource group next to the shared Foundry project:
#   - an Azure AI Content Safety resource (Prompt Shields), free tier F0
#   - a Document Intelligence resource (prebuilt-read OCR), free tier F0
# Both get a custom subdomain, because keyless (Microsoft Entra ID) calls need one,
# and you get Cognitive Services User on both. Endpoints go to d12.env (ignored by git).
# Nothing here is billed by the hour. F0 has rate and page limits, which this demo stays far below.
#
# Sources:
# https://learn.microsoft.com/azure/ai-services/content-safety/overview (F0/S0, Entra ID, Cognitive Services User)
# https://learn.microsoft.com/azure/ai-services/content-safety/region-availability (Prompt Shields in Sweden Central)
# https://learn.microsoft.com/azure/ai-services/document-intelligence/how-to-guides/create-document-intelligence-resource (F0)
# https://learn.microsoft.com/azure/ai-services/authentication#authenticate-with-microsoft-entra-id (custom subdomain)
set -euo pipefail
cd "$(dirname "$0")"
source ../common/demo.env

D12_RG=rg-ai103-d12
CS="${FOUNDRY}-cs"   # FOUNDRY is already globally unique, so these names are too
DI="${FOUNDRY}-di"

az group create -n "$D12_RG" -l "$LOCATION" -o none

az cognitiveservices account create -n "$CS" -g "$D12_RG" -l "$LOCATION" \
  --kind ContentSafety --sku F0 --custom-domain "$CS" --yes -o none
az cognitiveservices account create -n "$DI" -g "$D12_RG" -l "$LOCATION" \
  --kind FormRecognizer --sku F0 --custom-domain "$DI" --yes -o none

ME=$(az ad signed-in-user show --query id -o tsv)
for NAME in "$CS" "$DI"; do
  ID=$(az cognitiveservices account show -n "$NAME" -g "$D12_RG" --query id -o tsv)
  az role assignment create --role "Cognitive Services User" \
    --assignee-object-id "$ME" --assignee-principal-type User --scope "$ID" -o none || true
done

CS_ENDPOINT=$(az cognitiveservices account show -n "$CS" -g "$D12_RG" --query properties.endpoint -o tsv)
DI_ENDPOINT=$(az cognitiveservices account show -n "$DI" -g "$D12_RG" --query properties.endpoint -o tsv)
cat > d12.env <<ENV
CONTENT_SAFETY_ENDPOINT=$CS_ENDPOINT
DOCUMENT_INTELLIGENCE_ENDPOINT=$DI_ENDPOINT
ENV
echo "Wrote d12.env:"; cat d12.env
echo "Next: set -a; source d12.env; set +a   (role assignments can take a few minutes)"
