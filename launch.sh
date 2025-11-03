#!/bin/zsh
# ============================================
# Holo 1.5 Local API — Launch Script (macOS)
# Safe defaults for Python 3.13 (no uvloop/httptools)
# ============================================
set -e

PROJECT_DIR="${PROJECT_DIR:-$HOME/Projects/holo15-api}"
# Use HOLO_HOST to avoid conflicts with system HOST variable
HOLO_HOST="${HOLO_HOST:-127.0.0.1}"
HOLO_PORT="${HOLO_PORT:-8000}"

# Best defaults for Apple Silicon + MPS
export PYTORCH_ENABLE_MPS_FALLBACK="${PYTORCH_ENABLE_MPS_FALLBACK:-1}"
export PYTORCH_MPS_HIGH_WATERMARK_RATIO="${PYTORCH_MPS_HIGH_WATERMARK_RATIO:-0.0}"
export HOLO_MODEL="${HOLO_MODEL:-Hcompany/Holo1.5-7B}"
export HOLO_MAX_SIDE="${HOLO_MAX_SIDE:-1440}"

cd "$PROJECT_DIR"

if [ ! -f "server.py" ]; then
  echo "❌ server.py not found in $PROJECT_DIR"
  exit 1
fi

if [ -d ".venv" ]; then
  echo "🔧 Activating venv .venv"
  source .venv/bin/activate
else
  echo "⚠️  No .venv found in $PROJECT_DIR. Launch will use system Python environment."
fi

# Check if port is already in use
if lsof -Pi :$HOLO_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
  PID=$(lsof -ti:$HOLO_PORT)
  echo "⚠️  Port $HOLO_PORT is already in use by process $PID"
  echo "💡 To kill the process and free the port, run:"
  echo "   kill -9 $PID"
  echo ""
  read -q "REPLY?Do you want to kill the process and continue? (y/n) "
  echo ""
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔪 Killing process $PID..."
    kill -9 $PID
    sleep 1
  else
    echo "❌ Aborted. Please free port $HOLO_PORT manually or use a different port."
    exit 1
  fi
fi

echo "🚀 Starting Holo 1.5 API on http://$HOLO_HOST:$HOLO_PORT ..."
# NOTE: No --loop uvloop and no --http httptools (not available on Python 3.13 yet)
exec uvicorn server:app --host "$HOLO_HOST" --port "$HOLO_PORT" --no-access-log
