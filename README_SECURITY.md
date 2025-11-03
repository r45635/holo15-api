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
