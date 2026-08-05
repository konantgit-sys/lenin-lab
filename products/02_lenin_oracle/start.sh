#!/bin/bash
cd /home/agent/data/sites/lenin-book/products/02_lenin_oracle
kill $(ps aux | grep "oracle_bot.py" | grep -v grep | awk '{print \$2}') 2>/dev/null
sleep 1
nohup python3 oracle_bot.py > oracle_bot.log 2>&1 &
