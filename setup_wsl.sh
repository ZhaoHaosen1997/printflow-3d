#!/bin/bash
set -e

SRC="/mnt/c/mycode/printflow-3d"
DST="/home/zhaohaosen/applications/printflow-3d"
NGINX_CONF="/etc/nginx/sites-available/printflow"
SERVICE_FILE="/etc/systemd/system/printflow.service"

echo "============================================"
echo "  PrintFlow-3D WSL Setup"
echo "============================================"
echo ""

# ---- Phase 1: Pre-flight checks ----
echo "[Phase 1/8] Pre-flight checks..."

if [ ! -f /proc/sys/fs/binfmt_misc/WSLInterop ] && [ ! -d /mnt/c ]; then
    echo "WARNING: Does not appear to be WSL environment. Continue? (y/n)"
    read -r answer
    [ "$answer" != "y" ] && exit 0
fi

if [ ! -d "$SRC" ]; then
    echo "ERROR: Windows source not found at $SRC"
    exit 1
fi

echo "  Source: $SRC"
echo "  Target: $DST"
echo ""

# ---- Phase 2: System dependencies ----
echo "[Phase 2/8] Installing system dependencies..."
sudo apt update -qq
sudo apt install -y -qq python3 python3-venv python3-pip nginx rsync
echo "  Done"

# Node.js: check before installing (NodeSource package conflicts with Debian npm)
if ! command -v node &>/dev/null; then
    echo "  Installing Node.js..."
    sudo apt install -y -qq nodejs
else
    echo "  Node.js $(node -v) already installed"
fi
if ! command -v npm &>/dev/null; then
    echo "  Installing npm..."
    sudo apt install -y -qq npm 2>/dev/null || {
        echo "  WARNING: npm install via apt failed. Trying NodeSource..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y -qq nodejs
    }
else
    echo "  npm $(npm -v) already installed"
fi
echo ""

# ---- Phase 3: Project directory ----
echo "[Phase 3/8] Setting up project directory..."
mkdir -p "$DST"
mkdir -p "$DST/data/images" "$DST/data/logs"
sudo chown -R "$USER:$USER" "$DST"
echo "  Done"
echo ""

# ---- Phase 4: Initial code sync ----
echo "[Phase 4/8] Initial code sync from Windows..."
rsync -av --delete \
    --exclude '.venv/' \
    --exclude 'venv/' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    --exclude '.git/' \
    --exclude 'data/images/' \
    --exclude 'data/logs/' \
    --exclude 'data/app.db' \
    --exclude '.claude/' \
    --exclude '.workbuddy/' \
    --exclude 'old_data/' \
    --exclude 'old_version/' \
    --exclude 'scripts/' \
    "$SRC/" "$DST/"
echo "  Done"
echo ""

# ---- Phase 5: Python venv ----
echo "[Phase 5/8] Setting up Python virtual environment..."
cd "$DST"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
"$DST/venv/bin/pip" install -r requirements.txt -q
echo "  Done"
echo ""

# ---- Phase 6: Frontend build ----
echo "[Phase 6/8] Building frontend..."
cd "$DST/frontend"
npm install --silent
npm run build
# Allow nginx (www-data) to traverse the home directory chain
for d in /home /home/zhaohaosen /home/zhaohaosen/applications "$DST" "$DST/frontend"; do
    [ -d "$d" ] && sudo chmod o+x "$d" 2>/dev/null || true
done
chmod -R o+rX "$DST/frontend/dist"
echo "  Done"
echo ""

# ---- Phase 7: Nginx setup ----
echo "[Phase 7/8] Configuring nginx..."
sudo cp "$DST/nginx.conf" "$NGINX_CONF"
sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/printflow
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
echo "  Done"
echo ""

# ---- Phase 8: systemd service ----
echo "[Phase 8/8] Registering systemd service..."
sudo cp "$DST/printflow.service" "$SERVICE_FILE"
sudo systemctl daemon-reload
sudo systemctl enable printflow
echo "  Done"
echo ""

# ---- WSL systemd enablement ----
echo "----------------------------------------"
echo "Enabling systemd in WSL..."
WSL_CONF="/etc/wsl.conf"
if ! grep -q "systemd=true" "$WSL_CONF" 2>/dev/null; then
    echo "[boot]" | sudo tee -a "$WSL_CONF" > /dev/null 2>&1 || true
    echo "systemd=true" | sudo tee -a "$WSL_CONF" > /dev/null 2>&1 || true
    echo "  /etc/wsl.conf updated"
else
    echo "  systemd already enabled"
fi
echo ""

# ---- Done ----
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  IMPORTANT: Run this in Windows PowerShell:"
echo "    wsl --shutdown"
echo "  Then reopen WSL Debian."
echo ""
echo "  After restart, check services:"
echo "    ./start.sh"
echo "    http://localhost:18848"
echo "============================================"
