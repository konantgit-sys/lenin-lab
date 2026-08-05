#!/bin/bash
cd /home/agent/data/sites/api-lenin
exec python3 app.py >> server.log 2>&1
