# Virtual Environment Issues - Troubleshooting Guide

## 🔍 Common venv Issues

### Why does venv break?

1. **Absolute Paths**: venv uses absolute paths that break when:
   - You move the project directory
   - You access it from different mount points (e.g., /sgoinfre vs /home)
   - Symlinks change
   
2. **Cached Bytecode**: Python's `.pyc` files and `__pycache__` can cause:
   - Import errors
   - Module not found errors
   - Stale code execution
   
3. **PYTHONPATH Conflicts**: Environment variables can override venv:
   - System-wide PYTHONPATH
   - VSCode settings
   - Shell configuration (.bashrc, .zshrc)

4. **Corrupted pip**: Sometimes pip breaks after system Python updates

## 🛠️ Quick Fixes

### Option 1: Use the Auto-Fix Script (Recommended)
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
./fix_venv.sh
```

This will:
- Remove old venv completely
- Clear all Python cache
- Create fresh venv
- Install all dependencies
- Verify installation

### Option 2: Run Diagnostics First
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
./diagnose_venv.sh
```

This will tell you exactly what's wrong.

### Option 3: Use Robust Startup
```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
./start_robust.sh
```

This automatically checks venv health before starting.

## 🔧 Manual Fix

If scripts don't work, fix manually:

```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs

# 1. Deactivate if in venv
deactivate 2>/dev/null || true

# 2. Remove everything
rm -rf venv __pycache__ .pytest_cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete

# 3. Clear environment
unset PYTHONPATH
unset PYTHONHOME

# 4. Create fresh venv
python3 -m venv venv --clear --copies

# 5. Activate
source venv/bin/activate

# 6. Upgrade pip
python -m pip install --upgrade pip setuptools wheel

# 7. Install dependencies
pip install -r requirements.txt

# 8. Verify
python -c "import textual, flask, web3; print('✓ All imports work')"
```

## 🎯 VSCode-Specific Issues

VSCode can cause venv issues:

### Fix VSCode Python Interpreter

1. **Press** `Ctrl+Shift+P`
2. **Type**: "Python: Select Interpreter"
3. **Choose**: `./venv/bin/python` (the one in your FQS directory)
4. **Reload**: `Ctrl+Shift+P` → "Developer: Reload Window"

### Fix VSCode Settings

Add to `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/fqs/venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.envFile": "${workspaceFolder}/fqs/.env",
    "terminal.integrated.env.linux": {
        "PYTHONPATH": "",
        "PYTHONDONTWRITEBYTECODE": "1"
    }
}
```

### VSCode Terminal Not Using venv

If VSCode terminal shows wrong Python:

```bash
# Check which Python
which python
# Should show: /home/amoral-a/sgoinfre/polytrading/poly/fqs/venv/bin/python

# If not, manually activate
source /home/amoral-a/sgoinfre/polytrading/poly/fqs/venv/bin/activate
```

## 🚫 Prevention Tips

### 1. Always Use Scripts
Don't run `python app.py` directly, use:
```bash
./start.sh          # Auto-handles venv
./start_robust.sh   # With health checks
```

### 2. Clear Cache Regularly
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
```

### 3. Don't Move the Project
If you must move it:
```bash
./fix_venv.sh  # Rebuild venv in new location
```

### 4. Use --clear Flag
When recreating venv, always use `--clear`:
```bash
python3 -m venv venv --clear --copies
```

### 5. Check Environment
Before running, verify:
```bash
echo $PYTHONPATH    # Should be empty
echo $VIRTUAL_ENV   # Should be empty (before activation)
```

## 📊 Diagnostic Checklist

Run this to check everything:

```bash
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs

# 1. Python version
python3 --version
# Should be: Python 3.8+

# 2. venv module
python3 -m venv --help
# Should show help text

# 3. venv exists
ls -la venv/bin/python
# Should show file

# 4. venv works
venv/bin/python --version
# Should show Python version

# 5. pip works
venv/bin/python -m pip --version
# Should show pip version

# 6. Packages installed
venv/bin/python -c "import textual, flask, web3"
# Should return nothing (success)

# 7. No cache pollution
find . -type d -name "__pycache__" | wc -l
# Should be 0 or very low

# 8. No PYTHONPATH
echo $PYTHONPATH
# Should be empty
```

## 🆘 Still Not Working?

If venv still breaks after all fixes:

### Last Resort: Use System Python
```bash
# Install packages globally (not recommended but works)
pip3 install --user textual flask web3 httpx

# Run without venv
cd /home/amoral-a/sgoinfre/polytrading/poly/fqs
python3 app.py
```

### Nuclear Option: Reinstall Python
```bash
# Ubuntu/Debian
sudo apt remove python3 python3-pip
sudo apt install python3 python3-pip python3-venv

# Then rebuild venv
./fix_venv.sh
```

## 📝 Summary of Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `./fix_venv.sh` | Rebuild venv from scratch | venv is broken |
| `./diagnose_venv.sh` | Check what's wrong | Investigating issues |
| `./start_robust.sh` | Start with health checks | Every time |
| `./start.sh` | Normal startup | When venv is healthy |
| `./restart.sh` | Kill old processes | Before restarting |

## 🎯 Recommended Workflow

```bash
# First time setup or after issues
./fix_venv.sh

# Every time you start FQS
./restart.sh       # Clean slate
./start_robust.sh  # Safe startup

# If issues appear
./diagnose_venv.sh  # Check what's wrong
./fix_venv.sh       # Fix it
```
