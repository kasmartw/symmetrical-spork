#!/bin/bash
# Script to run the Mock API server

echo "======================================================================="
echo "🚀 Starting Mock API Server"
echo "======================================================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found!"
    echo "   Run: python3 -m venv venv && source venv/bin/activate && pip install -e '.[dev]'"
    exit 1
fi

# Activate venv
source venv/bin/activate

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "❌ Error: Flask not installed!"
    echo "   Run: pip install -e '.[dev]'"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found (optional for mock API)"
fi

echo "✅ Environment ready"
echo ""

# Run mock API
python mock_api.py
