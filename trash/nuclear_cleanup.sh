#!/bin/sh
# Nuclear venv cleanup - kills everything and forces removal

cd "$(dirname "$0")"

echo "=========================================="
echo "💣 Nuclear venv Cleanup"
echo "=========================================="
echo ""

# Kill ALL Python processes
echo "🛑 Killing all Python processes in project..."
pkill -9 -f "python.*$(pwd)" 2>/dev/null || true
pkill -9 -f "python.*fqs" 2>/dev/null || true
pkill -9 -f "python.*app.py" 2>/dev/null || true
pkill -9 -f "python.*run_flask" 2>/dev/null || true
sleep 2

# Force unmount if needed (for network drives)
if mount | grep -q "$(pwd)/venv"; then
    echo "🔓 Unmounting venv..."
    sudo umount -f "$(pwd)/venv" 2>/dev/null || true
fi

# Try to remove with force
echo "🗑️  Force removing venv..."
rm -rf venv 2>/dev/null || true

# If still exists, try harder
if [ -d "venv" ]; then
    echo "⚠️  venv still exists, using chmod to unlock..."
    chmod -R 777 venv 2>/dev/null || true
    find venv -type d -exec chmod 755 {} \; 2>/dev/null || true
    rm -rf venv 2>/dev/null || true
fi

# If STILL exists, move it out of the way
if [ -d "venv" ]; then
    echo "⚠️  Cannot remove venv, moving to venv.old..."
    mv venv "venv.old.$(date +%s)" 2>/dev/null || true
fi

# Clear all cache
echo "🗑️  Clearing cache..."
find . -type d -name "__pycache__" -exec chmod -R 777 {} \; 2>/dev/null || true
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Now create fresh venv:"
echo "  python3 -m venv venv --clear"
echo "  source venv/bin/activate"
echo "  pip install -r requirements.txt"
echo ""
echo "Or use the fix script:"
echo "  ./fix_venv.sh"
echo ""
