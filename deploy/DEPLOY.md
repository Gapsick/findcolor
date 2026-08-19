# AWS 배포 가이드

## 지금 쓰는 방식: 로컬 Docker + Cloudflare Tunnel (무료)

처음엔 AWS Lightsail Container Service(월 $40, 파워 medium)로 상시 배포했었는데,
발표·데모 때만 잠깐 공개 주소가 있으면 되는 용도라 **비용이 계속 나가는 게 낭비**라서
Lightsail 서비스는 삭제했다. 지금은 발표하는 사람 컴퓨터에서 Docker로 앱을 띄우고
**Cloudflare Tunnel**(회원가입 불필요, 완전 무료)로 그 순간만 공개 HTTPS 주소를 연다.
컴퓨터를 끄면 주소도 같이 사라지고, 평소엔 돈이 전혀 안 든다.

### 발표/데모 당일 켜는 법

```powershell
cd "findcolor"
docker build -t colorhunt:latest .          # 코드가 바뀐 경우만, 이미 빌드돼 있으면 생략
docker run -d --name colorhunt-live -p 8000:8000 -e COLORHUNT_WARMUP=1 colorhunt:latest

& "C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8000
```

터널을 실행하면 콘솔에 `https://<랜덤단어들>.trycloudflare.com` 형태의 주소가 뜬다.
**이 주소는 매번 새로 실행할 때마다 랜덤하게 바뀐다** — 발표 직전에 실행해서 그 자리에서
QR/링크를 공유해야 한다.

- 참가자 화면: 위 주소 그대로
- 방장 화면: 위 주소 + `/host` (PIN 기본 `1234`)

### 끝난 뒤 정리

```powershell
docker rm -f colorhunt-live
```
(cloudflared는 터미널 창을 닫거나 Ctrl+C로 종료하면 터널도 같이 끊긴다.)

---

## (참고, 지금은 미사용) AWS Lightsail Container Service로 상시 배포했던 기록

별도 VPC/네트워크 설정 없이 자동으로 HTTPS 공개 주소를 주는 관리형 서비스라 한동안 이걸로
상시 배포했었다. 다만 **파워 medium 기준 월 $40 고정 요금**(트래픽 없어도 떠 있기만 하면 과금)이라,
상시 운영이 필요 없어진 뒤 서비스를 삭제했다. 나중에 다시 상시 배포가 필요해지면 아래 절차를
그대로 따라 하면 된다 (`aws lightsail create-container-service`부터 다시 시작).

- 리전: `ap-northeast-1` (도쿄)
- 서비스 이름: `colorhunt`, 파워: `medium`, 스케일: 1
- 이미지 소스: `Dockerfile` (repo 루트) — CPU 전용 torch 사용 (`--index-url https://download.pytorch.org/whl/cpu`)

### 재배포 방법 (코드 수정 후)

`deploy/lightsail-containers.json`은 실제 시크릿 값이 들어가서 git에 안 올라간다
(`.gitignore` 처리됨). 처음 배포하는 사람은 `deploy/lightsail-containers.json.example`을
복사해서 만들어야 한다.

```powershell
$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
cd "findcolor"

# 처음 한 번만: 템플릿에서 실제 설정 파일 생성 후 COLORHUNT_SECRET을 랜덤값으로 교체
Copy-Item deploy\lightsail-containers.json.example deploy\lightsail-containers.json

docker build -t colorhunt:latest .
$env:Path += ";C:\Users\<사용자>\bin"   # lightsailctl 위치
& $aws lightsail push-container-image --service-name colorhunt --image colorhunt:latest --label app --region ap-northeast-1
# 위 명령 출력의 ":colorhunt.app.N" 값을 deploy/lightsail-containers.json의 "image" 필드에 반영
& $aws lightsail create-container-service-deployment --service-name colorhunt --region ap-northeast-1 `
  --containers "file://deploy/lightsail-containers.json" `
  --public-endpoint "file://deploy/lightsail-endpoint.json"
```

### 환경변수 (deploy/lightsail-containers.json, git에는 .example만 커밋됨)

- `COLORHUNT_PUBLIC_URL`: 위 서비스 URL 그대로 — QR/참가 링크 생성에 사용 (`backend/routes/admin.py`)
- `COLORHUNT_SECRET`: Flask 세션 서명 키 (고정값, 재배포해도 관리자 세션 유지됨)
- `COLORHUNT_ADMIN_PIN`: 방장 로그인 PIN (기본 `1234`, 실사용 전 변경 권장)

### 알아둘 점

- 인메모리 게임 상태이므로 **컨테이너는 스케일 1개 고정** (여러 개로 늘리면 게임 깨짐)
- 재배포/재시작하면 게임 상태 초기화됨 (인메모리)
- 정리(비용 절감)하려면: `aws lightsail delete-container-service --service-name colorhunt --region ap-northeast-1`

---

## (참고, 미사용) 처음 시도했던 방식: EC2 + CloudFront, 도메인 없이 HTTPS

구성: **EC2 인스턴스 1대(CPU)** 에서 gunicorn(단일 워커) + nginx로 앱을 띄우고,
**CloudFront**를 앞단에 붙여 도메인 구매 없이 `https://xxxxxxx.cloudfront.net` 형태의
무료 HTTPS 주소를 받는다.

## 0. 이번 배포 실제 정보 (기록용)

- 계정: 045861054142 (학교 공유 AWS 계정 — 다른 조 리소스도 같이 있으니 `colorhunt-*` 이름만 건드릴 것)
- 리전: `ap-northeast-1` (도쿄)
- 키페어: `colorhunt-key` (개인키는 `deploy/colorhunt-key.pem`, git에는 안 올라감)
- 보안그룹: `colorhunt-sg` (`sg-0b709fd71227d70ee`) — 22/80/443 all open
- EC2 인스턴스: 상황에 따라 재생성되므로 인스턴스 ID/IP는 `aws ec2 describe-instances`로 최신 값 확인
- CloudFront 배포: `EO1Y9QZXSVH77` → `https://du5n20p3401uf.cloudfront.net`

### 겪은 문제와 해결

- **로컬 개발 네트워크(학교망 추정)에서 EC2 인스턴스로 직접 SSH(22)/HTTP(80)/443 연결이 전부 타임아웃**됨.
  같은 포트로 다른 호스트(github.com:22, neverssl.com:80 등)는 정상 연결되는 걸로 봐서 AWS EC2 IP 대역 자체를
  이 네트워크에서 막고 있는 것으로 추정. → **CloudFront는 AWS 내부망으로 오리진에 붙기 때문에 이 문제와 무관하게 동작**.
  단, 이 때문에 로컬에서 EC2에 직접 SSH로 들어가 설정을 바꾸는 게 안 됨 — 필요하면 AWS 콘솔의
  **EC2 → 인스턴스 선택 → Connect → EC2 Instance Connect(브라우저 터미널)** 를 사용할 것 (브라우저가 AWS 콘솔
  백엔드를 통해 붙기 때문에 로컬 네트워크의 직접 연결 제한과 무관함).
- **user-data 스크립트의 진행 상황을 보는 법**: 스크립트 stdout/stderr를 파일로만 리다이렉트하면 SSH가 막힌 상황에서
  진행 상황을 전혀 볼 수 없다. `exec > >(tee /var/log/colorhunt-userdata.log) 2>&1` 처럼 **콘솔에도 같이 출력**되게
  해두면 `aws ec2 get-console-output --instance-id <id>` 로 SSH 없이도 진행 상황/실패 지점을 확인할 수 있다
  (단, 콘솔 출력 API 자체가 실시간이 아니라 몇 분 지연될 수 있음).

게임 상태(`backend/game_state.py`)가 프로세스 메모리에만 있으므로 **EC2 인스턴스는 반드시 1대,
gunicorn 워커도 반드시 1개**여야 한다. 여러 개로 늘리면 참가자별로 다른 메모리 상태를 보게 되어 게임이 깨진다.

## 1. EC2 인스턴스 생성 (콘솔)

- AMI: **Amazon Linux 2023**
- 인스턴스 타입: **t3.medium** (torch + ultralytics가 메모리를 꽤 씀. t3.small은 빡빡할 수 있음)
- 스토리지: gp3 **20GB** (torch 계열 패키지가 용량을 많이 차지함)
- 키 페어: 새로 생성하거나 기존 것 사용 (SSH 접속용)
- 보안 그룹 인바운드 규칙:
  - SSH(22) — 내 IP만
  - HTTP(80) — 0.0.0.0/0 (CloudFront가 여러 IP 대역에서 접속하므로 전체 허용. 원치 않으면 아래 "보안 강화" 참고)
  - HTTPS(443)는 열 필요 없음 — TLS 종료는 CloudFront가 담당

인스턴스가 뜨면 **퍼블릭 IPv4 DNS**(`ec2-x-x-x-x.compute-1.amazonaws.com` 형태)를 메모해둔다.

## 2. 코드 배포

로컬에서 GitHub에 최신 코드를 푸시해뒀다면, EC2에 SSH로 접속해서:

```bash
ssh -i your-key.pem ec2-user@<EC2-퍼블릭IP>

curl -O https://raw.githubusercontent.com/Gapsick/findcolor/main/deploy/setup_ec2.sh
chmod +x setup_ec2.sh
./setup_ec2.sh https://github.com/Gapsick/findcolor.git
```

`setup_ec2.sh`가 하는 일:
1. Python 3.12, git, nginx 설치
2. `/opt/colorhunt`에 저장소 클론
3. venv 생성 + `deploy/requirements-prod.txt`(requirements.txt + gunicorn) 설치
4. `deploy/colorhunt.env` 생성 (COLORHUNT_SECRET 랜덤 값 자동 생성)
5. `colorhunt.service`를 systemd에 등록해 gunicorn을 127.0.0.1:8000에서 상시 실행
6. nginx를 80번 포트 → 127.0.0.1:8000 리버스 프록시로 설정

완료 후 `deploy/colorhunt.env`를 열어 **COLORHUNT_ADMIN_PIN**을 기본값 `1234`에서 바꾸고 재시작:

```bash
sudo vi /opt/colorhunt/deploy/colorhunt.env   # ADMIN_PIN 변경
sudo systemctl restart colorhunt
```

확인:

```bash
curl -I http://127.0.0.1/          # nginx 경유, 200 나오면 정상
sudo systemctl status colorhunt    # active (running) 확인
sudo journalctl -u colorhunt -f    # 로그 확인 (YOLO 워밍업 로그 등)
```

## 3. CloudFront 배포 생성 (콘솔) — 도메인 없이 무료 HTTPS

1. CloudFront → **Create Distribution**
2. **Origin domain**: EC2 퍼블릭 DNS 이름 입력 (`ec2-x-x-x-x.compute-1.amazonaws.com`)
3. **Origin protocol policy**: HTTP only (포트 80)
4. **Viewer protocol policy**: Redirect HTTP to HTTPS
5. **Cache policy**: `CachingDisabled` 선택 (게임 상태 API가 실시간으로 바뀌므로 캐시되면 안 됨)
6. **Alternate domain name (CNAME)**: 비워둠, **Custom SSL certificate**도 비워둠
   → 기본 제공되는 `*.cloudfront.net` 인증서가 자동 적용됨 (별도 도메인/인증서 불필요)
7. 생성 후 몇 분 기다리면 배포 상태가 `Enabled`가 되고, **Distribution domain name**
   (`dxxxxxxxxxxxxx.cloudfront.net`)이 부여됨

CloudFront 도메인이 나오면 EC2로 다시 접속해 `COLORHUNT_PUBLIC_URL`을 채워야 한다
(참가자용 QR 코드가 이 값 기준으로 만들어짐 — `backend/routes/admin.py`):

```bash
ssh -i your-key.pem ec2-user@<EC2-퍼블릭IP>
sudo vi /opt/colorhunt/deploy/colorhunt.env
# COLORHUNT_PUBLIC_URL=https://dxxxxxxxxxxxxx.cloudfront.net
sudo systemctl restart colorhunt
```

## 4. 최종 확인

- 참가자 접속 주소: `https://dxxxxxxxxxxxxx.cloudfront.net/`
- 방장 접속 주소: `https://dxxxxxxxxxxxxx.cloudfront.net/host`
- `/host`에서 보여주는 QR을 실제 휴대폰으로 스캔해서 CloudFront 주소로 잘 들어오는지 확인 (COLORHUNT_PUBLIC_URL 설정 여부에 따라 달라짐)

## 5. 업데이트 배포 (코드 수정 후)

```bash
ssh -i your-key.pem ec2-user@<EC2-퍼블릭IP>
cd /opt/colorhunt
git pull
./venv/bin/pip install -r deploy/requirements-prod.txt   # 의존성 바뀐 경우만
sudo systemctl restart colorhunt
```

## 6. 알아둘 점

- **게임 데이터는 재시작하면 초기화**된다 (인메모리). `systemctl restart`, EC2 재부팅, 배포 업데이트 모두 초기화를 유발함.
- **CloudFront 배포/삭제는 몇 분씩 걸림** — 실수로 삭제하지 않도록 주의.
- 비용: t3.medium을 24시간 켜두면 대략 월 $30선(리전별 상이), CloudFront는 트래픽 종량 과금(소규모 게임 트래픽이면 거의 무시할 수준). 게임을 상시 운영하지 않는다면 행사 전후로 EC2를 **Stop**(정지)해서 컴퓨팅 비용을 아낄 수 있음 — 단, 정지 후 재시작하면 퍼블릭 IP가 바뀌므로 CloudFront 오리진 설정을 EC2 DNS 이름 기준으로 해두면(위 가이드처럼) 인스턴스가 켜져 있는 동안은 그대로 갱신되어 문제 없음.

## 7. (선택) 보안 강화 — EC2에 직접 접근 차단

지금 설정은 EC2 80번 포트가 전체 공개라 CloudFront를 거치지 않고 EC2 IP로 직접 접속도 가능하다.
막고 싶다면 CloudFront에 커스텀 헤더(예: `X-Origin-Verify: <임의의 비밀값>`)를 추가하고,
nginx에서 그 헤더가 없으면 403을 반환하도록 설정하면 된다. 필요하면 말씀해주시면 설정 추가해드리겠습니다.
