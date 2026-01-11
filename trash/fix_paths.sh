#!/bin/sh
# Permanent Path Fix for FQS
# Installs FQS as a proper Python package to avoid PYTHONPATH issues

cd "$(dirname "$0")"

echo "=========================================="
echo "🔧 FQS Path Fix - Permanent Solution"
echo "=========================================="
echo ""

# Check if in venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "📦 Activating virtual environment..."
    if [ ! -d "venv" ]; then
        echo "❌ No venv found! Run ./fix_venv.sh first"
        exit 1
    fi
    . venv/bin/activate
fi

echo "Current Python: $(which python)"
echo "Current venv: $VIRTUAL_ENV"
echo ""

# Navigate to project root
cd ..
PROJECT_ROOT=$(pwd)
echo "Project root: $PROJECT_ROOT"
echo ""

# Install FQS package in editable mode
echo "📦 Installing FQS as editable package..."
python -m pip install -e . --quiet

if [ $? -ne 0 ]; then
    echo "❌ Failed to install FQS package!"
    echo ""
    echo "Try manually:"
    echo "  cd $PROJECT_ROOT"
    echo "  source fqs/venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

echo "   ✓ FQS package installed in editable mode"
echo ""

# Test import
echo "🧪 Testing import..."
if python -c "import fqs; print(f'  ✓ fqs module location: {fqs.__file__}')" 2>/dev/null; then
    echo ""
    echo "=========================================="
    echo "✅ Success! Path issues fixed!"
    echo "=========================================="
    echo ""
    echo "Now you can:"
    echo "  1. Import fqs from anywhere in the venv"
    echo "  2. Run: python -c 'import fqs'"
    echo "  3. No more PYTHONPATH needed!"
    echo ""
    echo "The package is installed in 'editable' mode,"
    echo "so changes to the code will be reflected immediately."
    echo ""
else
    echo "❌ Import still failing!"
    echo ""
    echo "Manual fix:"
    echo "  1. cd $PROJECT_ROOT"
    echo "  2. source fqs/venv/bin/activate"
    echo "  3. pip install -e ."
    echo ""
fi

cd fqs
deactivate 2>/dev/null || true
