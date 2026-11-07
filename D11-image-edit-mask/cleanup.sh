#!/usr/bin/env bash
# Remove what D11 added: the gpt-image-2 deployment and the generated images in out/.
# The shared Foundry resource, project and other deployments stay. The Cognitive Services
# OpenAI User assignment also stays; it costs nothing and other demos can use it.
#
# Source: https://learn.microsoft.com/cli/azure/cognitiveservices/account/deployment?view=azure-cli-latest
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; set +a

IMAGE_DEPLOYMENT=${IMAGE_DEPLOYMENT:-gpt-image-2}

az cognitiveservices account deployment delete -n "$FOUNDRY" -g "$RG" \
  --deployment-name "$IMAGE_DEPLOYMENT"
rm -rf out
echo "Deleted deployment $IMAGE_DEPLOYMENT and out/."
