#!/bin/bash

# Run monitor_bot.sh every 5 minutes with error handling
while true; do
    # Run monitor script
    ./monitor_bot.sh >> monitor.log 2>&1
    
    # Check if monitor script failed
    if [ $? -ne 0 ]; then
        echo "Monitor script failed, restarting bot manually..." >> monitor.log
        pkill -9 -f python3 || true
        sleep 2
        nohup python3 -m safe_repo > bot.log 2>&1 &
        echo "Bot manually restarted" >> monitor.log
    fi
    
    sleep 300  # 5 minutes
done