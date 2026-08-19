# Color Hunt

## Project structure

```text
backend/                 Flask API, routes, game state, image analysis
frontend/templates/      HTML templates
frontend/static/         CSS and browser JavaScript
app.py                   Compatibility entry point
requirements.txt         Python dependencies
```

The existing command still starts the application:

```powershell
python app.py
```

The packaged backend can also be started with:

```powershell
python -m backend.app
```

## 역할별 파일

### 개발자 A — 서버와 게임 진행

- `app.py`: Flask 앱 생성과 실행
- `game_state.py`: 참가자, 타이머, 제출, 게임 시작, 목표 색 상태
- `routes/api.py`: 참가자 및 관리자 API
- `routes/admin.py`: 관리자 로그인과 관리자 화면 경로
- `qr_utils.py`: 참가 QR 생성
- `image_analysis.py`: 중앙색 추출, 색상 유사도, 목표색 영역 테두리

### 개발자 B — 참가자 화면과 디자인

- `routes/player.py`: 참가자 화면 경로
- `templates/`: HTML 화면
- `static/css/style.css`: 전체 디자인
- `static/js/`: 닉네임 입력, 대기방, 관리자 화면 동작

### QA·운영 담당

- 서로 다른 휴대폰에서 QR 접속 테스트
- 닉네임 중복, Start, 사진 제출, 타이머, 초기화 테스트
- 화면 문구와 일본어 번역 검수
- 발견한 문제의 기기·행동·결과·스크린샷 기록

## 실행

```powershell
python -m pip install -r requirements.txt
python app.py
```

- 참가자: `http://PC의-IP:5000/`
- 방장: `http://PC의-IP:5000/host`
- 기존 `/admin` 주소도 동일하게 작동합니다.
- 기본 관리자 PIN: `1234`

기존 방식인 `python 1.py`도 사용할 수 있습니다.

## AI 모델 준비

기본 분석은 저장소의 `yolo11n-seg.pt`를 사용합니다. GPU가 있으면 자동으로 CUDA를 선택합니다.

YOLO가 학습하지 않은 잔디, 벽, 바닥 같은 영역은 빠른 LAB 색상 영역 탐지로 보완하고, 연속된 가장 큰 유사색 영역의 외곽선을 표시합니다.

서버 시작 시 모델을 워밍업하고 80ms 안에 도착한 요청을 최대 20장까지 자동으로 묶어 배치 추론합니다. 배포 서버는 웹 프로세스를 1개만 실행해야 게임 메모리와 GPU 모델이 중복되지 않습니다.

YOLO가 물체를 찾지 못했을 때 GPU 환경에서만 SlimSAM fallback을 사용합니다. SlimSAM 체크포인트는 한 번 내려받습니다.

```powershell
python -c "from transformers import SamModel, SamProcessor; SamProcessor.from_pretrained('Zigeng/SlimSAM-uniform-50'); SamModel.from_pretrained('Zigeng/SlimSAM-uniform-50')"
```

모델은 사용자 캐시에 저장되며 이후 실행에서는 다시 다운로드하지 않습니다.
