#!/bin/sh
# Quick Restart Script - Kills old processes and starts fresh FQS

echo "=============================================="
echo "🔄 FQS Quick Restart"
echo "=============================================="
echo ""

# Navigate to FQS directory
cd "$(dirname "$0")/.."

# Kill all FQS processes
echo "🧹 Cleaning up all FQS processes..."
pkill -f "python.*app.py" 2>/dev/null && echo "   ✓ Killed old frontend"
pkill -f "python.*run_flask.py" 2>/dev/null && echo "   ✓ Killed old backend"
pkill -f "python.*fqs" 2>/dev/null && echo "   ✓ Killed other FQS instances"
sleep 2
echo ""

echo "✨ All old processes cleaned up!"
echo ""
echo "Now run one of these to start FQS:"
echo "  ./start.sh              - Start both backend + frontend"
echo "  ./start_backend.sh      - Start backend only"
echo "  ./start_frontend.sh     - Start frontend only"
echo ""
