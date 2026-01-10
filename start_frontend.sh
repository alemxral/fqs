#!/bin/sh
# Start Textual TUI Frontend

cd "$(dirname "$0")"

# Kill any existing frontend
echo "🧹 Cleaning up old frontend processes..."
pkill -f "python.*app.py" 2>/dev/null && echo "   ✓ Killed old frontend" || echo "   • No old frontend found"
pkill -f "python.*fqs" 2>/dev/null || true
sleep 1
echo ""

echo "🎨 Starting FQS Terminal UI"
echo "Press Ctrl+C to stop"
echo ""
python app.py
