#!/bin/sh
# FQS - Robust Startup Script with venv health checks
# Automatically fixes common venv issues

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

# Function to check venv health
check_venv_health() {
    # Check if venv exists
    if [ ! -d "venv" ]; then
        return 1
    fi
    
    # Check if python executable exists
    if [ ! -f "venv/bin/python" ]; then
        return 1
    fi
    
    # Check if venv python is actually working
    if ! venv/bin/python --version >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if pip works
    if ! venv/bin/python -m pip --version >/dev/null 2>&1; then
        return 1
    fi
    
    # Check if critical dependencies exist
    if ! venv/bin/python -c "import textual, flask, web3" 2>/dev/null; then
        return 1
    fi
    
    return 0
}

# Check venv health
echo "🔍 Checking virtual environment health..."
if check_venv_health; then
    echo "   ✓ Virtual environment is healthy"
else
    echo "   ⚠️  Virtual environment needs recreation"
    echo ""
    echo "📦 Creating fresh virtual environment..."
    
    # Remove old venv completely
    rm -rf venv __pycache__ .pytest_cache
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Create new venv
    python3 -m venv venv --clear
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        echo "Make sure python3-venv is installed:"
        echo "  sudo apt install python3-venv  # Ubuntu/Debian"
        echo "  sudo yum install python3-venv  # RHEL/CentOS"
        exit 1
    fi
    
    # Upgrade pip first
    echo "📦 Upgrading pip..."
    venv/bin/python -m pip install --upgrade pip setuptools wheel --quiet
    
    # Install dependencies
    echo "📦 Installing dependencies..."
    if [ -f "requirements.txt" ]; then
        venv/bin/python -m pip install -r requirements.txt --quiet
        if [ $? -ne 0 ]; then
            echo "❌ Failed to install dependencies"
            echo "Try manually:"
            echo "  source venv/bin/activate"
            echo "  pip install -r requirements.txt"
            exit 1
        fi
    fi
    
    echo "   ✓ Virtual environment created successfully"
fi

echo ""

# Activate virtual environment
echo "📦 Activating virtual environment..."
. venv/bin/activate

# Verify activation worked
if [ "$VIRTUAL_ENV" = "" ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "   ✓ Using: $VIRTUAL_ENV"
echo ""

# Clear Python cache to avoid import issues
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$(pwd)/..:$PYTHONPATH"  # Add project root to Python path

# Verify FQS can be imported
if ! python -c "import fqs" 2>/dev/null; then
    echo "⚠️  FQS module not found, installing..."
    cd ..
    python -m pip install -e . --quiet
    cd fqs
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

# Check if backend actually started
if ! kill -0 $FLASK_PID 2>/dev/null; then
    echo "❌ Backend failed to start. Check logs/flask.log"
    exit 1
fi

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
