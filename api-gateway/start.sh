#!/bin/bash
cd "${LENIN_API_GATEWAY_DIR:-/home/agent/data/sites/api-lenin}"
exec python3 app.py >> server.log 2>&1
