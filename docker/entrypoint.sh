#!/usr/bin/env bash
set -e

# Start uvicorn in background
PYTHONPATH=/app /usr/local/bin/uvicorn api.main:app --host 127.0.0.1 --port 8090 &

# Start nginx in foreground
exec /usr/sbin/nginx -g 'daemon off;'
