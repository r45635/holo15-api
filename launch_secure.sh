#!/bin/bash
# Launch Holo 1.5 API with full security (local)

echo "🚀 Starting Holo 1.5 API - Secure Mode"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "✅ .env created. Please edit it if needed."
    echo ""
fi

# Check if API keys exist
if [ ! -f ops/api_keys.yaml ]; then
    echo "⚠️  No API keys found!"
    echo ""
    echo "Generate a key first:"
    echo "  python scripts/generate_api_key.py"
    echo ""
    exit 1
fi

# Activate venv if it exists
if [ -d .venv ]; then
    echo "📦 Activating virtual environment..."
    source .venv/bin/activate
fi

echo "🔐 Starting secure server with authentication..."
echo ""
echo "Endpoints:"
echo "  - Health:  http://127.0.0.1:8000/health"
echo "  - Chat:    http://127.0.0.1:8000/v1/chat/completions (auth required)"
echo "  - Metrics: http://127.0.0.1:8000/metrics (auth required)"
echo "  - Docs:    http://127.0.0.1:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m uvicorn server_secure:app --host 127.0.0.1 --port 8000
