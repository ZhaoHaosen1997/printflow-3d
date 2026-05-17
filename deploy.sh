#!/bin/bash
set -e

SRC="/mnt/c/mycode/printflow-3d"
DST="/home/zhaohaosen/applications/printflow-3d"
NGINX_CONF="/etc/nginx/sites-available/printflow"
SERVICE_FILE="/etc/systemd/system/printflow.service"

echo "=== PrintFlow-3D Deploy ==="
echo ""

# Check source exists
if [ ! -d "$SRC" ]; then
    echo "ERROR: Windows source not found at $SRC"
    echo "Is the Windows drive mounted in WSL?"
    exit 1
fi

# Create destination if needed
mkdir -p "$DST"

# Step 1: Rsync from Windows to WSL
echo "[1/5] Syncing code from Windows..."
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

# Step 2: Check backend changes + restart
echo "[2/5] Checking backend changes..."
BACKEND_HASH_OLD=$(find "$DST/backend" -name '*.py' -exec md5sum {} \; 2>/dev/null | sort -k2 | md5sum | cut -d' ' -f1 2>/dev/null || echo "none")
BACKEND_HASH_NEW=$(find "$DST/backend" -name '*.py' -exec md5sum {} \; 2>/dev/null | sort -k2 | md5sum | cut -d' ' -f1)

BACKEND_STATUS_FILE="$DST/.backend_hash"

if [ ! -f "$BACKEND_STATUS_FILE" ] || [ "$(cat "$BACKEND_STATUS_FILE")" != "$BACKEND_HASH_NEW" ]; then
    echo "  Backend changed, installing deps & restarting..."
    cd "$DST"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    "$DST/venv/bin/pip" install -r requirements.txt -q
    sudo systemctl restart printflow
    echo "$BACKEND_HASH_NEW" > "$BACKEND_STATUS_FILE"
    echo "  Backend: restarted"
else
    echo "  Backend: no changes"
fi

# Step 3: Check frontend changes + rebuild
echo "[3/5] Checking frontend changes..."
FRONTEND_HASH_OLD=$(cat "$DST/.frontend_hash" 2>/dev/null || echo "none")
FRONTEND_HASH_NEW=$(find "$DST/frontend/src" "$DST/frontend/package.json" "$DST/frontend/index.html" "$DST/frontend/vite.config.js" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | md5sum | cut -d' ' -f1)

if [ "$FRONTEND_HASH_OLD" != "$FRONTEND_HASH_NEW" ] || [ ! -d "$DST/frontend/dist" ]; then
    echo "  Frontend changed, building..."
    cd "$DST/frontend"
    npm install --silent
    npm run build
    # Ensure www-data can read dist
    for d in /home /home/zhaohaosen /home/zhaohaosen/applications "$DST" "$DST/frontend"; do
        [ -d "$d" ] && sudo chmod o+x "$d" 2>/dev/null || true
    done
    chmod -R o+rX "$DST/frontend/dist"
    echo "$FRONTEND_HASH_NEW" > "$DST/.frontend_hash"
    echo "  Frontend: built"
else
    echo "  Frontend: no changes"
fi

# Step 4: Check nginx config changes
echo "[4/5] Checking nginx config..."
if ! diff -q "$DST/nginx.conf" "$NGINX_CONF" 2>/dev/null; then
    echo "  Nginx config changed, updating..."
    sudo cp "$DST/nginx.conf" "$NGINX_CONF"
    sudo ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/printflow
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    echo "  Nginx: reloaded"
else
    echo "  Nginx: no changes"
fi

# Step 5: Check systemd service changes
echo "[5/5] Checking systemd service..."
if ! diff -q "$DST/printflow.service" "$SERVICE_FILE" 2>/dev/null; then
    echo "  Service file changed, updating..."
    sudo cp "$DST/printflow.service" "$SERVICE_FILE"
    sudo systemctl daemon-reload
    sudo systemctl restart printflow
    echo "  Systemd: reloaded + restarted"
else
    echo "  Systemd: no changes"
fi

echo ""
echo "=== Deploy complete ==="
echo "  URL: http://localhost:18848"
echo "  Status: sudo systemctl status printflow nginx"
