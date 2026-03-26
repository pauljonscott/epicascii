#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

# Kill old processes
lsof -ti:8765 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti:8080 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

# Start game server
python run_server.py "$@" &
GAME_PID=$!

# Start web server
python -m http.server 8080 --bind 127.0.0.1 &>/dev/null &
WEB_PID=$!

cleanup() { kill $GAME_PID $WEB_PID 2>/dev/null; }
trap cleanup EXIT

# Wait for game server
echo "Starting EpicAscii..."
i=0
while [ $i -lt 30 ]; do
    if python -c "import socket; s=socket.socket(); s.settimeout(0.5); s.connect(('localhost',8765)); s.close()" 2>/dev/null; then
        sleep 0.5
        echo "Server ready!"
        open "http://localhost:8080/web_client.html"
        echo ""
        echo "  Browser:  http://localhost:8080/web_client.html"
        echo "  Terminal: python run_client.py"
        echo "  Ctrl-C to stop"
        echo ""
        wait $GAME_PID
        exit 0
    fi
    i=$((i + 1))
    sleep 0.5
done

echo "Server failed to start."
exit 1
