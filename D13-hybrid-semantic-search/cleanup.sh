#!/usr/bin/env bash
# Delete everything D13 created: the rg-ai103-d13 resource group with the search
# service, its index and the role assignments scoped to it. This stops the hourly charge.
# The shared Foundry project stays. The Cognitive Services OpenAI User assignment on the
# Foundry resource also stays; it costs nothing and other demos can use it.
set -euo pipefail

az group delete -n rg-ai103-d13 --yes --no-wait
echo "Deleting rg-ai103-d13 in the background. Check with: az group exists -n rg-ai103-d13"
