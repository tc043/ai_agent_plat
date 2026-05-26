#!/bin/bash
# AI Agent Platform & Sandbox — Start the platform
echo "🔮 Starting AI Agent Platform & Sandbox..."
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:8000"
echo ""
cd "$(dirname "$0")"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
