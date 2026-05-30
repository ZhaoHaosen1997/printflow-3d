#!/bin/bash
set -e
PI="zhaohaosen@192.163.20.150"

echo "=== PrintFlow-3D Start (Pi) ==="

echo "[1/2] Starting backend..."
ssh "$PI" "sudo systemctl start printflow"
echo "  Backend: OK (127.0.0.1:8848)"

echo "[2/2] Starting nginx..."
ssh "$PI" "sudo systemctl start nginx"
echo "  Nginx: OK (:18848)"

echo ""
echo "=== PrintFlow-3D is running ==="
echo "  URL: http://192.163.20.150:18848"
echo "  API docs: http://192.163.20.150:18848/api/docs"
