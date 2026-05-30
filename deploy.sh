#!/bin/bash
set -e

SRC="/mnt/c/mycode/printflow-3d"
PI="zhaohaosen@192.163.20.150"
DST="/home/zhaohaosen/applications/printflow-3d"
VENV="/home/zhaohaosen/.venvs/printflow"
SERVICE_FILE="/etc/systemd/system/printflow.service"

echo "=== PrintFlow-3D Deploy → Pi ==="
echo ""

if [ ! -d "$SRC" ]; then
    echo "ERROR: Windows source not found at $SRC"
    exit 1
fi

# Step 1: Rsync to Pi
echo "[1/4] Syncing code to Pi..."
rsync -avz --delete \
    --exclude '.venv/' --exclude 'venv/' --exclude 'node_modules/' \
    --exclude '__pycache__/' --exclude '.git/' \
    --exclude 'data/images/' --exclude 'data/logs/' --exclude 'data/app.db' \
    --exclude '.claude/' --exclude '.workbuddy/' \
    --exclude 'old_data/' --exclude 'old_version/' --exclude 'scripts/' \
    -e ssh "$SRC/" "$PI:$DST/"

# Step 2: Backend — check changes, install deps, restart
echo "[2/4] Checking backend..."
BACKEND_HASH=$(find "$SRC/backend" -name '*.py' -exec md5sum {} \; 2>/dev/null | sort -k2 | md5sum | cut -d' ' -f1)

ssh "$PI" bash -s << BACKEND
set -e
OLD=\$(cat "$DST/.backend_hash" 2>/dev/null || echo 'none')
if [ "\$OLD" != "$BACKEND_HASH" ]; then
    echo '  Backend changed, installing deps...'
    $VENV/bin/pip install -r $DST/requirements.txt -q
    sudo systemctl restart printflow
    echo "$BACKEND_HASH" > "$DST/.backend_hash"
    echo '  Backend: restarted'
else
    echo '  Backend: no changes'
fi
BACKEND

# Step 3: Frontend — check changes, npm build
echo "[3/4] Checking frontend..."
FRONTEND_HASH=$(find "$SRC/frontend/src" "$SRC/frontend/package.json" "$SRC/frontend/index.html" "$SRC/frontend/vite.config.js" -type f 2>/dev/null | sort | xargs md5sum 2>/dev/null | md5sum | cut -d' ' -f1)

ssh "$PI" bash -s << FRONTEND
set -e
OLD=\$(cat "$DST/.frontend_hash" 2>/dev/null || echo 'none')
if [ "\$OLD" != "$FRONTEND_HASH" ] || [ ! -d "$DST/frontend/dist" ]; then
    echo '  Frontend changed, building...'
    cd $DST/frontend
    npm install --silent
    npm run build
    echo "$FRONTEND_HASH" > "$DST/.frontend_hash"
    echo '  Frontend: built'
    sudo systemctl restart printflow
else
    echo '  Frontend: no changes'
fi
FRONTEND

# Step 4: Check systemd service file
echo "[4/4] Checking systemd service..."
ssh "$PI" bash -s << SERVICE
set -e
if ! diff -q $DST/printflow.service $SERVICE_FILE 2>/dev/null; then
    echo '  Service file changed, updating...'
    sudo cp $DST/printflow.service $SERVICE_FILE
    sudo systemctl daemon-reload
    sudo systemctl restart printflow
    echo '  Systemd: reloaded'
else
    echo '  Systemd: no changes'
fi
SERVICE

echo ""
echo "=== Deploy complete ==="
echo "  URL: http://192.163.20.150:8848"
echo "  Status: ssh $PI 'sudo systemctl status printflow'"
