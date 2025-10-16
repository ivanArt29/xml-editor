#!/usr/bin/env bash
set -euo pipefail

# Display and screen settings
export DISPLAY=:99
SCREEN_GEOMETRY=${SCREEN_GEOMETRY:-1366x768x24}

# Start a virtual X server
Xvfb $DISPLAY -screen 0 $SCREEN_GEOMETRY -ac +extension GLX +render -noreset &

# Start a lightweight window manager for better window behavior
fluxbox >/tmp/fluxbox.log 2>&1 &

# Start x11vnc on port 5900 with no password for simplicity (can be changed)
x11vnc -display $DISPLAY -forever -shared -rfbport 5900 -nopw -quiet >/tmp/x11vnc.log 2>&1 &

# Start noVNC on port 6080 (websocket to VNC)
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

# Small wait to ensure services are up
sleep 1

# Run the application
cd /app
exec python main.py
