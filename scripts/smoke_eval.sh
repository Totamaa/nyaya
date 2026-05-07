#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-20}"
SLEEP_SECONDS="${SLEEP_SECONDS:-1}"

if ! command -v curl >/dev/null 2>&1; then
  echo "error: curl is required"
  exit 1
fi

if ! command -v python >/dev/null 2>&1 && ! command -v python3 >/dev/null 2>&1; then
  echo "error: python or python3 is required"
  exit 1
fi

PY_BIN="python"
if ! command -v python >/dev/null 2>&1; then
  PY_BIN="python3"
fi

CONTENT_ID="c_smoke_$(date +%s)"
NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

REQUEST_BODY="$(cat <<JSON
{
  "content_id": "${CONTENT_ID}",
  "content_type": "comment",
  "text": "Test smoke: je propose de comparer avantages et risques avant de decider.",
  "created_at": "${NOW_UTC}",
  "author_id": 999001,
  "context": {
    "edito_id": 1,
    "topic_id": 1,
    "phase": "decision",
    "tags": ["smoke-test", "ia"]
  }
}
JSON
)"

echo "==> Health check: ${BASE_URL}/health"
curl -fsS "${BASE_URL}/health" >/dev/null

echo "==> POST /api/v1/messages/ (content_id=${CONTENT_ID})"
POST_CODE="$(curl -sS -o /tmp/nyaya_smoke_post.json -w "%{http_code}" \
  -X POST "${BASE_URL}/api/v1/messages/" \
  -H "Content-Type: application/json" \
  -d "${REQUEST_BODY}")"

if [[ "${POST_CODE}" != "201" ]]; then
  echo "error: POST /messages failed with status ${POST_CODE}"
  cat /tmp/nyaya_smoke_post.json
  exit 1
fi

echo "==> Poll GET /api/v1/evaluations/${CONTENT_ID}"
START_TS="$(date +%s)"

while true; do
  GET_CODE="$(curl -sS -o /tmp/nyaya_smoke_get.json -w "%{http_code}" \
    "${BASE_URL}/api/v1/evaluations/${CONTENT_ID}")"

  if [[ "${GET_CODE}" == "200" ]]; then
    echo "ok: evaluation found"
    cat /tmp/nyaya_smoke_get.json
    echo
    "${PY_BIN}" - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/nyaya_smoke_get.json").read_text(encoding="utf-8"))
score_total = payload.get("score_total")
print(f"score_total={score_total}")
PY
    echo "smoke test passed"
    exit 0
  fi

  NOW_TS="$(date +%s)"
  ELAPSED="$((NOW_TS - START_TS))"
  if (( ELAPSED >= MAX_WAIT_SECONDS )); then
    echo "error: timed out after ${MAX_WAIT_SECONDS}s waiting for evaluation"
    echo "last status: ${GET_CODE}"
    cat /tmp/nyaya_smoke_get.json
    exit 1
  fi

  sleep "${SLEEP_SECONDS}"
done
