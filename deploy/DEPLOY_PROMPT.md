# Color Hunt — AWS 배포 실행 프롬프트 (자기완결형)

이 파일 하나만 있으면 새 세션(다른 사람, 다른 Claude 세션 포함)이 별도 탐색 없이
Color Hunt를 AWS(EC2 + CloudFront)에 배포할 수 있다. 최상단 "실행 프롬프트"를
그대로 복사해서 에이전트에게 주면 된다.

---

## 실행 프롬프트 (복사해서 그대로 사용)

```
너는 Color Hunt(Flask 색상 찾기 게임) 앱을 AWS에 배포하는 작업을 맡았다.
저장소: https://github.com/Gapsick/findcolor (기본 브랜치: main)
전체 배경과 절차는 저장소의 deploy/DEPLOY_PROMPT.md 에 이미 정리되어 있으니
그 문서의 "0단계 ~ 4단계"를 순서대로 따라가라. 특히:

1. 0단계(로컬/깃 정리)를 절대 건너뛰지 마라 — deploy/ 와 Dockerfile이
   아직 main에 반영 안 됐을 수 있고, main이 로컬보다 앞서 있을 수 있다(dev 페이지 커밋 등).
   git push 전에는 항상 나(사용자)에게 먼저 확인받아라.
2. AWS 계정은 학교 공유 계정(045861054142, ap-northeast-1)이다.
   반드시 이름에 colorhunt- 접두어가 붙은 리소스만 건드리고, 다른 조 리소스는 손대지 마라.
3. 이 로컬 네트워크에서는 EC2로의 직접 SSH(22)/HTTP(80) 아웃바운드가 막혀 있다.
   AWS 콘솔의 EC2 → Connect → EC2 Instance Connect(브라우저 터미널) 또는
   AWS CloudShell을 통해서만 EC2에 명령을 실행할 수 있다. 로컬에서 ssh로 직접
   붙으려는 시도는 하지 말고, 콘솔 브라우저 터미널 사용을 안내하거나 사용자에게 위임해라.
4. EC2 인스턴스는 반드시 1대, gunicorn 워커도 반드시 1개여야 한다
   (game_state가 프로세스 메모리에만 있음 — 늘리면 게임이 깨진다).
5. 실제 리소스 변경(EC2 시작/중지/생성, CloudFront 배포/업데이트, git push,
   보안그룹 수정)은 실행 전에 무엇을 할지 먼저 설명하고 확인을 받아라.
6. 완료 후 deploy/DEPLOY_PROMPT.md의 "현재 인프라 상태" 섹션을 실제 값으로 갱신해라
   (EC2 IP, CloudFront 배포 상태, 마지막 배포 시각 등) — 다음 사람이 또 처음부터
   추적하지 않도록.

목표: 참가자가 CloudFront HTTPS 주소로 접속해 게임을 플레이할 수 있는 상태.
```

---

## 프로젝트 요약

- Flask 기반 실시간 색깔 찾기 게임. 참가자는 QR로 접속, 방장(`/host`, PIN 로그인)이 게임 진행.
- 사진 속 목표 색과 가장 비슷한 영역을 YOLO11n-seg(+GPU 없으면 LAB 색상 영역 탐지, GPU 있으면 SlimSAM fallback)로 분석.
- 게임 상태(`backend/game_state.py`)가 **프로세스 메모리에만 존재** → 서버 재시작 시 초기화, 반드시 인스턴스 1대·워커 1개.
- 구조: `backend/`(Flask 앱·API·이미지 분석), `frontend/`(템플릿·정적 파일), `app.py`(엔트리포인트).
- 컨테이너 배포용 `Dockerfile`도 있음(로컬 스택 미가공 배포엔 안 씀, 참고/대안용).

## 현재 인프라 상태 (마지막 확인: 2026-08-19, 직접 확인 필요 — 아래 "확인 필요" 표시 참고)

| 항목 | 값 |
|---|---|
| AWS 계정 | 045861054142 (학교 공유 계정) |
| 리전 | ap-northeast-1 (도쿄) |
| 키 페어 | `colorhunt-key` (개인키 `deploy/colorhunt-key.pem`, git 미추적) |
| 보안그룹 | `colorhunt-sg` (`sg-0b709fd71227d70ee`), 22/80/443 all open |
| CloudFront 배포 ID | `EO1Y9QZXSVH77` |
| CloudFront 도메인 | `https://du5n20p3401uf.cloudfront.net` |
| CloudFront 현재(cf-current.json) 오리진 | `ec2-52-194-190-84.ap-northeast-1.compute.amazonaws.com` |
| 마지막으로 준비된 업데이트(cf-update-config.json) 오리진 | `ec2-54-249-79-172.ap-northeast-1.compute.amazonaws.com` |
| GitHub 저장소 | https://github.com/Gapsick/findcolor.git |

**⚠ 확인 필요:** `cf-current.json`(실제 배포된 설정)과 `cf-update-config.json`(준비된 업데이트안)의
오리진 IP가 서로 다르다 — EC2 인스턴스가 재시작되며 퍼블릭 IP가 바뀌었고, CloudFront 오리진을
새 IP로 갱신하는 작업이 준비만 되고 실제 적용됐는지 미확인 상태로 보인다. 배포 전에 반드시:
1. AWS 콘솔에서 현재 EC2 퍼블릭 IPv4 DNS를 확인
2. CloudFront 배포(`EO1Y9QZXSVH77`)의 현재 오리진과 비교
3. 다르면 콘솔에서 오리진 도메인을 최신 EC2 DNS로 갱신 (아래 "3단계" 참고)

인스턴스를 비용 절감을 위해 Stop 해뒀다면 재시작 시 IP가 또 바뀐다 — 매번 이 확인이 필요하다.

---

## 0단계 — 배포 전 로컬/깃 정리 (필수, 아직 안 끝남)

**현재 로컬 저장소 상태(2026-08-19 확인)는 배포 준비가 끝나지 않았다:**

- 현재 브랜치 `feat/aws-deploy`는 `origin/main`보다 **뒤처져 있음** — main에는 이 브랜치에 없는
  "개발용 page 추가" 커밋(`ff78c6b`)이 있다 (`backend/routes/dev.py`, `frontend/templates/dev.html`,
  `game_state.py`/`app.py` 변경 포함).
- `Dockerfile`, `.dockerignore`, `deploy/` 전체(배포 스크립트, systemd 유닛, nginx 설정 등)가
  **아직 커밋되지 않은 미추적 파일**이다 — 즉 GitHub에는 아직 이 배포 설정이 전혀 없다.
- `.gitignore`, `backend/routes/admin.py`(퍼블릭 URL 기준 QR 생성용 `COLORHUNT_PUBLIC_URL` 처리)도
  수정됐지만 미커밋 상태다.

`setup_ec2.sh`/`user-data.sh`는 GitHub의 `main` 브랜치를 `git clone`하기 때문에,
**이 변경들이 main에 병합·푸시되기 전까지는 EC2에서 deploy/ 스크립트 자체를 받을 수 없다.**
즉 지금 이 순간 "그대로 갖다 놓으면 바로 배포되는" 상태가 아니라, 아래를 먼저 해야 한다:

```bash
# feat/aws-deploy 안에서
git add .gitignore backend/routes/admin.py .dockerignore Dockerfile deploy/
git commit -m "Add AWS deploy setup (EC2 + CloudFront, Docker)"

# main의 최신 커밋(dev 페이지 추가)과 합치기 — 충돌 가능성 낮음(겹치는 파일 없음)
git fetch origin
git rebase origin/main   # 또는 팀 컨벤션에 따라 merge

# 사용자 확인 후 푸시
git push origin feat/aws-deploy
# 이후 PR 생성 → main 병합 (또는 팀 컨벤션에 따라 바로 main에 병합)
```

**git push, 브랜치 병합은 공유 저장소에 영향을 주므로 실행 전 반드시 사용자에게 확인받을 것.**

---

## 1단계 — EC2 인스턴스 확인/생성

이미 인스턴스가 있다면(위 표 참고) 콘솔에서 상태만 확인(Stop 상태면 Start). 새로 만들 경우:

- AMI: Amazon Linux 2023
- 타입: t3.medium (torch+ultralytics가 메모리를 많이 씀, t3.small은 빠듯)
- 스토리지: gp3 20GB
- 키 페어: `colorhunt-key`
- 보안그룹: `colorhunt-sg` — SSH(22, 내 IP만) / HTTP(80, 0.0.0.0/0, CloudFront용) / HTTPS(443, 불필요·CloudFront가 TLS 종료)

인스턴스가 뜨면 **퍼블릭 IPv4 DNS**(`ec2-x-x-x-x.ap-northeast-1.compute.amazonaws.com`)를 확인.

**로컬 네트워크에서 EC2로 SSH/HTTP 직접 연결이 막혀 있다** (학교망 추정, AWS IP 대역 자체가 차단된 것으로 보임 — github.com 등 다른 호스트의 동일 포트는 정상 연결됨). CloudFront는 AWS 내부망으로 오리진에 붙으므로 이 문제와 무관하게 정상 동작한다. EC2에 직접 명령을 실행해야 할 때는 **AWS 콘솔 → EC2 → 인스턴스 선택 → Connect → EC2 Instance Connect(브라우저 터미널)** 를 사용한다.

## 2단계 — 코드 배포 (EC2 Instance Connect 브라우저 터미널에서)

```bash
curl -O https://raw.githubusercontent.com/Gapsick/findcolor/main/deploy/setup_ec2.sh
chmod +x setup_ec2.sh
./setup_ec2.sh https://github.com/Gapsick/findcolor.git
```

`setup_ec2.sh`가 하는 일: Python 3.12/git/nginx 설치 → `/opt/colorhunt`에 클론 →
venv + `deploy/requirements-prod.txt`(requirements.txt + gunicorn) 설치 →
`deploy/colorhunt.env` 생성(`COLORHUNT_SECRET` 랜덤 생성) →
`colorhunt.service`를 systemd 등록해 gunicorn을 127.0.0.1:8000에서 상시 실행 →
nginx를 80 → 127.0.0.1:8000 리버스 프록시로 설정.

완료 후:

```bash
sudo vi /opt/colorhunt/deploy/colorhunt.env   # COLORHUNT_ADMIN_PIN을 1234에서 변경
sudo systemctl restart colorhunt
curl -I http://127.0.0.1/                     # 200이면 정상
sudo systemctl status colorhunt               # active (running) 확인
sudo journalctl -u colorhunt -f                # YOLO 워밍업 로그 등 확인
```

## 3단계 — CloudFront 오리진 확인/갱신

기존 배포(`EO1Y9QZXSVH77`, `https://du5n20p3401uf.cloudfront.net`)가 있으면 오리진 IP만 최신화하면 된다:

1. CloudFront 콘솔 → 해당 배포 → Origins → 오리진 편집
2. Origin domain을 현재 EC2 퍼블릭 DNS로 갱신 (위 "확인 필요" 항목)
3. 나머지 설정은 그대로 유지 (Origin protocol: HTTP only / Viewer: Redirect HTTP to HTTPS / Cache policy: CachingDisabled)

새로 만드는 경우:

1. CloudFront → Create Distribution
2. Origin domain: EC2 퍼블릭 DNS
3. Origin protocol policy: HTTP only (포트 80)
4. Viewer protocol policy: Redirect HTTP to HTTPS
5. Cache policy: CachingDisabled (게임 상태 API가 실시간이라 캐시되면 안 됨)
6. Alternate domain name / Custom SSL certificate: 비워둠 → 기본 `*.cloudfront.net` 인증서 자동 적용
7. 생성 후 `Enabled` 상태가 되면 Distribution domain name 확인

CloudFront 도메인이 정해지면 EC2로 다시 접속(Instance Connect)해서 `COLORHUNT_PUBLIC_URL`을 반영
(참가자용 QR이 이 값 기준으로 생성됨 — `backend/routes/admin.py`):

```bash
sudo vi /opt/colorhunt/deploy/colorhunt.env
# COLORHUNT_PUBLIC_URL=https://<distribution>.cloudfront.net
sudo systemctl restart colorhunt
```

## 4단계 — 최종 확인

- 참가자: `https://<distribution>.cloudfront.net/`
- 방장: `https://<distribution>.cloudfront.net/host`
- `/host`의 QR을 실제 휴대폰으로 스캔해 CloudFront 주소로 들어오는지 확인

## 업데이트 배포 (코드 수정 후, 이후 반복 작업)

```bash
cd /opt/colorhunt
git pull
./venv/bin/pip install -r deploy/requirements-prod.txt   # 의존성 바뀐 경우만
sudo systemctl restart colorhunt
```

## 알아둘 점 / 주의사항

- 게임 데이터는 재시작하면 초기화(인메모리). `systemctl restart`/EC2 재부팅/배포 갱신 모두 초기화 유발.
- CloudFront 배포 생성/삭제는 몇 분 걸림 — 실수로 삭제 주의.
- 비용: t3.medium 24시간 기준 월 $30선(리전별 상이), CloudFront는 트래픽 종량(소규모 게임이면 미미).
  상시 운영 안 하면 행사 전후로 EC2 **Stop**해서 비용 절감 가능 — 재시작 시 퍼블릭 IP가 바뀌므로
  3단계(CloudFront 오리진 갱신)를 다시 해야 함.
- 보안 강화(선택): EC2 80번 포트가 전체 공개라 CloudFront 없이 EC2 IP로 직접 접속도 가능한 상태.
  막으려면 CloudFront에 커스텀 헤더(`X-Origin-Verify: <비밀값>`) 추가 + nginx에서 헤더 없으면 403 처리.
- 이 계정은 학교 공유 AWS 계정이다 — `colorhunt-*` 이름이 아닌 리소스는 절대 건드리지 말 것.
