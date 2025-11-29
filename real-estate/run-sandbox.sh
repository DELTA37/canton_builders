#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   JSON_API_PORT=17575 WAIT_FOR_SIGNAL=yes ./run-sandbox.sh
# Defaults match sandbox.conf (ledger 16865, admin 15011, http-ledger 17575, sequencer 19017/19018, mediator 19019).

JSON_API_PORT="${JSON_API_PORT:-17575}"
SANDBOX_CONFIG="${SANDBOX_CONFIG:-sandbox.conf}"
WAIT_FOR_SIGNAL="${WAIT_FOR_SIGNAL:-yes}"

echo "Starting daml sandbox with config=${SANDBOX_CONFIG}, json-api=${JSON_API_PORT}, wait-for-signal=${WAIT_FOR_SIGNAL}"
exec daml start \
  --sandbox-option --config="${SANDBOX_CONFIG}" \
  --json-api-port "${JSON_API_PORT}" \
  --wait-for-signal "${WAIT_FOR_SIGNAL}"
