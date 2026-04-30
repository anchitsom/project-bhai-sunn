#!/bin/bash
# Launchd entrypoint for bhai-sunn STT server.
# Hosts IndicConformer 600M on 127.0.0.1:8765 (localhost-only; no auth on the wire).
set -euo pipefail

PROJECT=/Users/anchitsom/agent-brain/projects/experiments/project-bhai-sunn_asp
cd "$PROJECT"
exec "$PROJECT/.venv/bin/uvicorn" \
  prototype.stt_server:app \
  --host 127.0.0.1 \
  --port 8765 \
  --log-level warning
