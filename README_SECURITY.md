# Holo 1.5 API - Secured

API sécurisée pour le modèle Holo 1.5 7B avec authentification, rate limiting et abuse detection.

## 🚀 Démarrage Rapide

### Installation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Générer une clé API
python scripts/generate_api_key.py

# Copier la configuration
cp .env.example .env
```

### Utilisation

**Mode développement** (sans sécurité) :
```bash
./launch.sh
```

**Mode sécurisé** (recommandé) :
```bash
./launch_secure.sh
```

## 🔐 Sécurité

### Fonctionnalités

- ✅ **Authentification API Key** : Hachage bcrypt, Bearer token
- ✅ **Rate Limiting** : Token bucket (IP + clé API)
- ✅ **Abuse Detection** : Auto-blocking avec deny-list
- ✅ **Validation** : Taille body (10MB), MIME types
- ✅ **Logging** : JSON structuré + audit trail
- ✅ **Métriques** : Endpoint temps réel

### Endpoints

- `GET /health` - Health check (public)
- `POST /v1/chat/completions` - Chat (authentification requise)
- `GET /metrics` - Métriques (authentification requise)
- `GET /docs` - Documentation API

## 📡 Utilisation de l'API Externe

### Connexion et Authentification

L'API utilise le standard **Bearer Token** pour l'authentification. Vous devez inclure votre clé API dans le header `Authorization` :

```
Authorization: Bearer YOUR_API_KEY_HERE
```

### Exemples de Connexion

#### Python avec requests

```python
import requests
import base64

API_URL = "http://127.0.0.1:8000"
API_KEY = "votre-cle-api-ici"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Requête simple texte
response = requests.post(
    f"{API_URL}/v1/chat/completions",
    headers=headers,
    json={
        "model": "Hcompany/Holo1.5-7B",
        "messages": [
            {"role": "user", "content": "Bonjour, comment vas-tu ?"}
        ],
        "max_tokens": 128,
        "temperature": 0.7
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

#### Python avec OpenAI SDK

L'API est compatible avec le SDK OpenAI :

```python
from openai import OpenAI

# Initialiser le client avec votre API locale
client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="votre-cle-api-ici"
)

# Requête simple
response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[
        {"role": "user", "content": "Explique-moi l'IA en une phrase"}
    ],
    max_tokens=100,
    temperature=0.7
)

print(response.choices[0].message.content)
```

#### JavaScript / Node.js

```javascript
const API_URL = "http://127.0.0.1:8000";
const API_KEY = "votre-cle-api-ici";

async function chat(message) {
    const response = await fetch(`${API_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: "Hcompany/Holo1.5-7B",
            messages: [
                { role: "user", content: message }
            ],
            max_tokens: 128,
            temperature: 0.7
        })
    });
    
    const data = await response.json();
    return data.choices[0].message.content;
}

// Utilisation
chat("Quelle est la capitale de la France ?")
    .then(console.log)
    .catch(console.error);
```

#### cURL

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer votre-cle-api-ici" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Hcompany/Holo1.5-7B",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

### Envoi d'Images

#### Python avec base64

```python
import requests
import base64
from pathlib import Path

API_URL = "http://127.0.0.1:8000"
API_KEY = "votre-cle-api-ici"

# Lire et encoder l'image
image_path = "mon_image.jpg"
with open(image_path, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

# Envoyer la requête avec image
response = requests.post(
    f"{API_URL}/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "Hcompany/Holo1.5-7B",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "Que vois-tu dans cette image ?"},
                {"type": "image", "image": {"b64": image_b64}}
            ]
        }],
        "max_tokens": 256,
        "temperature": 0.7
    }
)

print(response.json()["choices"][0]["message"]["content"])
```

#### Python avec OpenAI SDK (vision)

```python
from openai import OpenAI
import base64

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="votre-cle-api-ici"
)

# Encoder l'image
with open("image.jpg", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "Décris cette image en détail"},
            {"type": "image", "image": {"b64": image_b64}}
        ]
    }],
    max_tokens=300
)

print(response.choices[0].message.content)
```

#### JavaScript avec image

```javascript
async function analyzeImage(imagePath, prompt) {
    // Lire l'image (Node.js)
    const fs = require('fs');
    const imageBuffer = fs.readFileSync(imagePath);
    const imageB64 = imageBuffer.toString('base64');
    
    const response = await fetch(`${API_URL}/v1/chat/completions`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            model: "Hcompany/Holo1.5-7B",
            messages: [{
                role: "user",
                content: [
                    { type: "text", text: prompt },
                    { type: "image", image: { b64: imageB64 } }
                ]
            }],
            max_tokens: 256
        })
    });
    
    const data = await response.json();
    return data.choices[0].message.content;
}
```

### Gestion des Erreurs

#### Codes de statut HTTP

| Code | Signification | Action recommandée |
|------|---------------|-------------------|
| 200  | Succès | Traiter la réponse |
| 400  | Requête invalide | Vérifier le format de la requête |
| 401  | Non authentifié | Vérifier votre clé API |
| 403  | Accès refusé | Clé expirée ou IP bloquée |
| 413  | Body trop large | Réduire la taille de l'image ou du texte |
| 415  | Format non supporté | Vérifier le format de l'image (JPEG, PNG, etc.) |
| 429  | Rate limit dépassé | Attendre avant de réessayer (voir header `Retry-After`) |
| 500  | Erreur serveur | Réessayer plus tard |
| 503  | Service indisponible | Le modèle n'est pas chargé |

#### Exemple de gestion d'erreurs en Python

```python
import requests
import time

def call_api_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "Hcompany/Holo1.5-7B",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 128
                },
                timeout=30
            )
            
            # Vérifier le statut
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            
            elif response.status_code == 429:
                # Rate limit - attendre
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limit atteint, attente de {retry_after}s...")
                time.sleep(retry_after)
                continue
            
            elif response.status_code == 401:
                raise ValueError("Clé API invalide ou expirée")
            
            elif response.status_code == 503:
                raise RuntimeError("Service temporairement indisponible")
            
            else:
                error_detail = response.json().get('detail', 'Erreur inconnue')
                raise Exception(f"Erreur API ({response.status_code}): {error_detail}")
        
        except requests.exceptions.Timeout:
            print(f"Timeout (tentative {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Backoff exponentiel
            else:
                raise
        
        except requests.exceptions.ConnectionError:
            raise RuntimeError("Impossible de se connecter à l'API")
    
    raise Exception("Nombre maximum de tentatives atteint")

# Utilisation
try:
    result = call_api_with_retry("Bonjour!")
    print(result)
except Exception as e:
    print(f"Erreur: {e}")
```

### Limites et Quotas

- **Rate limiting IP** : 60 requêtes/minute (burst: 10)
- **Rate limiting clé API** : 120 requêtes/minute (burst: 20)
- **Taille maximale du body** : 10 MB
- **Taille maximale d'image** : 2048x2048 pixels
- **Tokens max par requête** : 2048

Les limites sont configurables dans `.env`.

### Headers de réponse utiles

```
X-Request-Id: abc123...       # ID unique de la requête pour le debugging
X-RateLimit-Limit: 60         # Limite de rate
X-RateLimit-Remaining: 45     # Requêtes restantes
Retry-After: 30               # Secondes à attendre (si 429)
```

## 🧪 Tests

```bash
# Tests complets de sécurité (7 tests)
python test_security.py

# Tests rapides avec curl
./test_curl.sh
```

## 📝 Configuration

Éditer `.env` pour personnaliser :

```bash
# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE_IP=60
RATE_LIMIT_REQUESTS_PER_MINUTE_KEY=120

# Validation
MAX_BODY_MB=10

# CORS
CORS_ALLOW_ORIGINS=http://127.0.0.1:5500,http://localhost:5500

# Sécurité
ALLOW_DOCS=true  # false en production
```

## 🔑 Gestion des Clés API

### Générer une nouvelle clé

```bash
python scripts/generate_api_key.py
```

La sortie vous donnera :
- La clé en clair (à partager de façon sécurisée)
- L'entrée YAML à ajouter dans `ops/api_keys.yaml`

### Format des clés

Fichier `ops/api_keys.yaml` :

```yaml
keys:
  - key_id: "team-core"
    hash: "$2b$12$..."
    owner: "admin@example.com"
    scopes: ['*']
    created_at: "2025-11-03T00:00:00Z"
    expires_at: null  # ou date ISO
```

## 📊 Monitoring

### Métriques en temps réel

```bash
curl http://127.0.0.1:8000/metrics \
  -H "Authorization: Bearer YOUR_API_KEY"
```

Retourne :
- Nombre total de requêtes
- Répartition des codes HTTP (2xx, 4xx, 5xx)
- Latences (P50, P95)
- Statistiques abuse detection

### Logs d'audit

Tous les événements de sécurité sont tracés dans `logs/audit.log` :
- 401 : Authentification échouée
- 403 : Accès refusé
- 413 : Body trop large
- 415 : Type de média non supporté
- 429 : Rate limit dépassé

## 🌐 Interface Web

Une interface web simple est disponible dans `ui/` :

```bash
# Démarrer le serveur UI
cd ui
python -m http.server 5500
```

Puis ouvrir http://127.0.0.1:5500

L'UI supporte :
- Envoi de messages texte
- Upload d'images (drag & drop)
- Configuration (API URL, clé, modèle, paramètres)

## 📚 Documentation

- `docs/SECURITY.md` - Guide détaillé de la sécurité
- `.env.example` - Toutes les variables d'environnement disponibles

## 🛠️ Développement

### Structure du projet

```
.
├── server.py              # Serveur dev (sans sécurité)
├── server_secure.py       # Serveur prod (avec sécurité)
├── config.py              # Configuration centralisée
├── middleware.py          # Middleware de sécurité
├── security/              # Modules de sécurité
│   ├── auth.py           # Authentification
│   ├── rate_limit.py     # Rate limiting
│   └── abuse.py          # Abuse detection
├── scripts/              # Utilitaires
│   └── generate_api_key.py
├── ops/                  # Configuration opérationnelle
│   ├── api_keys.yaml     # Clés API (non committé)
│   └── denylist.json     # IPs bloquées (auto-généré)
├── logs/                 # Logs (non committé)
│   └── audit.log
└── ui/                   # Interface web
    ├── index.html
    ├── app.js
    └── styles.css
```

## 📄 Licence

Voir LICENSE

## 🤝 Support

Pour toute question ou problème, ouvrir une issue sur GitHub.
