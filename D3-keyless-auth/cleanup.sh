#!/usr/bin/env bash
# D3 cleanup. Makes sure you have Foundry User on the shared Foundry resource again (in case
# you stopped after step 5) and shows the key auth setting.
#
# Key auth stays OFF by default: no demo in this repo calls the Foundry resource with a key.
# Every demo uses Microsoft Entra ID (DefaultAzureCredential), and Learn lists Agent Service and
# evaluations as Entra ID only anyway. If you need keys back for your own work:
#
#   ./cleanup.sh --enable-keys
#
# Re-enabling, like disabling, can take a few minutes up to several hours to apply.
#
# Usage: ./cleanup.sh [--enable-keys]   (needs az login and the same ../common/demo.env)
#
# Sources:
#   https://learn.microsoft.com/azure/ai-services/disable-local-auth#re-enable-local-authentication
#   https://learn.microsoft.com/azure/foundry/concepts/authentication-authorization-foundry#feature-support-matrix
set -euo pipefail
cd "$(dirname "$0")"

./roles.sh add
if [ "${1:-}" = "--enable-keys" ]; then
  ./local_auth.sh on
else
  ./local_auth.sh status
  echo "Key auth left as it is. Run './cleanup.sh --enable-keys' to turn keys back on."
fi
echo "Also run: unset FOUNDRY_KEY"
