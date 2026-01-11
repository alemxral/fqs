#!/bin/sh
# FQS Virtual Environment Diagnostic and Fix Tool
# Run this if you have venv issues

cd "$(dirname "$0")"

echo "=========================================="
echo "🔧 FQS venv Diagnostic Tool"
echo "=========================================="
echo ""

# Colors for output (if supported)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_success() {
    echo "   ${GREEN}✓${NC} $1"
}

print_error() {
    echo "   ${RED}✗${NC} $1"
}

print_warning() {
    echo "   ${YELLOW}⚠${NC} $1"
}

echo "🔍 Running diagnostics..."
echo ""

# Check 1: Python3 availability
echo "1. Checking Python3..."
if command -v python3 >/dev/null 2>&1; then
    PY_VERSION=$(python3 --version)
    print_success "Python3 found: $PY_VERSION"
else
    print_error "Python3 not found!"
    echo "   Install: sudo apt install python3"
    exit 1
fi

# Check 2: python3-venv module
echo ""
echo "2. Checking python3-venv module..."
if python3 -m venv --help >/dev/null 2>&1; then
    print_success "python3-venv is installed"
else
    print_error "python3-venv not installed!"
    echo "   Install: sudo apt install python3-venv"
    exit 1
fi

# Check 3: Current venv status
echo ""
echo "3. Checking current venv..."
if [ -d "venv" ]; then
    print_warning "venv directory exists"
    
    # Check if venv python works
    if venv/bin/python --version >/dev/null 2>&1; then
        print_success "venv python is executable"
        VENV_PY_VERSION=$(venv/bin/python --version)
        echo "      Version: $VENV_PY_VERSION"
    else
        print_error "venv python is broken!"
    fi
    
    # Check pip
    if venv/bin/python -m pip --version >/dev/null 2>&1; then
        print_success "pip is working"
        PIP_VERSION=$(venv/bin/python -m pip --version)
        echo "      $PIP_VERSION"
    else
        print_error "pip is broken!"
    fi
    
    # Check textual
    if venv/bin/python -c "import textual" 2>/dev/null; then
        print_success "textual is installed"
    else
        print_error "textual not found in venv"
    fi
    
    # Check flask
    if venv/bin/python -c "import flask" 2>/dev/null; then
        print_success "flask is installed"
    else
        print_error "flask not found in venv"
    fi
    
else
    print_warning "No venv found (will be created)"
fi

# Check 4: __pycache__ pollution
echo ""
echo "4. Checking for cached bytecode..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l)
PYC_COUNT=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l)

if [ $PYCACHE_COUNT -gt 0 ] || [ $PYC_COUNT -gt 0 ]; then
    print_warning "Found $PYCACHE_COUNT __pycache__ dirs and $PYC_COUNT .pyc files"
    echo "   These can cause import issues"
else
    print_success "No stale bytecode found"
fi

# Check 5: PYTHONPATH conflicts
echo ""
echo "5. Checking environment variables..."
if [ ! -z "$PYTHONPATH" ]; then
    print_warning "PYTHONPATH is set: $PYTHONPATH"
    echo "   This can cause import conflicts"
else
    print_success "PYTHONPATH is not set"
fi

if [ ! -z "$VIRTUAL_ENV" ]; then
    print_warning "Already in a virtual environment: $VIRTUAL_ENV"
    echo "   Deactivate first with: deactivate"
else
    print_success "Not in a virtual environment"
fi

# Check 6: File permissions
echo ""
echo "6. Checking file permissions..."
if [ -w "." ]; then
    print_success "Current directory is writable"
else
    print_error "Current directory is not writable!"
fi

# Summary and recommendations
echo ""
echo "=========================================="
echo "📊 Summary & Recommendations"
echo "=========================================="
echo ""

ISSUES=0

# Count issues
if [ ! -d "venv" ] || ! venv/bin/python --version >/dev/null 2>&1; then
    ISSUES=$((ISSUES + 1))
fi

if [ $PYCACHE_COUNT -gt 0 ] || [ $PYC_COUNT -gt 0 ]; then
    ISSUES=$((ISSUES + 1))
fi

if [ ! -z "$PYTHONPATH" ]; then
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "${GREEN}✨ No issues found!${NC}"
    echo ""
    echo "Your venv should be working. If you still have problems:"
    echo "  1. Make sure to activate venv: source venv/bin/activate"
    echo "  2. Or use the start scripts: ./start.sh"
else
    echo "${YELLOW}Found $ISSUES potential issue(s)${NC}"
    echo ""
    echo "🔧 Recommended fixes:"
    echo ""
    
    if [ ! -d "venv" ] || ! venv/bin/python --version >/dev/null 2>&1; then
        echo "1. Recreate virtual environment:"
        echo "   rm -rf venv"
        echo "   python3 -m venv venv --clear"
        echo "   source venv/bin/activate"
        echo "   pip install -r requirements.txt"
        echo ""
    fi
    
    if [ $PYCACHE_COUNT -gt 0 ] || [ $PYC_COUNT -gt 0 ]; then
        echo "2. Clear Python cache:"
        echo "   find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null"
        echo "   find . -type f -name '*.pyc' -delete"
        echo ""
    fi
    
    if [ ! -z "$PYTHONPATH" ]; then
        echo "3. Clear PYTHONPATH:"
        echo "   unset PYTHONPATH"
        echo ""
    fi
    
    echo "Or run the automatic fix:"
    echo "   ./fix_venv.sh"
fi

echo ""
