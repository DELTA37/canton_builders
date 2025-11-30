#!/usr/bin/env bash
set -euo pipefail

# Launch full stack: Canton sandbox (via daml start) + JSON API + Streamlit UI.
# Env vars:
#   JSON_API_PORT (default 17575)
#   SANDBOX_CONFIG (default sandbox.conf)
#   WAIT_SECONDS (default 60) time to wait for JSON API health
#   UI_PORT (default 8501)
#   WAIT_FOR_SIGNAL (default yes) passed to daml start
#   LEDGER_HOST (default localhost) LEDGER_PORT (default 26865) passed to UI

cd real-estate

JSON_API_PORT="${JSON_API_PORT:-17575}"
SANDBOX_CONFIG="${SANDBOX_CONFIG:-sandbox.conf}"
WAIT_SECONDS="${WAIT_SECONDS:-60}"
UI_PORT="${UI_PORT:-8501}"
WAIT_FOR_SIGNAL="${WAIT_FOR_SIGNAL:-yes}"
LEDGER_HOST="${LEDGER_HOST:-localhost}"
LEDGER_PORT="${LEDGER_PORT:-26865}"

if ! command -v streamlit >/dev/null 2>&1; then
  echo "streamlit not found. Install deps: pip install -r python_client/requirements.txt" >&2
  exit 1
fi

mkdir -p log

if [ "${SKIP_SANDBOX:-false}" != "true" ]; then
  echo "Starting daml start (config=${SANDBOX_CONFIG}, json-api=${JSON_API_PORT})..."
  daml start \
    --sandbox-option --config="${SANDBOX_CONFIG}" \
    --json-api-port "${JSON_API_PORT}" \
    --wait-for-signal "${WAIT_FOR_SIGNAL}" \
    >log/app-sandbox.log 2>&1 &
  SANDBOX_PID=$!

  cleanup() {
    echo "Stopping sandbox (pid ${SANDBOX_PID})"
    kill "${SANDBOX_PID}" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  echo "Waiting for JSON API on http://localhost:${JSON_API_PORT} ..."
  API_READY=0
  for _ in $(seq 1 "${WAIT_SECONDS}"); do
    if curl -sSf "http://localhost:${JSON_API_PORT}/livez" -o /dev/null; then
      echo "JSON API is up."
      API_READY=1
      break
    fi
    sleep 1
  done
  if [ "${API_READY}" -eq 0 ]; then
    echo "JSON API did not become ready within ${WAIT_SECONDS}s. Check log/app-sandbox.log." >&2
    exit 1
  fi
else
  echo "SKIP_SANDBOX=true, not starting daml sandbox. Using existing ledger at ${LEDGER_HOST}:${LEDGER_PORT}."
fi

export LEDGER_HOST LEDGER_PORT
export JSON_API_URL="http://localhost:${JSON_API_PORT}"
echo "Starting Streamlit UI on port ${UI_PORT} (LEDGER_HOST=${LEDGER_HOST} LEDGER_PORT=${LEDGER_PORT})..."
cd ..
exec streamlit run ui.py --server.port "${UI_PORT}" --server.headless true
