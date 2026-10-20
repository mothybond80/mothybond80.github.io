#!/usr/bin/env bash
# "Navigate to Tim Bond Dental from my current location"
#
# Usage: ./examples/tim-bond-dental.sh            (no origin: Maps link opens from the phone's location)
#        ORIGIN="52.3478,-1.5803" ./examples/tim-bond-dental.sh   (GPS fix: also returns distance/duration)
set -euo pipefail
cd "$(dirname "$0")/.."

URL="${BRIDGE_URL:-http://127.0.0.1:${PORT:-3000}}/navigate_to_g2"
AUTH=()
if [[ -n "${BRIDGE_API_TOKEN:-}" ]]; then AUTH=(-H "Authorization: Bearer ${BRIDGE_API_TOKEN}"); fi

BODY=$(cat examples/tim-bond-dental.json)
if [[ -n "${ORIGIN:-}" ]]; then
  BODY=$(node -e 'const b=JSON.parse(process.argv[1]);b.origin=process.argv[2];console.log(JSON.stringify(b))' "$BODY" "$ORIGIN")
fi

curl -sS -X POST "$URL" -H 'Content-Type: application/json' ${AUTH[@]+"${AUTH[@]}"} -d "$BODY"
echo
