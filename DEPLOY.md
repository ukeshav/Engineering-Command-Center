# Deployment Guide — AI Engineering Command Center

This guide covers a full production deployment on a fresh Ubuntu 22.04 server (AWS Lightsail or any VPS).  
Follow sections in order. The result is a hardened, SSL-enabled, production-ready stack.

---

## Architecture Overview

```
Internet
   │
   ▼
nginx (80 → redirect, 443 SSL)
   ├── /api/v1/*  → FastAPI backend  (127.0.0.1:8000)
   └── /*         → Next.js frontend (127.0.0.1:3000)
                          │
                    FastAPI backend
                          ├── Gemini API  (outbound HTTPS)
                          ├── GitHub API  (outbound HTTPS)
                          └── Qdrant      (127.0.0.1:6333, Docker)
```

- **OS**: Ubuntu 22.04 LTS  
- **Backend**: Python 3.11 + FastAPI + Uvicorn (systemd)  
- **Frontend**: Node.js 20 + Next.js (systemd)  
- **Vector DB**: Qdrant in Docker (localhost-only)  
- **Reverse proxy**: nginx with Let's Encrypt SSL  
- **Firewall**: UFW + cloud security group (ports 22, 80, 443 only)

---

## Prerequisites

### Cloud / DNS
- A VPS with a **public IP** (AWS Lightsail, EC2, DigitalOcean, etc.)
- A **domain name** pointing to that IP via an A record (DNS TTL propagated before running certbot)
- Inbound firewall rules in your cloud console: **TCP 22, 80, 443** only

### Secrets & API Keys you need before starting
| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 credentials |
| `GITHUB_TOKEN` | GitHub → Settings → Developer Settings → Personal Access Tokens (scopes: `repo`, `read:org`) |
| `SECRET_KEY` | Generate: `openssl rand -hex 32` |

### Google OAuth setup
1. Go to **Google Cloud Console → APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add Authorized redirect URI: `https://yourdomain.com/api/auth/callback`
4. Save the Client ID and Client Secret

---

## Step 1 — SSH into the server

```bash
chmod 600 your-key.pem
ssh -i your-key.pem ubuntu@<SERVER_IP>
```

---

## Step 2 — System updates

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y git curl unzip build-essential ca-certificates gnupg
```

---

## Step 3 — Install Docker (for Qdrant)

```bash
# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker apt repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow ubuntu user to run Docker without sudo
sudo usermod -aG docker ubuntu
newgrp docker   # apply group change in current shell
```

---

## Step 4 — Install Python 3.11

Ubuntu 22.04 ships with Python 3.10. The app requires 3.11+ (`datetime.UTC`, `StrEnum`).

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
```

---

## Step 5 — Install Node.js 20

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node --version   # should print v20.x.x
```

---

## Step 6 — Install nginx

```bash
sudo apt-get install -y nginx
sudo systemctl enable nginx
```

---

## Step 7 — Clone the repository

```bash
cd ~
git clone https://github.com/Engineering-Command-Center/ai-engineering-command-center.git engineeringCommandCenter
cd engineeringCommandCenter
```

---

## Step 8 — Configure environment variables

```bash
cp .env.example .env
nano .env
```

Fill in all values. Key production settings:

```env
ENVIRONMENT=production
DEBUG=false

# Gemini
GEMINI_API_KEY=your_gemini_api_key

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SECRET_KEY=<output of: openssl rand -hex 32>
ALLOWED_EMAIL_DOMAIN=yourdomain.com
FRONTEND_URL=https://yourdomain.com

# GitHub
GITHUB_TOKEN=ghp_your_token
GITHUB_ORG=your-org-name

# Qdrant (stays on localhost)
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Repos — adjust to your org's naming conventions
REPOS_BASE_PATH=/home/ubuntu/repos
REPO_INCLUDE_PATTERNS=["*"]
REPO_EXCLUDE_PATTERNS=["experimental-*","poc-*"]

# Frontend
NEXT_PUBLIC_API_URL=https://yourdomain.com
ALLOWED_ORIGINS=["https://yourdomain.com"]
```

---

## Step 9 — Start Qdrant (Docker)

The `docker-compose.yml` binds Qdrant to **localhost only** for security.

```bash
cd ~/engineeringCommandCenter
docker compose up -d

# Verify it's running
curl http://localhost:6333/readyz   # should return: {"result":true,...}
```

---

## Step 10 — Set up the Python backend

```bash
cd ~/engineeringCommandCenter/backend

# Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify it starts (Ctrl+C to stop after confirming)
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

---

## Step 11 — Build the Next.js frontend

```bash
cd ~/engineeringCommandCenter/frontend

# Install dependencies
npm install

# Build for production
npm run build
```

> **Note**: If the server has restricted outbound internet (e.g., AWS blocking port 443), build on your local machine and SCP the `.next/` folder to the server:
> ```bash
> # Run locally:
> npm run build
> scp -i your-key.pem -r .next ubuntu@<SERVER_IP>:~/engineeringCommandCenter/frontend/
> ```

---

## Step 12 — Create systemd services

### Backend service

```bash
sudo nano /etc/systemd/system/ecc-backend.service
```

```ini
[Unit]
Description=ECC FastAPI Backend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/engineeringCommandCenter/backend
EnvironmentFile=/home/ubuntu/engineeringCommandCenter/.env
ExecStart=/home/ubuntu/engineeringCommandCenter/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Frontend service

```bash
sudo nano /etc/systemd/system/ecc-frontend.service
```

```ini
[Unit]
Description=ECC Next.js Frontend
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/engineeringCommandCenter/frontend
Environment=NODE_ENV=production
Environment=API_INTERNAL_URL=http://localhost:8000
ExecStart=/usr/bin/node /home/ubuntu/engineeringCommandCenter/frontend/node_modules/.bin/next start --hostname 127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

> `API_INTERNAL_URL` tells Next.js server-side routes to call the backend directly on localhost, bypassing any outbound network restrictions.

### Enable and start both services

```bash
sudo systemctl daemon-reload
sudo systemctl enable ecc-backend ecc-frontend
sudo systemctl start ecc-backend ecc-frontend

# Check status
sudo systemctl status ecc-backend
sudo systemctl status ecc-frontend
```

---

## Step 13 — Configure nginx

### Disable the default site

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

### Create the site config

```bash
sudo nano /etc/nginx/sites-available/engineering-command-center
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    # SSL certificates (filled in by Certbot — see Step 14)
    # ssl_certificate ...
    # ssl_certificate_key ...

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Block CVE-2025-55182 (Next.js Server Action RCE) at proxy level
    set $block_next_action 0;
    if ($http_next_action ~* ".+") { set $block_next_action 1; }
    if ($block_next_action) { return 403; }

    # FastAPI backend
    location /api/v1/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # Next.js frontend (with WebSocket support for HMR)
    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade           $http_upgrade;
        proxy_set_header   Connection        "upgrade";
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

### Enable the site and test

```bash
sudo ln -s /etc/nginx/sites-available/engineering-command-center /etc/nginx/sites-enabled/
sudo nginx -t          # must print "syntax is ok"
sudo systemctl reload nginx
```

---

## Step 14 — SSL certificate with Let's Encrypt

> DNS must be pointing to your server's IP before running this step. Certbot will fail if the domain doesn't resolve correctly.

```bash
sudo apt-get install -y certbot python3-certbot-nginx

sudo certbot --nginx -d yourdomain.com

# Follow prompts:
# - Enter your email
# - Agree to terms
# - Choose to redirect HTTP to HTTPS (recommended)
```

Certbot will automatically update your nginx config with the certificate paths and reload nginx.

### Verify auto-renewal

```bash
sudo certbot renew --dry-run   # should succeed with no errors
```

Certbot installs a systemd timer that auto-renews before expiry — no manual action needed.

---

## Step 15 — Host firewall (UFW)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

sudo ufw status
```

Expected output:
```
Status: active
To                         Action      From
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

> Qdrant (6333/6334) should NOT appear here — it's only accessible on localhost via Docker.

---

## Step 16 — Nginx TLS hardening (global config)

Edit `/etc/nginx/nginx.conf` and ensure the `http {}` block contains:

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
```

This disables TLS 1.0 and 1.1. After editing:

```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Step 17 — Verify everything is working

```bash
# Health check (should return {"status":"ok",...})
curl https://yourdomain.com/api/v1/health

# Check all services
sudo systemctl status ecc-backend ecc-frontend nginx docker

# Check Qdrant is only on localhost (should fail/timeout)
curl http://<SERVER_IP>:6333   # should NOT be reachable

# Check logs
sudo journalctl -u ecc-backend -n 50 --no-pager
sudo journalctl -u ecc-frontend -n 50 --no-pager
```

---

## Step 18 — Index your repositories

Once the stack is up, trigger the initial repo sync from the app UI or via API:

```bash
# Discover repos (no clone)
curl -X POST https://yourdomain.com/api/v1/repositories/discover \
  -H "Cookie: ecc_token=<your_jwt>"

# Sync (clone + index) — runs in background
curl -X POST https://yourdomain.com/api/v1/repositories/sync/background \
  -H "Content-Type: application/json" \
  -H "Cookie: ecc_token=<your_jwt>" \
  -d '{}'
```

Or use the **Sync** button in the dashboard UI.

---

## Updating the application

```bash
cd ~/engineeringCommandCenter

# Pull latest code
git pull origin main

# Rebuild frontend
cd frontend && npm install && npm run build && cd ..

# Restart services
sudo systemctl restart ecc-backend ecc-frontend
```

---

## Troubleshooting

| Symptom | Check |
|---|---|
| 500 on chat/RAG | `sudo journalctl -u ecc-backend -n 50` |
| Frontend not loading | `sudo journalctl -u ecc-frontend -n 50` |
| OAuth redirecting to localhost | Check `FRONTEND_URL` in `.env` — must be `https://yourdomain.com` |
| OAuth 500 after login | Check `API_INTERNAL_URL=http://localhost:8000` is set in the frontend service |
| Qdrant `search` AttributeError | qdrant-client ≥1.7 uses `query_points()` not `search()` — update the code |
| SSL cert expired | `sudo certbot renew` — check `systemctl status certbot.timer` |
| Next.js build fails (swc mismatch) | Run `npm install` on the server to get correct native binaries |
| `ModuleNotFoundError: structlog` | Activate venv and run `pip install -r requirements.txt` again |
| Port 3000 still reachable externally | Confirm `--hostname 127.0.0.1` flag in the frontend systemd service |

---

## Security checklist

- [x] UFW firewall: only 22, 80, 443 open
- [x] Qdrant bound to `127.0.0.1` only (`127.0.0.1:6333:6333` in docker-compose)
- [x] Next.js bound to `127.0.0.1` only (`--hostname 127.0.0.1`)
- [x] TLS 1.0/1.1 disabled in nginx
- [x] Security headers on all responses (HSTS, X-Frame-Options, etc.)
- [x] CVE-2025-55182 mitigated: Next.js upgraded to ≥16.2.0 + nginx blocks `next-action` header
- [x] All API endpoints require JWT authentication
- [x] Admin login rate-limited (5 attempts / 5 min per IP)
- [x] CORS restricted to explicit allowed origins
- [x] `backend/usage.db` excluded from git
- [ ] Rotate secrets if any were ever committed to git history
