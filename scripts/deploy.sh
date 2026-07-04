#!/usr/bin/env bash
set -euo pipefail

# Cricket Rules AI — Linux/VPS Deployment Script
# Usage: ./scripts/deploy.sh [--domain cricketrules.ai] [--email admin@...] [--skip-ssl] [--ingest]

DOMAIN="${DOMAIN:-cricketrules.ai}"
EMAIL="${EMAIL:-admin@cricketrules.ai}"
SKIP_SSL=false
INGEST=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --email) EMAIL="$2"; shift 2 ;;
    --skip-ssl) SKIP_SSL=true; shift ;;
    --ingest) INGEST=true; shift ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== Cricket Rules AI Deployment ==="
echo "Domain: $DOMAIN"

# 1. Check Docker
if ! command -v docker &>/dev/null; then
  echo "[SETUP] Installing Docker..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo "[OK] Docker installed. You may need to re-login for group changes."
fi
echo "[OK] Docker: $(docker --version)"

# 2. Check Docker Compose
if ! docker compose version &>/dev/null; then
  echo "[SETUP] Installing Docker Compose..."
  sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi
echo "[OK] Docker Compose: $(docker compose version)"

# 3. Create .env from template if not exists
if [[ ! -f .env ]]; then
  if [[ -f deployment.env.example ]]; then
    cp deployment.env.example .env
    # Generate random secrets
    ADMIN_KEY=$(openssl rand -hex 32)
    JWT_KEY=$(openssl rand -hex 32)
    sed -i "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=${GEMINI_API_KEY:-your_key_here}/" .env
    sed -i "s/ADMIN_API_KEY=.*/ADMIN_API_KEY=$ADMIN_KEY/" .env
    sed -i "s/JWT_SECRET=.*/JWT_SECRET=$JWT_KEY/" .env
    sed -i "s/DOMAIN_NAME=.*/DOMAIN_NAME=$DOMAIN/" .env
    sed -i "s/ADMIN_EMAIL=.*/ADMIN_EMAIL=$EMAIL/" .env
    echo "[OK] Created .env from template"
  fi
else
  echo "[OK] .env already exists"
fi

# 4. Replace DOMAIN_NAME placeholder in nginx config
if [[ -f nginx/sites/cricket-rules.conf ]]; then
  sed -i "s/DOMAIN_NAME/$DOMAIN/g" nginx/sites/cricket-rules.conf
  echo "[OK] Updated nginx config with domain: $DOMAIN"
fi

# 5. Pull & Build
echo "[BUILD] Pulling base images and building app..."
docker compose pull qdrant redis postgres nginx certbot
docker compose build app
echo "[OK] Build complete"

# 6. Start data services
echo "[START] Starting Qdrant, Redis, Postgres..."
docker compose up -d qdrant redis postgres
echo "[WAIT] Waiting for services to be healthy..."
sleep 15

# 7. Start app
docker compose up -d app
sleep 15

# 8. Ingest PDFs (optional)
if [[ "$INGEST" == true ]]; then
  echo "[INGEST] Running PDF ingestion..."
  docker compose run --rm ingest
  echo "[OK] Ingestion complete"
fi

# 9. Start nginx
docker compose up -d nginx
echo "[OK] nginx started"

# 10. SSL via Certbot
if [[ "$SKIP_SSL" == false ]]; then
  echo "[SSL] Requesting Let's Encrypt certificate..."
  docker compose run --rm certbot certonly --webroot \
    -w /var/www/certbot \
    -d "$DOMAIN" \
    --email "$EMAIL" \
    --agree-tos \
    --non-interactive
  echo "[OK] SSL certificate obtained"
  docker compose restart nginx
fi

echo ""
echo "=== Deployment Complete ==="
echo "API:    https://$DOMAIN/api/v1/health"
echo "Widget: https://$DOMAIN/widget/embed.js"
echo "Admin:  https://$DOMAIN/admin/"
echo ""
echo "Useful commands:"
echo "  View logs:       docker compose logs -f app"
echo "  Ingest PDFs:     docker compose run --rm ingest"
echo "  Stop services:   docker compose down"
echo "  Renew SSL:       docker compose run --rm certbot renew"
