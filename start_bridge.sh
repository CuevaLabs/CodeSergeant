#!/bin/bash
# Start Code Sergeant Python Bridge Server

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Error: Virtual environment not found. Run: python3 -m venv .venv"
    exit 1
fi

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Installing bridge dependencies..."
    pip install flask flask-cors > /dev/null 2>&1
fi

# Start bridge server
echo "Starting Code Sergeant Bridge Server on http://127.0.0.1:5050"
python bridge/server.py

