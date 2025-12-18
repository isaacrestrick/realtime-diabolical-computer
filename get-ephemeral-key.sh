#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "Missing OPENAI_API_KEY." >&2
  echo "Usage: OPENAI_API_KEY=... ./get-ephemeral-key.sh" >&2
  exit 1
fi

MODEL="${MODEL:-gpt-realtime}"
VOICE="${VOICE:-verse}"
TTL_SECONDS="${TTL_SECONDS:-600}"
ANCHOR="${ANCHOR:-created_at}"

json="$(
  curl -sS -X POST "https://api.openai.com/v1/realtime/client_secrets" \
    -H "Authorization: Bearer ${OPENAI_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"expires_after\": { \"anchor\": \"${ANCHOR}\", \"seconds\": ${TTL_SECONDS} },
      \"session\": {
        \"type\": \"realtime\",
        \"model\": \"${MODEL}\",
        \"audio\": { \"output\": { \"voice\": \"${VOICE}\" } }
      }
    }"
)"

if command -v jq >/dev/null 2>&1; then
  value="$(echo "$json" | jq -r '.value // empty')"
else
  value="$(
    python3 - <<'PY'
import json, os, sys
data = json.loads(sys.stdin.read())
print(data.get("value") or "")
PY
  <<<"$json"
  )"
fi

if [[ -z "${value}" ]]; then
  echo "Failed to extract value. Full response:" >&2
  echo "$json" >&2
  exit 1
fi

echo "$value"
