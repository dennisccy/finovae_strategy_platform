#!/usr/bin/env bash
# Start the Finovae Strategy API with multiple workers.
# --timeout-graceful-shutdown 0 ensures Ctrl+C kills workers immediately
# instead of waiting for long-running SSE connections to close.

WORKERS=${WEB_CONCURRENCY:-4}

exec uvicorn backend.api:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "$WORKERS" \
  --timeout-graceful-shutdown 0
