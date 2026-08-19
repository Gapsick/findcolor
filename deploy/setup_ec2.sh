#!/usr/bin/env bash
# EC2(Ubuntu)에서 처음 한 번만 실행: 파이썬 환경 만들고 의존성 설치
# 사용법: 이 저장소를 git clone 한 뒤, colorhunt 폴더 안에서
#   bash deploy/setup_ec2.sh
set -e

cd "$(dirname "$0")/.."

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

echo ""
echo "설치 완료."
echo "1) .env 파일을 이 폴더에 직접 옮겨두세요 (git에는 없음, scp로 복사)."
echo "2) 바로 실행해보려면: .venv/bin/python app.py"
echo "3) 계속 떠있게 하려면 deploy/colorhunt.service 참고해서 systemd 서비스로 등록하세요."
