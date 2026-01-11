#!/bin/sh
# Start Flask Backend Server

cd "$(dirname "$0")/server"

# Kill any existing Flask backend
echo "🧹 Cleaning up old backend processes..."
pkill -f "python.*run_flask.py" 2>/dev/null && echo "   ✓ Killed old backend" || echo "   • No old backend found"
sleep 1
echo ""

echo "🚀 Starting Flask Backend on http://127.0.0.1:5000"
echo "Press Ctrl+C to stop"
echo ""
python run_flask.py
