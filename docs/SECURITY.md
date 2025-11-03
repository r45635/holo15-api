# 🔒 Security Guide - Holo 1.5 API

Complete guide for securing and deploying the Holo 1.5 API in production.

## Table of Contents

1. [Security Overview](#security-overview)
2. [API Key Management](#api-key-management)
3. [Rate Limiting](#rate-limiting)
4. [Abuse Detection](#abuse-detection)
5. [CORS Configuration](#cors-configuration)
6. [Deployment](#deployment)
7. [Monitoring](#monitoring)
8. [Best Practices](#best-practices)

## Security Overview

The secure version of Holo 1.5 API includes:

- ✅ **API Key Authentication** - Bearer token with bcrypt hashing
- ✅ **Rate Limiting** - Per-IP and per-key limits with token bucket algorithm
- ✅ **Abuse Detection** - Heuristic-based blocking with deny-list
- ✅ **Request Validation** - Body size, image format, token limits
- ✅ **Structured Logging** - JSON logs with request IDs and audit trail
- ✅ **CORS Control** - Whitelist-based origin restrictions
- ✅ **TLS Termination** - Automatic HTTPS via Caddy/Nginx
- ✅ **Security Headers** - HSTS, CSP, X-Frame-Options, etc.

## API Key Management

### Generating API Keys

Use the provided script to generate secure API keys:

```bash
python scripts/generate_api_key.py
```

Follow the prompts to set:
- **Key ID**: Unique identifier (e.g., `team-core`, `partner-acme`)
- **Owner**: Email address for accountability
- **Scopes**: Permissions (`chat:read`, `chat:write`, `*`)
- **Expiration**: When the key should expire

The script outputs:
1. **Plain-text API key** - Share securely with the user (ONE TIME ONLY)
2. **Bcrypt hash** - Add to `ops/api_keys.yaml`
3. **YAML entry** - Copy to your API keys file

### API Keys File Format

File: `ops/api_keys.yaml`

```yaml
keys:
  - key_id: "team-core"
    hash: "$2b$12$..."
    owner: "admin@example.com"
    scopes: ["*"]
    created_at: "2025-01-01T00:00:00Z"
    expires_at: "2026-01-01T00:00:00Z"
```

### Security Best Practices

- ✅ Never commit `ops/api_keys.yaml` to git (add to `.gitignore`)
- ✅ Rotate keys every 3-6 months
- ✅ Use strong random keys (32+ characters)
- ✅ Set expiration dates for all keys
- ✅ Remove unused keys immediately
- ✅ Use scopes to limit permissions
- ✅ Share keys via secure channels (not email/Slack)

### Using API Keys

Include the API key in requests:

```bash
curl -X POST https://yourdomain.com/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

Python example:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://yourdomain.com/v1",
    api_key="YOUR_API_KEY_HERE"
)

response = client.chat.completions.create(
    model="Hcompany/Holo1.5-7B",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Rate Limiting

### Configuration

Set in environment variables or `.env`:

```bash
# IP-based limits (unauthenticated)
RATE_LIMIT_IP=60/minute      # 60 requests per minute
BURST_IP=10                   # Allow burst of 10

# API key limits (authenticated)
RATE_LIMIT_KEY=120/minute     # 120 requests per minute
BURST_KEY=20                  # Allow burst of 20
```

### Rate Limit Algorithm

Uses **token bucket** algorithm:
- Tokens refill at constant rate
- Each request consumes 1 token
- Burst allows temporary spikes
- Returns 429 when depleted

### Response Headers

When rate limit exceeded:

```
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
```

## Abuse Detection

### Automatic Blocking

The API automatically detects and blocks abusive behavior:

**Triggers:**
- Too many failed requests (4xx/5xx errors)
- Invalid images repeatedly
- Suspicious patterns

**Configuration:**

```bash
ABUSE_THRESHOLD_ERRORS=5      # Block after 5 errors
ABUSE_WINDOW_SECONDS=30       # Within 30 seconds
DENYLIST_FILE=ops/denylist.txt
```

### Deny-List

Blocked IPs/keys are written to `ops/denylist.txt`:

```
192.168.1.100  # Blocked: 5 errors in 30s at 2025-11-03 10:30:00
key:suspicious-client  # Blocked: invalid_image at 2025-11-03 10:31:00
```

To unblock, remove the entry and restart the API.

### Monitoring Abuse

Check abuse stats via `/metrics` endpoint (requires admin scope):

```bash
curl -H "Authorization: Bearer ADMIN_KEY" \
  https://yourdomain.com/metrics
```

Returns:
```json
{
  "abuse_stats": {
    "denied_count": 3,
    "tracked_entities": 150,
    "threshold_errors": 5,
    "window_seconds": 30
  }
}
```

## CORS Configuration

### Setting Allowed Origins

```bash
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

**Important:**
- Never use `*` in production
- Include protocol (`https://`)
- No trailing slashes
- Comma-separated list

### Testing CORS

```bash
curl -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://yourdomain.com/v1/chat/completions
```

Should return:
```
Access-Control-Allow-Origin: https://yourdomain.com
Access-Control-Allow-Methods: POST, GET, OPTIONS
```

## Deployment

### Option 1: Docker Compose (Recommended)

**Prerequisites:**
- Docker and Docker Compose installed
- Domain name pointing to your server
- API keys file created

**Steps:**

1. **Clone and configure:**

```bash
cd holo15-api
cp .env.example .env
# Edit .env with your settings
```

2. **Create API keys:**

```bash
python scripts/generate_api_key.py
# Add output to ops/api_keys.yaml
```

3. **Update Caddyfile:**

```bash
# Edit Caddyfile
# Replace 'yourdomain.com' with your actual domain
```

4. **Build and start:**

```bash
docker-compose up -d
```

5. **Check logs:**

```bash
docker-compose logs -f api
docker-compose logs -f caddy
```

6. **Test:**

```bash
curl https://yourdomain.com/health
```

### Option 2: Manual Deployment

**Prerequisites:**
- Linux server with Python 3.13
- Nginx or Caddy for reverse proxy
- SSL certificate (Let's Encrypt)

**Steps:**

1. **Install dependencies:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env
source .env
```

3. **Create API keys:**

```bash
python scripts/generate_api_key.py
```

4. **Run with systemd:**

Create `/etc/systemd/system/holo-api.service`:

```ini
[Unit]
Description=Holo 1.5 API
After=network.target

[Service]
Type=simple
User=holoapi
WorkingDirectory=/opt/holo15-api
EnvironmentFile=/opt/holo15-api/.env
ExecStart=/opt/holo15-api/.venv/bin/python -m uvicorn server_secure:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable holo-api
sudo systemctl start holo-api
```

5. **Configure Nginx:**

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
    }
}
```

## Monitoring

### Logs

**Application logs** (JSON format):

```bash
tail -f logs/app.log | jq .
```

Example:
```json
{
  "timestamp": "2025-11-03 10:30:00",
  "level": "INFO",
  "message": "POST /v1/chat/completions -> 200",
  "request_id": "a1b2c3d4",
  "method": "POST",
  "path": "/v1/chat/completions",
  "ip": "203.0.113.45",
  "user": "team-core",
  "status": 200,
  "latency_ms": 2345.67
}
```

**Audit logs** (security events):

```bash
tail -f logs/audit.log | jq .
```

### Metrics Endpoint

Access via `/metrics` (requires admin scope):

```bash
curl -H "Authorization: Bearer ADMIN_KEY" \
  https://yourdomain.com/metrics | jq .
```

Returns:
```json
{
  "requests_total": 1234,
  "requests_2xx": 1200,
  "requests_4xx": 30,
  "requests_5xx": 4,
  "latency_p50_ms": 1234.56,
  "latency_p95_ms": 3456.78,
  "abuse_stats": {...}
}
```

### Health Checks

```bash
curl https://yourdomain.com/health
```

Returns:
```json
{
  "status": "ok",
  "device": "cuda",
  "model": "Hcompany/Holo1.5-7B",
  "version": "1.0.0"
}
```

## Best Practices

### Security Checklist

- [ ] API keys file not in git
- [ ] Strong random API keys (32+ chars)
- [ ] Keys have expiration dates
- [ ] CORS limited to your domains
- [ ] `/docs` disabled in production (`ALLOW_DOCS=false`)
- [ ] Running behind TLS reverse proxy
- [ ] Rate limits configured appropriately
- [ ] Abuse detection enabled
- [ ] Logs stored securely
- [ ] Regular key rotation schedule
- [ ] Monitoring and alerting set up

### Performance Tuning

**Rate Limits:**
- Start conservative (60/min for IP, 120/min for keys)
- Monitor actual usage
- Adjust based on capacity and abuse patterns

**Request Limits:**
- `MAX_BODY_MB`: Balance between usability and DoS protection
- `MAX_IMAGE_SIDE`: Larger = slower inference, more memory
- `MAX_TOKENS_LIMIT`: Prevent excessive generation times

**Resources:**
- Allocate enough memory for model (8-16GB)
- CPU/GPU as needed for inference speed
- Monitor latency metrics

### Incident Response

**If API key is compromised:**

1. Remove key from `ops/api_keys.yaml`
2. Restart API
3. Generate new key
4. Notify user securely
5. Check audit logs for unauthorized usage

**If under attack:**

1. Check deny-list: `cat ops/denylist.txt`
2. Review audit logs: `grep 429 logs/audit.log`
3. Tighten rate limits temporarily
4. Block attacking IPs in firewall
5. Contact hosting provider if needed

### Regular Maintenance

**Weekly:**
- Review audit logs for anomalies
- Check deny-list growth
- Verify disk space for logs

**Monthly:**
- Rotate logs
- Review and remove expired keys
- Update dependencies
- Check for model updates

**Quarterly:**
- Rotate all active API keys
- Security audit
- Load testing
- Update documentation

## Support

For issues or questions:
- Check logs first: `logs/app.log` and `logs/audit.log`
- Review this security guide
- Check main [README.md](../README.md) for API usage
- Check [docs/API_GUIDE.md](API_GUIDE.md) for detailed API docs

## License

Same as main project. Use responsibly and secure your deployment!
