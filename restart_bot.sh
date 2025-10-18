#!/data/data/com.termux/files/usr/bin/sh
cd /data/data/com.termux/files/home/mbbs_bot

while true; do
    python mbbs_bot.py
    echo "Bot crashed, restarting in 5 seconds..."
    sleep 5
done
