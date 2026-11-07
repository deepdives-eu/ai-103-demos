#!/usr/bin/env bash
# D11 extras: one gpt-image-2 deployment on the shared Foundry resource (Sweden Central),
# Global Standard, pay per image. No second resource: Learn lists gpt-image-2 (2026-04-21)
# for Global Standard in Sweden Central. Nothing here costs money while idle.
# gpt-image-2 is generally available; unlike gpt-image-1 and 1.5 it needs no limited access application.
#
# Overrides (optional, in the environment):
#   IMAGE_DEPLOYMENT  default gpt-image-2 (the deployment name the script calls)
#   IMAGE_CAPACITY    default 1 (deployment capacity; see the README, VERIFY in the dry run)
#
# Sources:
# https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability#global-standard
# https://learn.microsoft.com/azure/foundry/openai/how-to/dall-e (availability, quota, 401 troubleshooting)
# https://learn.microsoft.com/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a

IMAGE_DEPLOYMENT=${IMAGE_DEPLOYMENT:-gpt-image-2}
IMAGE_CAPACITY=${IMAGE_CAPACITY:-1}

az cognitiveservices account deployment create -n "$FOUNDRY" -g "$RG" \
  --deployment-name "$IMAGE_DEPLOYMENT" --model-name gpt-image-2 --model-version 2026-04-21 \
  --model-format OpenAI --sku-name GlobalStandard --sku-capacity "$IMAGE_CAPACITY" -o none

# Learn's troubleshooting for a 401 with Entra ID: the identity needs Cognitive Services OpenAI User
# on the resource. ../common/setup.sh already gives you Foundry User; this adds the role Learn names.
ME=$(az ad signed-in-user show --query id -o tsv)
FOUNDRY_ID=$(az cognitiveservices account show -n "$FOUNDRY" -g "$RG" --query id -o tsv)
az role assignment create --role "Cognitive Services OpenAI User" --assignee-object-id "$ME" \
  --assignee-principal-type User --scope "$FOUNDRY_ID" -o none || true

az cognitiveservices account deployment show -n "$FOUNDRY" -g "$RG" \
  --deployment-name "$IMAGE_DEPLOYMENT" --query "properties.provisioningState" -o tsv
echo "Endpoint: https://$FOUNDRY.openai.azure.com/openai/v1/  deployment: $IMAGE_DEPLOYMENT"
echo "Role assignments can take a few minutes. Then: python image_demo.py generate"
