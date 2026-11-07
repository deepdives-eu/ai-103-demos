#!/usr/bin/env bash
# Delete what D10 created: the two deployments, and rg-ai103-d10 if setup.sh had to create
# the fallback resource. The shared Foundry resource and gpt-5.4-mini stay; the other demos
# use them. The Cognitive Services OpenAI User assignment on the shared resource also stays;
# it costs nothing and D13 uses the same role.
set -euo pipefail
cd "$(dirname "$0")"
set -a; source ../common/demo.env; [ -f out/d10.env ] && source out/d10.env; set +a
AUDIO_RG=${AUDIO_RG:-$RG}; AUDIO_ACCOUNT=${AUDIO_ACCOUNT:-$FOUNDRY}

if [ "$AUDIO_RG" = "rg-ai103-d10" ]; then
  az group delete -n rg-ai103-d10 --yes --no-wait
  echo "Deleting rg-ai103-d10 in the background. Check with: az group exists -n rg-ai103-d10"
else
  for D in gpt-audio-mini gpt-4o-mini-transcribe; do
    az cognitiveservices account deployment delete -n "$AUDIO_ACCOUNT" -g "$AUDIO_RG" \
      --deployment-name "$D" -o none && echo "Deleted deployment $D" || true
  done
fi
rm -rf out
echo "Removed out/ (the call recording, transcript and answers)."
