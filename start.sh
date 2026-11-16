#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"

python3 -m pip install -r backend/requirements.txt
if [ ! -d frontend/node_modules ]; then
  npm --prefix frontend install
fi

python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
backend_pid=$!
cleanup() {
  kill "$backend_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
npm --prefix frontend run dev -- --open
