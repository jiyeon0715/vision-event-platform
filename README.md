# Edge AI Vision Event Monitoring Platform

## 프로젝트 소개

AI Vision Monitoring Platform은 이미지/영상 입력으로부터 AI 이벤트를 생성하고, 생성된 이벤트를 Backend에서 관리하며, Next.js Dashboard에서 조회/검색/통계를 제공하는 웹서비스입니다.

현재 구현은 영상 파일 기반 파이프라인, 이벤트 저장, REST API(`main:app`), Next.js 기반 Dashboard를 중심으로 구성되어 있습니다. 실제 카메라 실시간 스트림 연동과 운영 배포 구성은 진행 중입니다.

## 시스템 아키텍처

현재 코드 기준의 주요 처리 흐름은 다음과 같습니다.

```mermaid
flowchart TD
    A["Video / Image File"] --> B["OpenCV"]
    B --> C["VisionEventPipeline"]
    C --> D["YOLO Detector"]
    D --> E["ByteTrack Tracker"]
    E --> F["Rule Engine"]
    F --> G["AlertPolicy"]
    G --> H["Event Repository"]
    G --> I["Snapshot Files"]
    H --> J["SQLite / PostgreSQL"]
    J --> K["FastAPI REST API (main:app)"]
    K --> L["Next.js Dashboard"]
```

`scripts/run_video.py`가 영상 파일을 프레임 단위로 읽고 `VisionEventPipeline`에 전달합니다. 파이프라인은 객체 검출, 객체 추적, 규칙 평가, 알림 중복 제어를 거쳐 이벤트를 만들고, 저장 옵션이 켜져 있으면 이벤트와 snapshot을 저장합니다.

## 주요 기능

- YOLO 기반 객체 검출
- ByteTrack 스타일 객체 추적
- Rule Engine 기반 이벤트 생성
- danger-zone, loitering, person-count 규칙
- Alert cooldown 기반 반복 이벤트 제어
- 이벤트 저장 (SQLite / PostgreSQL)
- 이벤트 발생 프레임 snapshot 저장
- REST API를 통한 이벤트 조회 / 검색 / 통계
- Next.js Dashboard에서 Events, Cameras, EventTypes 관리
- API key 기반 보호 설정
- pytest 기반 단위 테스트

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| API | FastAPI, Pydantic, Uvicorn |
| Vision | OpenCV, Ultralytics YOLO |
| Tracking | ByteTrack 스타일 tracker, `lapx` |
| Rule | Python rule evaluator, YAML 설정 |
| Persistence | SQLAlchemy, SQLite, PostgreSQL driver |
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Test | pytest, httpx, FastAPI TestClient |
| Runtime | Python 3.12, Docker, Docker Compose |

## 프로젝트 구조

```text
main.py                  FastAPI 앱 entrypoint (uvicorn main:app)
app/
  api/                   REST API routes
  core/                  설정 로딩, 보안 설정
  database/              SQLAlchemy model, session, health check
  detector/              YOLO detector adapter
  pipeline/              frame-to-event orchestration
  repositories/          SQLAlchemy 기반 repository (Event, Camera, EventType, Snapshot)
  rules/                 danger-zone, loitering, person-count rule
  schemas/               Pydantic request/response schema
  services/              camera health registry
  tracker/               ByteTrack adapter
vision/
  inputs/                FrameSource (ImageSource, VideoFileSource)
config/config.yaml       app, database, camera, rule, alert 설정
scripts/run_video.py     로컬 영상 파일 파이프라인 실행
scripts/run_image.py     로컬 이미지 파이프라인 실행
frontend/                Next.js 14 Dashboard
tests/                   unit/integration test suite
docker/Dockerfile        컨테이너 이미지 정의
docker-compose.yml       app + PostgreSQL 로컬 실행 구성
```

## 실행 방법

### 의존성 설치

```bash
pip install -r requirements.txt
```

### 기본 API 실행

기본 API entrypoint는 `main:app`입니다.

```bash
uvicorn main:app --reload
```

상태 확인:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

### 영상 파일 파이프라인 실행

```bash
python scripts/run_video.py /path/to/video.mp4 --camera-id gate_01
```

이벤트와 snapshot을 저장하려면 `--save-events` 옵션을 사용합니다. 기본적으로 `data/events.db` SQLite를 사용합니다.

```bash
python scripts/run_video.py /path/to/video.mp4 \
  --camera-id gate_01 \
  --save-events \
  --db-path data/events.db \
  --snapshot-dir data/snapshots
```

PostgreSQL 등 다른 DB를 사용하려면 `--database-url` 또는 `DATABASE_URL` 환경변수를 설정합니다.

```bash
DATABASE_URL=postgresql://user:pass@localhost/vision python scripts/run_video.py \
  /path/to/video.mp4 --camera-id gate_01 --save-events
```

설정 파일에 정의된 camera 목록을 사용하려면 다음 명령을 실행합니다.

```bash
python scripts/run_video.py --config config/config.yaml
```

### Next.js Frontend 실행

Next.js 기반 Dashboard는 `frontend/` 디렉터리에 있습니다. FastAPI 기본 API(`main:app`)를 먼저 실행한 뒤 별도 터미널에서 프론트엔드를 실행합니다.

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 다음 주소를 엽니다.

```text
http://localhost:3000
```

기본 API 주소는 `http://localhost:8000`입니다. 다른 주소나 API key를 사용해야 하면 `frontend/.env.local`에 다음 값을 설정합니다.

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=change-me
```

현재 프론트엔드는 프로젝트 구조와 API 연동 기반을 우선하기 위해 shadcn/ui를 도입하지 않았습니다. Dashboard, Events, Cameras, Settings의 기본 라우트와 공통 Layout만 직접 구성했고, 컴포넌트 요구가 구체화되면 디자인 시스템 도입 여부를 다시 판단합니다.

### Docker Compose 실행

Docker Compose는 `main:app`과 PostgreSQL을 함께 실행합니다.

```bash
docker compose up --build
```

API 주소:

```text
http://localhost:8000
```

컨테이너 안에서 영상 파일 파이프라인을 실행할 수 있습니다.

```bash
docker compose exec app python scripts/run_video.py \
  /app/data/videos/sample.mp4 \
  --camera-id gate_01 \
  --save-events
```

## 주요 API

entrypoint: `uvicorn main:app`

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/health` | 서비스 상태 확인 |
| `GET` | `/health/db` | DB 연결 상태 확인 |
| `GET` | `/events` | 이벤트 목록 조회 (pagination, filter) |
| `GET` | `/events/latest` | 최신 이벤트 조회 |
| `GET` | `/events/{event_id}` | 단일 이벤트 조회 |
| `GET` | `/events/stats` | 이벤트 통계 조회 |
| `GET` | `/events/{event_id}/snapshots` | 이벤트 snapshot 목록 |
| `GET` | `/cameras` | 카메라 목록 조회 |
| `POST` | `/cameras` | 카메라 등록 |
| `GET` | `/cameras/{id}` | 카메라 단건 조회 |
| `PATCH` | `/cameras/{id}` | 카메라 수정 |
| `DELETE` | `/cameras/{id}` | 카메라 비활성화 |
| `GET` | `/cameras/health` | 런타임 카메라 health 조회 |
| `GET` | `/event-types` | EventType 목록 조회 |
| `POST` | `/event-types` | EventType 등록 |
| `PATCH` | `/event-types/{id}` | EventType 수정 |
| `DELETE` | `/event-types/{id}` | EventType 비활성화 |

`API_KEY` 환경변수가 설정된 경우 보호 대상 API에는 `X-API-Key` header를 전달해야 합니다.

```bash
curl -H "X-API-Key: change-me" \
  "http://localhost:8000/events/latest?limit=5&camera_id=gate_01"
```

## 테스트

전체 테스트 실행:

```bash
python -m pytest
```

CI처럼 native vision dependency 부담을 줄인 환경에서는 다음 의존성을 사용할 수 있습니다.

```bash
pip install -r requirements-ci.txt
python -m pytest
```

현재 테스트는 파이프라인, 규칙, 저장소, API, 보안 설정, 카메라 health, 설정 로딩, snapshot path 검증을 포함합니다.

## 향후 개선 예정

- Dashboard 실제 데이터 연결 (stats, camera count)
- Events 페이지 필터 / 검색 UI
- Snapshot 이미지 뷰어
- 통계 차트 (시간별 이벤트, 타입별 분포)
- RTSP / Webcam 실시간 스트림 지원
- Alembic Migration 적용
- 인증 및 권한 구조 개선
