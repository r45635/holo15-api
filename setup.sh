#!/bin/zsh
# ==========================================================
# Holo 1.5 Local API Server - Setup & Launch Script (MacOS)
# ==========================================================

set -e
echo "🚀 Initialisation de l'environnement Holo 1.5..."

# Dossier projet
PROJECT_DIR="$HOME/Projects/holo15-api"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Création environnement virtuel
if [ ! -d ".venv" ]; then
  echo "📦 Création de l'environnement virtuel..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Installation dépendances
echo "📚 Installation des dépendances..."
pip install --upgrade pip wheel
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install "transformers>=4.44" "accelerate>=0.33" pillow fastapi uvicorn uvloop httptools pydantic>=2

# Variables d'environnement
export PYTORCH_ENABLE_MPS_FALLBACK=1
export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
export HOLO_MODEL="Hcompany/Holo1.5-7B"
export HOLO_MAX_SIDE=1440

echo "✅ Environnement prêt. Démarrage du serveur..."
uvicorn server:app --host 127.0.0.1 --port 8000 --loop uvloop --http httptools --no-access-log
