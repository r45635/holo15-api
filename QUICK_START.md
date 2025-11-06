# 🚀 Quick Start Guide - Holo 1.5 API

Guide de démarrage rapide pour utiliser l'API Holo 1.5 en local ou via connexion externe.

## 📋 Prérequis

- macOS avec Apple Silicon (M1/M2/M3)
- Python 3.10 ou supérieur
- 16 GB RAM minimum recommandé

## ⚡ Installation Rapide

```bash
# 1. Cloner le projet
git clone https://github.com/r45635/holo15-api.git
cd holo15-api

# 2. Créer l'environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

## 🔧 Configuration

### Mode Développement (sans sécurité)

Idéal pour les tests locaux rapides :

```bash
./launch.sh
```

### Mode Production (avec sécurité)

Recommandé pour un usage réel :

```bash
# 1. Générer une clé API
python scripts/generate_api_key.py

# 2. Copier la clé dans ops/api_keys.yaml (voir sortie du script)

# 3. Configurer l'environnement (optionnel)
cp .env.example .env
# Éditer .env si nécessaire

# 4. Lancer le serveur sécurisé
./launch_secure.sh
```

Le serveur démarre sur `http://127.0.0.1:8000`

## 🎯 Utilisation Simple

### Test de santé

```bash
curl http://127.0.0.1:8000/health
```

### Requête texte simple (mode dev)

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Hcompany/Holo1.5-7B",
    "messages": [{"role": "user", "content": "Bonjour!"}],
    "max_tokens": 100
  }'
```

### Requête avec authentification (mode prod)

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer VOTRE_CLE_API" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Hcompany/Holo1.5-7B",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 100
  }'
```

## 🐍 Utilisation avec Python

### Installation du client OpenAI (optionnel)

```bash
pip install openai
```

### Exemple de code

```python
from openai import OpenAI

# Connecter à votre API locale
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="votre-cle-api-ici"  # Pas nécessaire en mode dev
)

# Envoyer une requête
response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[
        {"role": "user", "content": "Quelle est la capitale de la France?"}
    ],
    max_tokens=100
)

print(response.choices[0].message.content)
```

## 🖼️ Utilisation avec Images

### Python avec base64

```python
import base64
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="votre-cle-api"
)

# Charger et encoder l'image
with open("image.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

# Analyser l'image
response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Que vois-tu dans cette image?"},
            {"type": "image", "image": {"b64": image_b64}}
        ]
    }],
    max_tokens=200
)

print(response.choices[0].message.content)
```

## 🌐 Interface Web

Une interface web simple est disponible :

```bash
# Depuis le dossier ui/
cd ui
python -m http.server 5500
```

Ouvrir dans le navigateur : http://127.0.0.1:5500

## 🧪 Tests

### Tests de sécurité

```bash
python test_security.py
```

### Tests des clients API

```bash
python test_api_client.py
```

### Tests rapides avec curl

```bash
./test_curl.sh
```

## 📚 Documentation Complète

- **[README.md](README.md)** - Documentation générale de l'API
- **[README_SECURITY.md](README_SECURITY.md)** - Guide complet de sécurité et exemples clients
- **[docs/SECURITY.md](docs/SECURITY.md)** - Guide détaillé de déploiement en production

## 🔑 Endpoints Disponibles

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/health` | GET | Non | Vérifier l'état du serveur |
| `/v1/chat/completions` | POST | Oui (prod) | Générer des réponses texte/image |
| `/metrics` | GET | Oui | Métriques du serveur |
| `/docs` | GET | Non | Documentation Swagger |

## ⚙️ Configuration Avancée

Variables d'environnement dans `.env` :

```bash
# Modèle
HOLO_MODEL=Hcompany/Holo1.5-7B
HOLO_MAX_SIDE=1440

# Serveur
HOLO_HOST=127.0.0.1
HOLO_PORT=8000

# Rate limiting
RATE_LIMIT_IP=60/minute
RATE_LIMIT_KEY=120/minute

# Limites
MAX_BODY_MB=10.0
MAX_TOKENS_LIMIT=2048
```

Voir `.env.example` pour la liste complète.

## 🆘 Problèmes Courants

### Le serveur ne démarre pas

- Vérifier que le port 8000 n'est pas utilisé : `lsof -i :8000`
- Vérifier l'environnement virtuel : `which python`
- Vérifier les logs dans `server.log`

### Erreur "Model failed to load"

- Vérifier l'espace disque (modèle = ~14 GB)
- Vérifier la mémoire disponible
- Le premier lancement télécharge le modèle depuis Hugging Face

### Erreur 401 Unauthorized

- En mode production, vérifier que vous avez une clé API valide
- Vérifier le format du header : `Authorization: Bearer VOTRE_CLE`
- Vérifier que la clé est dans `ops/api_keys.yaml`

### Erreur 429 Too Many Requests

- Rate limit atteint, attendre quelques secondes
- Voir le header `Retry-After` pour le délai exact

## 📊 Performances

- **Premier token** : ~2-3 secondes (après warmup)
- **Tokens suivants** : ~50-100 ms/token
- **Latence typique** : 1-3 secondes pour réponses courtes
- **Device** : MPS (GPU Apple Silicon)
- **Mémoire** : ~8-10 GB pour le modèle 7B

## 🤝 Support

- Issues GitHub : https://github.com/r45635/holo15-api/issues
- Documentation : Voir les fichiers README
- Tests : Exécuter les scripts de test fournis

## 📄 Licence

Voir le fichier LICENSE du projet.
