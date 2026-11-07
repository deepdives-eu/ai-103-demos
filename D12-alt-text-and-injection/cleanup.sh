#!/usr/bin/env bash
# Remove what D12 added: the rg-ai103-d12 resource group (Content Safety and Document Intelligence),
# d12.env and the generated images. The shared Foundry project and its deployments stay.
set -euo pipefail
cd "$(dirname "$0")"

if [ "$(az group exists -n rg-ai103-d12)" = "true" ]; then
  az group delete -n rg-ai103-d12 --yes --no-wait
  echo "Deleting rg-ai103-d12 in the background. Check with: az group exists -n rg-ai103-d12"
else
  echo "rg-ai103-d12 doesn't exist, nothing to delete in Azure."
fi
rm -f d12.env
rm -rf images
