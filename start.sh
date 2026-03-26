#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate

# Kill old processes
kill $(lsof -ti:8765) 2>/dev/null
kill $(lsof -ti:8080) 2>/dev/null
sleep 1

# Start game server
python run_server.py &
SERVER_PID=$!

# Start HTTP server for web client
python -m http.server 8080 &>/dev/null &
HTTP_PID=$!

trap "kill $SERVER_PID $HTTP_PID 2>/dev/null" EXIT

# Wait for server to be ready
sleep 2

echo "Server ready!"
open "http://127.0.0.1:8080/web_client.html"
echo ""
echo "  Browser:  http://127.0.0.1:8080/web_client.html"
echo "  Terminal: python run_client.py"
echo "  Ctrl-C to stop"
echo ""
wait $SERVER_PID
