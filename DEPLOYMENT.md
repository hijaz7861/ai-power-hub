# Deployment with Docker Compose

This repository includes a self-hosted container stack for the Next.js frontend, FastAPI backend, PostgreSQL 16 and password-protected Redis. It is a deployment starting point, not proof that the service has been deployed or production-audited.

## Requirements

- A Linux host with Docker Engine and the Docker Compose v2 plugin.
- A domain name and a TLS reverse proxy (Caddy, Nginx or a managed HTTPS ingress).
- Persistent disk for PostgreSQL and Redis.
- Server-side provider/payment credentials only when enabling those capabilities.

The Compose stack binds the web frontend to loopback by default (127.0.0.1:3000). Put a TLS reverse proxy in front of it. Do not expose PostgreSQL, Redis or the FastAPI port directly to the public internet.

## Configure secrets

    cp .env.example .env
    openssl rand -hex 32

Generate separate random values for SECRET_KEY, POSTGRES_PASSWORD and REDIS_PASSWORD. Use URL-safe hexadecimal passwords for PostgreSQL and Redis because they are embedded in the internal connection URLs. Do not reuse the same secret.

Set at minimum:

- APP_ENV=production
- DEBUG=false
- SECRET_KEY to a unique random value of at least 32 characters
- POSTGRES_PASSWORD and REDIS_PASSWORD to separate random hex values
- PUBLIC_APP_URL=https://your-real-domain
- APP_ORIGIN=https://your-real-domain (exact origin, no path)
- WEB_BIND_ADDRESS=127.0.0.1

The Compose network assigns the frontend a fixed internal address and configures that exact address as the backend's trusted proxy. The frontend forwards the ingress X-Forwarded-For header to the API; the backend ignores it unless the direct TCP peer is in TRUSTED_PROXY_IPS. Configure the public TLS reverse proxy to overwrite X-Forwarded-For with the actual connecting client IP, never append an untrusted client-supplied value. The default Compose subnet is 172.30.0.0/24; if it conflicts with an existing network, change the subnet and all four static service addresses plus TRUSTED_PROXY_IPS together.

For deployments outside this Compose stack, set TRUSTED_PROXY_IPS to the exact proxy address/CIDR. Do not trust broad public or shared networks.
- WEB_PORT=3000

Keep DATABASE_URL and REDIS_URL in the environment managed by Compose; the backend service overrides them with internal service addresses. The frontend API_BASE_URL is also set to the internal backend service. The .env file must never be committed or copied into an image.

Optional OPENAI_API_KEY, MISTRAL_API_KEY, Safepay credentials and webhook secret must be added only to the server's secret environment. Do not paste keys into chat, source control, issue comments or browser code. Chat models remain unavailable until the matching supplier token-rate pair is contract-verified and enabled by an administrator.

## Start the stack

    docker compose config --quiet
    docker compose up -d --build
    docker compose ps
    docker compose logs -f backend frontend

The backend container runs alembic upgrade head before starting Uvicorn. The backend readiness probe checks PostgreSQL and Redis. The frontend is exposed only on the configured host bind address; configure the reverse proxy to forward HTTPS traffic to 127.0.0.1:3000.

Check liveness and readiness from the host:

    curl -fsS http://127.0.0.1:3000/health

The frontend rewrites /health to the API liveness endpoint. For direct API readiness checks, run the request from inside the backend container:

    docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/ready').read().decode())"

## Backup and restore

Before upgrades, back up PostgreSQL and verify the backup can be restored to a separate database. Example logical backup:

    docker compose exec -T db pg_dump -U aiph -d aiph -Fc > ai-power-hub-backup.dump

A restore drill must be performed against a separate disposable database before any production launch. Protect backup files as sensitive data; they may contain customer account, billing and conversation records. Redis stores rate-limit counters and can be rebuilt; PostgreSQL contains the authoritative financial and application records.

## Important launch gates

- Configure automated encrypted backups, off-host retention and restore drills.
- Configure TLS, firewall, SSH hardening, OS patching, monitoring and alerting.
- Use a secret manager rather than a broadly readable .env file where available.
- Review Redis/PostgreSQL access, network isolation and connection limits.
- Complete live Safepay sandbox verification, provider usage reconciliation, independent security review and browser end-to-end tests.
- Confirm supplier agreements and resale rights before enabling any paid provider model.
- Review Pakistan tax, consumer, privacy, data-retention and refund obligations with qualified professionals.

The included Compose configuration is not a substitute for operational hardening, a privacy policy, payment-provider onboarding or an independent security review.
