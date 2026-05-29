#!/usr/bin/env bash
# Start cotton.xyz local dev (UI + API). Run from project root:
#   ./scripts/dev.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

UI_PORT="${UI_PORT:-3000}"
API_PORT="${API_PORT:-8000}"

if ! curl -sf "http://127.0.0.1:${UI_PORT}/app.html" >/dev/null 2>&1; then
  echo "Starting UI on http://127.0.0.1:${UI_PORT} ..."
  python3 -m http.server "$UI_PORT" --bind 127.0.0.1 >/tmp/cotton-ui.log 2>&1 &
  echo $! > /tmp/cotton-ui.pid
fi

if ! curl -sf "http://127.0.0.1:${API_PORT}/health" >/dev/null 2>&1; then
  echo "Starting API on http://127.0.0.1:${API_PORT} ..."
  if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
    echo "Run once: npm run api:install"
    exit 1
  fi
  (cd "$ROOT/backend" && .venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port "$API_PORT") >/tmp/cotton-api.log 2>&1 &
  echo $! > /tmp/cotton-api.pid
  sleep 1
fi

echo ""
echo "  Trade UI:  http://127.0.0.1:${UI_PORT}/app.html"
echo "  Earn:      http://127.0.0.1:${UI_PORT}/earn.html"
echo "  Landing:   http://127.0.0.1:${UI_PORT}/"
echo "  API:       http://127.0.0.1:${API_PORT}/health"
echo ""
open -a Safari "http://127.0.0.1:${UI_PORT}/app.html" 2>/dev/null || true
