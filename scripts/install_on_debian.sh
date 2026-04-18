#!/usr/bin/env bash
set -euo pipefail
APP_DIR="/opt/precificador"
echo "[1/6] Dependências..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip unzip
echo "[2/6] Criando pasta..."
mkdir -p "$APP_DIR"
echo "[3/6] Copiando projeto..."
cp -r ./* "$APP_DIR/"
echo "[4/6] Venv + requirements..."
cd "$APP_DIR"
python3 -m venv .venv
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r requirements.txt
echo "[5/6] systemd..."
cp "$APP_DIR/precificador.service" /etc/systemd/system/precificador.service
systemctl daemon-reload
systemctl enable precificador
echo "[6/6] Start..."
systemctl restart precificador
echo "✅ OK"
echo "Acesse: http://$(hostname -I | awk '{print $1}'):5000"
echo "Logs: journalctl -u precificador -f"
