#!/usr/bin/env bash
# SMC Terminal - Quick Start Script
# Run this once to install dependencies, then open http://127.0.0.1:8050

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$SCRIPT_DIR/../venv"

# Activate the venv if it exists, otherwise use system pip
if [ -d "$VENV" ]; then
    echo "Using venv at $VENV"
    "$VENV/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    echo "Starting SMC Terminal..."
    "$VENV/bin/python3" "$SCRIPT_DIR/app.py"
else
    echo "No venv found - using system pip"
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
    echo "Starting SMC Terminal..."
    python3 "$SCRIPT_DIR/app.py"
fi
