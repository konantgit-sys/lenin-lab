#!/bin/bash
cd "${LENIN_SITE_DIR:-/home/agent/data/sites/lenin-book}"
kill $(cat /tmp/lenin_api.pid 2>/dev/null) 2>/dev/null
sleep 1
nohup python3 -m uvicorn api_v2:app --host 0.0.0.0 --port 9770 > /tmp/lenin_api.log 2>&1 &
echo $! > /tmp/lenin_api.pid
