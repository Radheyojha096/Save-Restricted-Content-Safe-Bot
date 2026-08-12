#!/bin/bash

# Monitor bot and restart if necessary
BOT_PID=$(ps aux | grep python3 | grep -v grep | awk '{print $2}')

if [ -z "$BOT_PID" ]; then
    echo "Bot is not running. Restarting..."
    nohup python3 -m safe_repo > bot.log 2>&1 &
    echo "Bot restarted with PID: $!"
else
    echo "Bot is running with PID: $BOT_PID"
fi

# Check if bot responds to API calls with timeout
# NOTE: Use the same BOT_TOKEN as config.py. The old hardcoded token here
# was different from config.py and caused a 409 Conflict (dual-login) that
# made the bot stop responding.
BOT_TOKEN="${BOT_TOKEN:-8564747078:AAF4rw9Fw7sBI-NCdCZgOvaUL2mIGrleIss}"
RESPONSE=$(curl -s --connect-timeout 10 "https://api.telegram.org/bot${BOT_TOKEN}/getMe")

if echo "$RESPONSE" | grep -q "ok\":true"; then
    echo "Bot is responding to API calls"
else
    echo "Bot is not responding to API calls. Restarting..."
    # Try to kill gracefully first
    pkill -f python3 || true
    sleep 3
    # Force kill if still running
    pkill -9 -f python3 || true
    sleep 2
    nohup python3 -m safe_repo > bot.log 2>&1 &
    echo "Bot restarted with PID: $!"
fi

# Check for any zombie processes
ZOMBIES=$(ps aux | grep -E "python3.*defunct" | grep -v grep)
if [ -n "$ZOMBIES" ]; then
    echo "Found zombie processes, cleaning up..."
    pkill -9 -f python3 || true
    sleep 2
    nohup python3 -m safe_repo > bot.log 2>&1 &
    echo "Bot restarted with PID: $!"
fi