#!/usr/bin/env bash
# Hockey Intelligence — portable launcher.
#
# Prefers the bundled Python sidecar (hockey-server); falls back to a system
# Python for development. Serves the SPA on http://127.0.0.1:8000 and opens a
# browser. Kill with Ctrl-C and the server is shut down too.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

API_URL="http://127.0.0.1:8000"
PID=""

cleanup() {
  if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

start_sidecar() {
  export HI_DATA_DIR="${HI_DATA_DIR:-$DIR/data}"
  if [[ -x "$DIR/hockey-server" ]]; then
    "$DIR/hockey-server" >"$DIR/hockey-server.log" 2>&1 &
    PID=$!
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    python3 -m uvicorn app.main:app \
      --host 127.0.0.1 --port 8000 --app-dir "$DIR" \
      >"$DIR/hockey-server.log" 2>&1 &
    PID=$!
    return 0
  fi
  echo "No hockey-server bundled and no python3 found; cannot start the API." >&2
  return 1
}

wait_for_api() {
  for _ in $(seq 1 90); do
    if curl -fsS -m 1 "$API_URL/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Timed out waiting for $API_URL/health — see $DIR/hockey-server.log" >&2
  return 1
}

start_sidecar
wait_for_api

echo "Hockey Intelligence is running at $API_URL"
if command -v xdg-open >/dev/null 2>&1; then
  (xdg-open "$API_URL" >/dev/null 2>&1 &)
elif command -v open >/dev/null 2>&1; then
  (open "$API_URL" >/dev/null 2>&1 &)
fi

wait "$PID"