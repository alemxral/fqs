#!/bin/sh
# Start Flask Backend Server

cd "$(dirname "$0")/server"
echo "🚀 Starting Flask Backend on http://127.0.0.1:5000"
echo "Press Ctrl+C to stop"
echo ""
python run_flask.py
