#!/bin/sh
# Quick fix script - removes conflicting directories and recreates venv

cd "$(dirname "$0")"

echo "Fixing FQS setup..."
echo ""

# Remove conflicting directories
echo "1. Removing conflicting types/ and utilities/ directories..."
rm -rf types utilities venv
echo "   ✓ Cleaned up"
echo ""

# Create fresh venv
echo "2. Creating fresh virtual environment..."
python3 -m venv venv
echo "   ✓ venv created"
echo ""

# Activate and install
echo "3. Installing dependencies..."
. venv/bin/activate
python -m pip install --upgrade pip setuptools wheel -q
python -m pip install -r requirements.txt
echo "   ✓ Dependencies installed"
echo ""

echo "✅ Setup complete!"
echo ""
echo "Now run: ./start.sh"
