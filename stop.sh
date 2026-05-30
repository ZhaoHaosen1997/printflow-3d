#!/bin/bash
set -e
PI="zhaohaosen@192.163.20.150"

echo "=== PrintFlow-3D Stop (Pi) ==="

echo "[1/2] Stopping backend..."
ssh "$PI" "sudo systemctl stop printflow"
echo "  Backend: stopped"

echo "[2/2] Stopping nginx..."
ssh "$PI" "sudo systemctl stop nginx"
echo "  Nginx: stopped"

echo ""
echo "All services stopped."
