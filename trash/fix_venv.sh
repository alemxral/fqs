#!/bin/sh
# FQS Virtual Environment Auto-Fix Script
# Completely rebuilds venv from scratch

cd "$(dirname "$0")"

echo "=========================================="
echo "🔧 FQS venv Auto-Fix"
echo "=========================================="
echo ""

# Deactivate if in venv
if [ ! -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Deactivating current virtual environment..."
    deactivate 2>/dev/null || true
fi

# Clear environment variables
echo "🧹 Clearing environment variables..."
unset PYTHONPATH
unset PYTHONHOME
export PYTHONDONTWRITEBYTECODE=1

# Kill any Python processes using this venv
echo "🛑 Stopping any processes using venv..."
pkill -f "$(pwd)/venv" 2>/dev/null || true
sleep 1

# Remove old venv completely
echo "🗑️  Removing old virtual environment..."
rm -rf venv
echo "   ✓ Removed venv/"

# Clear all Python cache
echo "🗑️  Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
echo "   ✓ Cleared __pycache__ and .pyc files"

# Create fresh venv
echo ""
echo "📦 Creating fresh virtual environment..."
python3 -m venv venv --clear --copies

if [ $? -ne 0 ]; then
    echo "❌ Failed to create venv!"
    echo "Make sure python3-venv is installed:"
    echo "  Ubuntu/Debian: sudo apt install python3-venv"
    echo "  RHEL/CentOS:   sudo yum install python3-venv"
    exit 1
fi

echo "   ✓ venv created successfully"

# Activate venv
echo ""
echo "📦 Activating venv..."
. venv/bin/activate

if [ "$VIRTUAL_ENV" = "" ]; then
    echo "❌ Failed to activate venv!"
    exit 1
fi

echo "   ✓ Activated: $VIRTUAL_ENV"

# Upgrade pip, setuptools, wheel
echo ""
echo "📦 Upgrading pip, setuptools, wheel..."
python -m pip install --upgrade pip setuptools wheel --quiet

if [ $? -ne 0 ]; then
    echo "❌ Failed to upgrade pip!"
    exit 1
fi

PIP_VERSION=$(python -m pip --version)
echo "   ✓ $PIP_VERSION"

# Install dependencies
echo ""
echo "📦 Installing dependencies from requirements.txt..."

if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

python -m pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies!"
    echo "Check requirements.txt and try manually:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "   ✓ All dependencies installed"

# Install FQS package in editable mode
echo ""
echo "📦 Installing FQS package in editable mode..."
cd ..
python -m pip install -e . --quiet

if [ $? -ne 0 ]; then
    echo "❌ Failed to install FQS package!"
    echo "Continuing anyway..."
else
    echo "   ✓ FQS package installed"
fi

cd fqs

# Verify critical packages
echo ""
echo "🔍 Verifying critical packages..."

check_package() {
    if python -c "import $1" 2>/dev/null; then
        echo "   ✓ $1"
        return 0
    else
        echo "   ✗ $1 (missing)"
        return 1
    fi
}

MISSING=0
check_package "textual" || MISSING=$((MISSING + 1))
check_package "flask" || MISSING=$((MISSING + 1))
check_package "web3" || MISSING=$((MISSING + 1))
check_package "httpx" || MISSING=$((MISSING + 1))
check_package "asyncio" || MISSING=$((MISSING + 1))

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "⚠️  $MISSING critical packages are missing!"
    echo "Try installing manually:"
    echo "  source venv/bin/activate"
    echo "  pip install textual flask web3 httpx"
fi

# Success
echo ""
echo "=========================================="
echo "✅ Virtual Environment Fixed!"
echo "=========================================="
echo ""
echo "You can now run FQS:"
echo "  ./start.sh              - Start both backend + frontend"
echo "  ./start_robust.sh       - Start with health checks"
echo ""
echo "Or manually:"
echo "  source venv/bin/activate"
echo "  python app.py"
echo ""

deactivate
