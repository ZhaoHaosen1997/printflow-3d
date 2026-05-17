#!/bin/bash
set -e

echo "=== PrintFlow-3D WSL Stop ==="

echo "[1/2] Stopping backend service..."
sudo systemctl stop printflow
echo "  Backend: stopped"

echo "[2/2] Stopping nginx..."
sudo systemctl stop nginx
echo "  Nginx: stopped"

echo ""
echo "All services stopped."
