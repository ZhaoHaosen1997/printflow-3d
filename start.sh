#!/bin/bash
set -e

echo "=== PrintFlow-3D WSL Start ==="

echo "[1/2] Starting backend service..."
sudo systemctl start printflow
echo "  Backend: OK (127.0.0.1:8848)"

echo "[2/2] Starting nginx..."
sudo systemctl start nginx
echo "  Nginx: OK (:18848)"

echo ""
echo "=== PrintFlow-3D is running ==="
echo "  URL: http://localhost:18848"
echo "  API docs: http://localhost:18848/api/docs"
echo ""
echo "  Status:  sudo systemctl status printflow nginx"
echo "  Logs:    sudo journalctl -u printflow -f"
echo "  Stop:    ./stop.sh"
