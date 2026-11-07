#!/usr/bin/env bash
# D10 extras: two pay-per-token deployments, Global Standard, nothing billed by the hour.
#   gpt-audio-mini (2025-12-15)          listens to the call (chat completions with input_audio)
#   gpt-4o-mini-transcribe (2025-12-15)  turns the call into text (/audio/transcriptions, preview)
# Learn lists both as Global Standard in Sweden Central, so they go into the shared Foundry
# resource. If the shared region doesn't offer gpt-audio-mini as Global Standard (for example
# because you changed LOCATION), the script creates a second, small Foundry resource in
# AUDIO_FALLBACK_LOCATION in its own resource group, rg-ai103-d10. ./cleanup.sh deletes it.
#
# Writes out/d10.env (AZURE_OPENAI_ENDPOINT, AUDIO_DEPLOYMENT, TRANSCRIBE_DEPLOYMENT).
#
# Sources:
# https://learn.microsoft.com/azure/foundry/openai/audio-completions-quickstart
# https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability
# https://learn.microsoft.com/azure/foundry-classic/openai/how-to/role-based-access-control
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a

AUDIO_MODEL=gpt-audio-mini;          AUDIO_VERSION=2025-12-15
TRANSCRIBE_MODEL=gpt-4o-mini-transcribe; TRANSCRIBE_VERSION=2025-12-15
AUDIO_FALLBACK_LOCATION=${AUDIO_FALLBACK_LOCATION:-eastus2}   # Learn lists both models as Global Standard there
CAPACITY=${CAPACITY:-10}                                        # small on purpose: one short call at a time

offers_global_standard() {  # location model version
  az cognitiveservices model list -l "$1" \
    --query "[?model.name=='$2' && model.version=='$3'].model.skus[].name" -o tsv | grep -qx GlobalStandard
}

# AUDIO_USE_SHARED=1 skips the region check and always uses the shared resource.
if [ "${AUDIO_USE_SHARED:-0}" = 1 ] || offers_global_standard "$LOCATION" "$AUDIO_MODEL" "$AUDIO_VERSION"; then
  AUDIO_RG=$RG; AUDIO_ACCOUNT=$FOUNDRY
  echo "Using the shared resource $FOUNDRY in $LOCATION."
else
  AUDIO_RG=rg-ai103-d10; AUDIO_ACCOUNT="$FOUNDRY-d10"
  echo "$AUDIO_MODEL $AUDIO_VERSION isn't Global Standard in $LOCATION."
  echo "Creating $AUDIO_ACCOUNT in $AUDIO_FALLBACK_LOCATION (resource group $AUDIO_RG)."
  az group create -n "$AUDIO_RG" -l "$AUDIO_FALLBACK_LOCATION" -o none
  az cognitiveservices account create -n "$AUDIO_ACCOUNT" -g "$AUDIO_RG" -l "$AUDIO_FALLBACK_LOCATION" \
    --kind AIServices --sku S0 --custom-domain "$AUDIO_ACCOUNT" --yes -o none
fi

deploy() {  # name model version
  az cognitiveservices account deployment create -n "$AUDIO_ACCOUNT" -g "$AUDIO_RG" \
    --deployment-name "$1" --model-name "$2" --model-version "$3" --model-format OpenAI \
    --sku-name GlobalStandard --sku-capacity "$CAPACITY" -o none
}
deploy "$AUDIO_MODEL" "$AUDIO_MODEL" "$AUDIO_VERSION"
deploy "$TRANSCRIBE_MODEL" "$TRANSCRIBE_MODEL" "$TRANSCRIBE_VERSION"

# Keyless calls to the Azure OpenAI endpoint need an inference role on the resource.
ACCOUNT_ID=$(az cognitiveservices account show -n "$AUDIO_ACCOUNT" -g "$AUDIO_RG" --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
az role assignment create --role "Cognitive Services OpenAI User" --assignee-object-id "$ME" \
  --assignee-principal-type User --scope "$ACCOUNT_ID" -o none || true

mkdir -p out
cat > out/d10.env <<ENV
AZURE_OPENAI_ENDPOINT=https://$AUDIO_ACCOUNT.openai.azure.com/
AUDIO_DEPLOYMENT=$AUDIO_MODEL
TRANSCRIBE_DEPLOYMENT=$TRANSCRIBE_MODEL
AUDIO_RG=$AUDIO_RG
AUDIO_ACCOUNT=$AUDIO_ACCOUNT
ENV
echo "Wrote out/d10.env. Load it with: set -a; source ../common/demo.env; source out/d10.env; set +a"
echo "Role assignments can take a few minutes to apply."
