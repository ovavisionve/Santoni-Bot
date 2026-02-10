#!/usr/bin/env bash
# ============================================
# SantoniBot - VM Setup Script
# Target: Ubuntu 25.10 (192.168.1.26)
# Specs: 16GB RAM, 8 vCPU, 512GB SSD
# ============================================
set -euo pipefail

echo "=========================================="
echo "  SantoniBot - VM Setup"
echo "  Ubuntu 25.10 Server"
echo "=========================================="

# ---- System updates ----
echo "[1/7] Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ---- Essential packages ----
echo "[2/7] Installing essential packages..."
sudo apt-get install -y \
    curl \
    wget \
    git \
    htop \
    ufw \
    fail2ban \
    unzip \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common

# ---- Docker ----
echo "[3/7] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo "Docker installed. You may need to log out and back in for group changes."
else
    echo "Docker already installed: $(docker --version)"
fi

# ---- Docker Compose plugin ----
echo "[4/7] Verifying Docker Compose..."
if docker compose version &> /dev/null; then
    echo "Docker Compose available: $(docker compose version)"
else
    echo "Installing Docker Compose plugin..."
    sudo apt-get install -y docker-compose-plugin
fi

# ---- Firewall ----
echo "[5/7] Configuring firewall (UFW)..."
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # Backend API (dev only, remove in production)
sudo ufw allow 3000/tcp  # Frontend dev (remove in production)
sudo ufw --force enable
echo "Firewall configured."

# ---- Fail2Ban ----
echo "[6/7] Configuring Fail2Ban..."
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# ---- Project directory ----
echo "[7/7] Creating project directory..."
PROJECT_DIR="/opt/santonibot"
sudo mkdir -p "$PROJECT_DIR"
sudo chown "$USER":"$USER" "$PROJECT_DIR"

echo ""
echo "=========================================="
echo "  VM Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Clone the repo:  cd /opt/santonibot && git clone <repo-url> ."
echo "  2. Copy .env:       cp .env.example .env && nano .env"
echo "  3. Deploy:          bash scripts/deploy.sh"
echo ""
echo "VM Info:"
echo "  Internal IP: 192.168.1.26"
echo "  Public IP:   201.249.55.198"
echo "  Specs:       16GB RAM | 8 vCPU | 512GB SSD"
echo ""
