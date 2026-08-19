#!/usr/bin/env bash
# EC2 user-data: runs as root at boot. Output is teed to console (visible via
# `aws ec2 get-console-output`) AND to a log file, so setup can be diagnosed
# without needing a direct network path to the instance.
exec > >(tee /var/log/colorhunt-userdata.log) 2>&1
trap 'echo "USERDATA_FAILED at line $LINENO"' ERR
set -xeuo pipefail

REPO_URL="https://github.com/Gapsick/findcolor.git"
APP_DIR=/opt/colorhunt

echo "=== STEP: dnf update ==="
dnf update -y

echo "=== STEP: pick python package ==="
if dnf list python3.12 >/dev/null 2>&1; then
    PYTHON_PKGS="python3.12 python3.12-pip"
    PYTHON_BIN=python3.12
else
    PYTHON_PKGS="python3 python3-pip"
    PYTHON_BIN=python3
fi
echo "using $PYTHON_BIN"

echo "=== STEP: install packages ==="
dnf install -y $PYTHON_PKGS git nginx

echo "=== STEP: clone repo ==="
mkdir -p "$APP_DIR"
git clone "$REPO_URL" "$APP_DIR"
chown -R ec2-user:ec2-user "$APP_DIR"

echo "=== STEP: venv + pip install ==="
cd "$APP_DIR"
sudo -u ec2-user $PYTHON_BIN -m venv venv
sudo -u ec2-user ./venv/bin/pip install --upgrade pip
sudo -u ec2-user ./venv/bin/pip install -r deploy/requirements-prod.txt

echo "=== STEP: env file ==="
cp deploy/colorhunt.env.example deploy/colorhunt.env
SECRET=$($PYTHON_BIN -c "import secrets; print(secrets.token_hex(32))")
sed -i "s/change-this-to-a-long-random-string/$SECRET/" deploy/colorhunt.env
chown ec2-user:ec2-user deploy/colorhunt.env
chmod 600 deploy/colorhunt.env

echo "=== STEP: systemd service ==="
cp deploy/colorhunt.service /etc/systemd/system/colorhunt.service
systemctl daemon-reload
systemctl enable --now colorhunt
sleep 3
systemctl status colorhunt --no-pager || true

echo "=== STEP: nginx ==="
cp deploy/nginx-colorhunt.conf /etc/nginx/conf.d/colorhunt.conf
rm -f /etc/nginx/conf.d/default.conf || true
systemctl enable --now nginx
systemctl reload nginx
systemctl status nginx --no-pager || true

echo "=== STEP: local smoke test ==="
sleep 2
curl -sS -o /dev/null -w "local curl status: %{http_code}\n" http://127.0.0.1/ || echo "local curl FAILED"

touch /opt/colorhunt/.setup-done
echo "USERDATA_COMPLETE_OK"
