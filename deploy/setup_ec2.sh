#!/usr/bin/env bash
# Amazon Linux 2023, EC2에서 실행. Color Hunt 앱을 클론 -> venv -> gunicorn(systemd) -> nginx로 구성한다.
set -euo pipefail

REPO_URL="${1:?사용법: setup_ec2.sh <git-repo-url>}"
APP_DIR=/opt/colorhunt

sudo dnf update -y

if sudo dnf list python3.12 >/dev/null 2>&1; then
    PYTHON_PKGS="python3.12 python3.12-pip"
    PYTHON_BIN=python3.12
else
    PYTHON_PKGS="python3 python3-pip"
    PYTHON_BIN=python3
fi
sudo dnf install -y $PYTHON_PKGS git nginx

sudo mkdir -p "$APP_DIR"
sudo chown "$USER":"$USER" "$APP_DIR"

if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull
else
    git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"
$PYTHON_BIN -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r deploy/requirements-prod.txt

if [ ! -f deploy/colorhunt.env ]; then
    cp deploy/colorhunt.env.example deploy/colorhunt.env
    SECRET=$($PYTHON_BIN -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/change-this-to-a-long-random-string/$SECRET/" deploy/colorhunt.env
    echo "deploy/colorhunt.env 생성됨. COLORHUNT_ADMIN_PIN을 원하는 값으로 바꾸세요."
fi
chmod 600 deploy/colorhunt.env

sudo cp deploy/colorhunt.service /etc/systemd/system/colorhunt.service
sudo systemctl daemon-reload
sudo systemctl enable --now colorhunt

sudo cp deploy/nginx-colorhunt.conf /etc/nginx/conf.d/colorhunt.conf
sudo rm -f /etc/nginx/conf.d/default.conf 2>/dev/null || true
sudo systemctl enable --now nginx
sudo systemctl reload nginx

echo "완료. http://<EC2-퍼블릭IP>/ 로 접속 확인하세요."
