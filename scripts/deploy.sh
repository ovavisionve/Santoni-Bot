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

# ---- Build containers ----
echo "[3/6] Building containers..."
docker compose build --no-cache

# ---- Stop old containers ----
echo "[4/6] Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

# ---- Start services ----
echo "[5/6] Starting services..."
docker compose up -d

# ---- Health check ----
echo "[6/6] Waiting for services to start..."
sleep 10

echo ""
echo "Service status:"
docker compose ps

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
echo ""
echo "Access points:"
echo "  Frontend:  http://192.168.1.26"
echo "  API:       http://192.168.1.26:8000"
echo "  API Docs:  http://192.168.1.26:8000/docs"
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
