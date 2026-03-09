#!/usr/bin/env bash
# ============================================
# SantoniBot - Deployment Script
# Deploys the full stack using Docker Compose
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "  SantoniBot - Deploy"
echo "=========================================="

cd "$PROJECT_DIR"

# ---- Pre-flight checks ----
echo "[1/6] Pre-flight checks..."

if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Run setup-vm.sh first."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "ERROR: Docker Compose is not available."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found."
    echo "  Copy .env.example to .env and fill in the values:"
    echo "  cp .env.example .env && nano .env"
    exit 1
fi

# ---- Pull latest code ----
echo "[2/6] Pulling latest code..."
if [ -d ".git" ]; then
    git pull origin main 2>/dev/null || echo "Git pull skipped (not on main or no remote)."
fi

# ---- Detect environment ----
COMPOSE_FILES="-f docker-compose.yml"
if [ "${APP_ENV:-}" = "production" ] || grep -q "APP_ENV=production" .env 2>/dev/null; then
    echo "  Detected: PRODUCTION environment"
    COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"
else
    echo "  Detected: DEVELOPMENT environment"
fi

# ---- Validate critical env vars ----
echo "[3/8] Validating environment..."
MISSING_VARS=""
for VAR in SECRET_KEY POSTGRES_PASSWORD; do
    if ! grep -q "^${VAR}=" .env 2>/dev/null || grep -q "^${VAR}=change" .env 2>/dev/null; then
        MISSING_VARS="${MISSING_VARS} ${VAR}"
    fi
done
if [ -n "$MISSING_VARS" ]; then
    echo "WARNING: Estas variables necesitan configurarse en .env:${MISSING_VARS}"
fi

# Check AI provider is configured
AI_PROVIDER=$(grep "^AI_PROVIDER=" .env 2>/dev/null | cut -d= -f2 || echo "groq")
case "$AI_PROVIDER" in
    openrouter)
        if ! grep -q "^OPENROUTER_API_KEY=." .env 2>/dev/null || grep -q "^OPENROUTER_API_KEY=your-" .env 2>/dev/null; then
            echo "WARNING: OPENROUTER_API_KEY no configurada para AI_PROVIDER=openrouter"
        fi
        ;;
    groq)
        if ! grep -q "^GROQ_API_KEY=." .env 2>/dev/null; then
            echo "WARNING: GROQ_API_KEY no configurada para AI_PROVIDER=groq"
        fi
        ;;
esac

# ---- Build containers ----
echo "[4/8] Building containers..."
docker compose $COMPOSE_FILES build --no-cache

# ---- Stop old containers ----
echo "[5/8] Stopping existing containers..."
docker compose $COMPOSE_FILES down --remove-orphans 2>/dev/null || true

# ---- Start services ----
echo "[6/8] Starting services..."
docker compose $COMPOSE_FILES up -d

# ---- Run database migrations ----
echo "[7/8] Running database migrations..."
sleep 5  # Wait for DB to be ready
docker compose $COMPOSE_FILES exec -T backend alembic upgrade head 2>&1 || {
    echo "WARNING: Alembic migrations failed. Check backend logs."
}

# ---- Health check ----
echo "[8/8] Waiting for services to start..."
sleep 5

echo ""
echo "Service status:"
docker compose $COMPOSE_FILES ps

echo ""
echo "Checking API health..."
for i in {1..6}; do
    if curl -sf http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "API is healthy!"
        curl -s http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || true
        break
    fi
    if [ "$i" -eq 6 ]; then
        echo "WARNING: API health check failed after 30s. Check logs:"
        echo "  docker compose logs backend"
    fi
    echo "  Waiting... (attempt $i/6)"
    sleep 5
done

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
# Read DOMAIN from .env for display
DOMAIN=$(grep "^DOMAIN=" .env 2>/dev/null | cut -d= -f2 || echo "localhost")
IS_PROD=$(grep -q "APP_ENV=production" .env 2>/dev/null && echo "yes" || echo "no")

echo ""
echo "Access points:"
echo "  Frontend:  http://${DOMAIN}"
echo "  API:       http://${DOMAIN}:8000"
if [ "$IS_PROD" = "no" ]; then
    echo "  API Docs:  http://${DOMAIN}:8000/api/docs  (solo en desarrollo)"
fi
echo ""
echo "Default admin login:"
echo "  User: admin"
echo "  Pass: SantoniAdmin2026!"
echo ""
echo "Useful commands:"
echo "  Logs:      docker compose logs -f"
echo "  Restart:   docker compose restart"
echo "  Stop:      docker compose down"
echo "  DB shell:  docker compose exec db psql -U santonibot"
echo ""
