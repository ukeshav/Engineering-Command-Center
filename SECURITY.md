# Security Policy

## Supported Versions

Engineering Command Center is an open-source project maintained on a best-effort basis. Security fixes are applied to the latest version on `main` only.

| Version | Supported |
|---|---|
| Latest (`main`) | Yes |
| Older tags | No |

We recommend always running from the latest `main` or the most recent tagged release.

---

## Reporting a Vulnerability

We take security issues seriously. If you have found a vulnerability, please follow responsible disclosure and **do not open a public GitHub issue** until we have had a chance to assess and address the problem.

### How to report

Open a GitHub issue in this repository and apply the **`security`** label. In the issue body, include:

1. A description of the vulnerability and its potential impact.
2. The component or file(s) affected (e.g., backend auth middleware, nginx configuration).
3. Steps to reproduce or a proof-of-concept (where safe to share).
4. Your suggested fix, if you have one.

We will acknowledge the report within **72 hours** and aim to provide an initial assessment within **7 days**.

> If you are uncomfortable using a GitHub issue — for example, because the vulnerability involves credentials or sensitive data that you do not want posted publicly even briefly — please contact the maintainer directly. You can find contact information in the repository's GitHub profile.

### What to expect

- We will confirm receipt and keep you informed of our progress.
- We will credit you in the fix commit and release notes unless you prefer to remain anonymous.
- We will coordinate a disclosure timeline with you. For high-severity issues we aim to ship a fix within 14 days.
- This is a small open-source project with no bug bounty programme. We cannot offer financial rewards, but we are genuinely grateful for responsible disclosures.

---

## Known Security Considerations

The following items are documented explicitly so operators are aware of them when deploying.

### Authentication

- All API endpoints require a JWT issued after Google OAuth login.
- Login is restricted to a single email domain via `ALLOWED_EMAIL_DOMAIN`. Ensure this is set correctly in production.
- JWT secrets are derived from `SECRET_KEY`. Generate this with `openssl rand -hex 32` and never commit it to source control.
- Admin login is rate-limited (5 attempts per 5 minutes per IP) to mitigate brute-force attacks.

### Network exposure

- Qdrant is bound to `127.0.0.1` only in `docker-compose.yml`. Do not expose ports 6333 or 6334 to the public internet.
- Both the backend (port 8000) and frontend (port 3000) should be bound to `127.0.0.1` in production, with nginx as the only public-facing process.
- The UFW firewall configuration in [DEPLOY.md](DEPLOY.md) opens only ports 22, 80, and 443.

### TLS

- The deployment guide configures nginx to use TLS 1.2 and 1.3 only. TLS 1.0 and 1.1 are disabled.
- Let's Encrypt certificates auto-renew via a systemd timer.

### CVE-2025-55182 (Next.js Server Action RCE)

- The nginx configuration in [DEPLOY.md](DEPLOY.md) blocks requests containing a `next-action` header at the proxy level.
- Ensure Next.js is kept at version 16.2.0 or later, which contains the upstream fix.

### Secrets management

- Never commit `.env` files. `.env` is in `.gitignore`.
- `backend/usage.db` is excluded from git.
- Rotate all secrets immediately if any were ever committed to the repository's git history.

### CORS

- The `ALLOWED_ORIGINS` environment variable restricts cross-origin requests. In production this should be set to your exact domain (e.g., `["https://yourdomain.com"]`).

---

## Security Checklist for Operators

Before going to production, verify:

- [ ] UFW firewall is active: only ports 22, 80, and 443 open
- [ ] Qdrant is not reachable from the public internet (`curl http://<SERVER_IP>:6333` should time out)
- [ ] `ALLOWED_EMAIL_DOMAIN` is set to your organisation's domain
- [ ] `SECRET_KEY` is a strong random value (`openssl rand -hex 32`) and not committed to git
- [ ] `ALLOWED_ORIGINS` is set to `["https://yourdomain.com"]`
- [ ] TLS 1.0/1.1 are disabled in nginx
- [ ] Security headers are present: HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- [ ] Next.js is at version 16.2.0 or later (CVE-2025-55182)
- [ ] No secrets appear in the git history (`git log --all --full-history -- .env` returns nothing)
