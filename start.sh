#!/bin/sh
# FQS - Unified Startup Script
# Starts both Flask backend and Textual frontend

cd "$(dirname "$0")"

echo "=========================================="
echo "🚀 FQS - Football Quick Shoot Terminal"
echo "=========================================="
echo ""

# Kill any existing FQS processes
echo "🧹 Cleaning up old processes..."
pkill -f "python.*app.py" 2>/dev/null && echo "   ✓ Killed old frontend" || echo "   • No old frontend found"
pkill -f "python.*run_flask.py" 2>/dev/null && echo "   ✓ Killed old backend" || echo "   • No old backend found"
pkill -f "python.*fqs" 2>/dev/null && echo "   ✓ Killed old FQS instances" || true
sleep 1
echo ""

# Check if virtual environment exists and is valid
if [ ! -d "venv" ] || [ ! -f "venv/bin/python" ]; then
    echo "📦 Creating virtual environment..."
    rm -rf venv
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Make sure python3-venv is installed"
        exit 1
    fi
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
. venv/bin/activate

# Verify pip works, reinstall if needed
if ! python -m pip --version >/dev/null 2>&1; then
    echo "⚠️  pip is broken, recreating venv..."
    deactivate 2>/dev/null
    rm -rf venv
    python3 -m venv venv
    . venv/bin/activate
fi

# Set PYTHONPATH to project root
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"

# Check if dependencies are installed
if ! python -c "import textual" 2>/dev/null; then
    echo "⚠️  Installing dependencies (this may take a minute)..."
    python -m pip install --upgrade pip setuptools wheel
    python -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        echo "Check requirements.txt and try manually:"
        echo "  source venv/bin/activate"
        echo "  pip install -r requirements.txt"
        exit 1
    fi
    echo "✓ Dependencies installed"
    echo ""
fi

# Install FQS package if not already installed
if ! python -c "import fqs" 2>/dev/null; then
    echo "📦 Installing FQS package..."
    cd ..
    python -m pip install -e . --quiet
    cd fqs
    echo "✓ FQS package installed"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Flask backend in background
echo "1️⃣  Starting Flask Backend..."
python server/run_flask.py > logs/flask.log 2>&1 &
FLASK_PID=$!
echo "   ✓ Backend running (PID: $FLASK_PID)"
echo "   📋 Logs: logs/flask.log"
echo ""

# Wait for Flask to initialize
sleep 2

# Start Textual frontend in foreground
echo "2️⃣  Starting Textual Frontend..."
echo "   Press Ctrl+C to stop both services"
echo ""
echo "=========================================="
echo ""

# Trap Ctrl+C to cleanup
trap "echo ''; echo '🛑 Stopping services...'; kill $FLASK_PID 2>/dev/null; echo '✓ Backend stopped'; deactivate; exit 0" INT TERM

# Run frontend (blocking)
python app.py

# If frontend exits normally, cleanup
kill $FLASK_PID 2>/dev/null
deactivate
echo ""
echo "✓ All services stopped"
echo "✅ FQS Started!"
echo ""
echo "📝 Quick Start:"
echo "  1. Welcome screen will appear in Textual TUI"
echo "  2. Press Enter to see football markets"
echo "  3. Select a match and press Enter to trade"
echo "  4. Use Ctrl+Y/Ctrl+N for quick buy YES/NO"
echo ""
echo "📚 Full documentation: README.md"
echo ""
