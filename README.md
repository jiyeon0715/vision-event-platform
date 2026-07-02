# Vision Event Platform

A real-time computer vision event platform that turns object detection and tracking output into queryable operational events.

The project demonstrates how a video analytics backend can be structured beyond a single model inference script: frames are processed through detection, tracking, configurable rules, alert throttling, snapshot storage, database persistence, and FastAPI endpoints for monitoring and review.

## Project Overview

Vision Event Platform is designed for security, facility operations, and safety-monitoring scenarios where teams need to detect meaningful activity from camera feeds and inspect the resulting events later.

Instead of treating every detection as an alert, the system applies rule-based event evaluation. A camera stream is processed by a YOLO detector, a ByteTrack-style tracker, and one or more configurable rules such as danger-zone entry, loitering, and person-count thresholds. Events are filtered by an alert policy, optionally saved with frame snapshots, and exposed through API endpoints for dashboards or downstream services.

The current implementation supports:

- Single-video and multi-camera local pipeline runs.
- Config-driven camera and rule definitions.
- Per-camera health tracking during runtime.
- SQLite for local development and PostgreSQL for Docker Compose runs.
- FastAPI endpoints for health checks, event reads, event statistics, and camera health.
- Snapshot file storage for persisted event review.

## Architecture

```mermaid
flowchart LR
    A["Camera sources<br/>config/config.yaml"] --> B["Video runner<br/>scripts/run_video.py"]
    B --> C["VisionEventPipeline"]
    C --> D["YOLO detector"]
    D --> E["ByteTrack tracker"]
    E --> F["Rule engine<br/>danger zone / loitering / person count"]
    F --> G["AlertPolicy<br/>cooldown filtering"]
    G --> H["Event snapshots<br/>data/snapshots/{camera_id}"]
    G --> I["Event repository<br/>SQLite or PostgreSQL"]
    C --> J["CameraHealthRegistry"]
    I --> K["FastAPI"]
    J --> K
    K --> L["Dashboard or API clients"]
```

### Request/Data Flow

1. Camera definitions are loaded from `config/config.yaml`, or a legacy single video path is passed on the command line.
2. The runner creates one `VisionEventPipeline` context per camera.
3. Each frame is detected once, tracked once, then evaluated by all enabled rules.
4. Emitted events receive a `camera_id` and pass through `AlertPolicy` cooldown filtering.
5. Approved events can be printed, saved to the database, and paired with a JPEG snapshot.
6. FastAPI reads persisted events and aggregate statistics from the database.
7. Runtime camera health is kept in memory and exposed through `/cameras/health`.

## Features

- **Vision pipeline orchestration**: coordinates detector, tracker, rules, alert policy, persistence, and health reporting.
- **Plugin-style rule loading**: enables rules from YAML configuration without changing the runner.
- **Event rules**: supports danger-zone, loitering, and person-count event types.
- **Alert cooldowns**: prevents repeated notifications for the same rule from flooding storage or clients.
- **Multi-camera support**: processes configured camera sources and stamps every event with `camera_id`.
- **Snapshot capture**: writes event frame JPEGs to per-camera folders and stores the snapshot path with the event.
- **Database abstraction**: supports local SQLite and PostgreSQL through SQLAlchemy URLs.
- **Operational API**: exposes health checks, event reads, event statistics, and camera health endpoints.
- **Dockerized runtime**: includes an app container and PostgreSQL service through Docker Compose.
- **Testable design**: core pipeline, rules, repository behavior, API routes, config loading, and camera health are covered by unit tests.

## Tech Stack

| Area | Technologies |
| --- | --- |
| API | FastAPI, Pydantic, Uvicorn |
| Vision | OpenCV, Ultralytics YOLO |
| Tracking | ByteTrack-style tracker, `lapx` |
| Rules | Config-driven Python rule evaluators |
| Persistence | SQLAlchemy, SQLite, PostgreSQL, psycopg |
| Runtime | Python 3.12, Docker, Docker Compose |
| Testing | pytest, httpx |

## Repository Structure

```text
app/
  api/                 FastAPI routes
  core/                settings and config loading
  database/            SQLAlchemy models, sessions, health checks
  detector/            YOLO detector adapter
  pipeline/            frame-to-event orchestration
  repositories/        database-backed event repository
  rules/               event rule evaluators and loader
  services/            camera health registry and event service
  tracker/             tracking adapters
config/config.yaml     camera, rule, alert, and database configuration
scripts/run_video.py   local and container video pipeline runner
storage/               local SQLite repository used by runner flows
tests/                 unit and integration test suite
docker/Dockerfile      production-like API image
docker-compose.yml     API + PostgreSQL stack
```

## Local Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI app:

```bash
uvicorn main:app --reload
```

Local development uses SQLite by default via `config/config.yaml`:

```text
sqlite:///data/events.db
```

Check service health:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

Run the pipeline against one local video:

```bash
python scripts/run_video.py /path/to/video.mp4 --camera-id gate_01
```

Save emitted events and snapshots locally:

```bash
python scripts/run_video.py /path/to/video.mp4 \
  --camera-id gate_01 \
  --save-events \
  --db-path data/events.db \
  --snapshot-dir data/snapshots
```

Run configured multi-camera sources:

```bash
python scripts/run_video.py --config config/config.yaml
```

Example camera configuration:

```yaml
cameras:
  - id: gate_01
    source: data/videos/video1.mp4
  - id: gate_02
    source: data/videos/video2.mp4
```

## Docker Run

Docker deployment uses PostgreSQL. `docker-compose.yml` explicitly injects `DATABASE_URL` into the app container, which overrides the local SQLite setting from `config/config.yaml`.

Run the full stack with PostgreSQL:

```bash
docker compose up --build
```

The API is available at:

```text
http://localhost:8000
```

Docker Compose starts:

- `app`: FastAPI service running `main:app`.
- `postgres`: PostgreSQL 16 with a health check.
- `postgres_data`: named volume for durable database data.
- `./data:/app/data`: bind mount for local videos, SQLite files, and event snapshots.

The app container receives:

```text
DATABASE_URL=postgresql://vision:vision@postgres:5432/vision_events
```

Run the video pipeline inside the Compose app container:

```bash
docker compose exec app python scripts/run_video.py \
  /app/data/videos/sample.mp4 \
  --camera-id gate_01 \
  --save-events
```

Verify persisted events:

```bash
curl "http://localhost:8000/events/latest?limit=5"
```

### API Image Only

Build and run only the API image:

```bash
docker build -f docker/Dockerfile -t vision-event-platform .

docker run --rm -p 8000:8000 \
  -e DATABASE_URL=sqlite:///data/events.db \
  -v "$PWD/data:/app/data" \
  vision-event-platform
```

## Demo Dashboard

The primary API entry point is `main:app`. The repository also includes a lightweight saved-events dashboard in `api.main` for local portfolio demos that read from the runner's SQLite database:

```bash
EVENT_DB_PATH=data/events.db SNAPSHOT_DIR=data/snapshots uvicorn api.main:app --reload
```

Open:

```text
http://localhost:8000/dashboard
```

The dashboard renders service status, event counts by rule and camera, current camera health, recent saved events, and snapshot thumbnails when `snapshot_path` is present.

## API Examples

### Health

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok"
}
```

```bash
curl http://localhost:8000/health/db
```

```json
{
  "status": "ok",
  "backend": "sqlite"
}
```

### Latest Events

```bash
curl "http://localhost:8000/events/latest?limit=5&camera_id=gate_01"
```

```json
[
  {
    "id": 1,
    "event_type": "danger_zone",
    "camera_id": "gate_01",
    "track_id": 42,
    "timestamp": 123.45,
    "message": "Track 42 stayed inside the danger zone.",
    "snapshot_path": "data/snapshots/gate_01/2f7c6f6d0a7f4f94a6a0c1fd7b7d9e91.jpg",
    "created_at": "2026-06-22T10:30:00Z"
  }
]
```

### Single Event

```bash
curl http://localhost:8000/events/1
```

### Event Statistics

```bash
curl "http://localhost:8000/events/stats?camera_id=gate_01&rule_name=danger_zone"
```

```json
{
  "total_event_count": 12,
  "event_count_by_rule_name": {
    "danger_zone": 12
  },
  "event_count_by_camera_id": {
    "gate_01": 12
  },
  "hourly_event_counts": {
    "2026-06-22T10:00:00Z": 7,
    "2026-06-22T11:00:00Z": 5
  },
  "latest_event_timestamp": "2026-06-22T11:14:08Z"
}
```

### Camera Health

```bash
curl http://localhost:8000/cameras/health
```

```json
[
  {
    "camera_id": "gate_01",
    "source": "data/videos/video1.mp4",
    "status": "online",
    "last_frame_at": "2026-06-22T10:30:00Z",
    "last_event_at": "2026-06-22T10:30:03Z",
    "processed_frame_count": 1800,
    "emitted_event_count": 4,
    "last_error": null
  }
]
```

## Screenshots and Snapshots

This repository stores event evidence as generated image snapshots rather than committed demo screenshots.

When `scripts/run_video.py` emits an event, it writes the current frame as a JPEG under:

```text
data/snapshots/{camera_id}/{uuid}.jpg
```

The saved event stores that location in `snapshot_path`, allowing an API client or dashboard to show a thumbnail beside the event metadata. The per-camera folder structure makes it easy to inspect events by source and avoids filename collisions when multiple cameras emit events at the same time.

Because snapshots are generated from local video inputs, `data/snapshots/.gitkeep` is committed but generated JPEGs are expected to remain local runtime artifacts.

## Testing Result

The test suite is organized around unit coverage for the behavior that matters most in an interview or production-readiness review:

- Pipeline orchestration and camera id propagation.
- Danger-zone, loitering, and person-count rule behavior.
- Alert cooldown policy.
- SQLite and SQLAlchemy event repository behavior.
- Saved event API responses and query filtering.
- Event statistics API behavior.
- Runtime camera health state.
- Configuration loading.
- Snapshot path creation in the video runner.
- Database health checks.

Run tests with:

```bash
pytest
```

For lighter CI environments that should avoid native vision/tracking dependency builds:

```bash
pip install -r requirements-ci.txt
pytest
```

Documentation-only note: this README polish did not require running application code or the test suite.

## Future Improvements

- Add a small dashboard frontend that renders event lists, statistics, camera health, and snapshot thumbnails.
- Serve snapshot files through authenticated API endpoints instead of exposing filesystem paths directly.
- Add async or background worker execution for long-running camera streams.
- Support RTSP camera sources and reconnection/backoff policies.
- Persist camera health history for operational trend analysis.
- Add event acknowledgement, severity, and review workflow fields.
- Add migrations with Alembic for production database changes.
- Add CI jobs for linting, unit tests, Docker image build, and API smoke tests.
- Add model configuration profiles for CPU/GPU environments.
- Add structured logging and metrics export for observability.

## Interview-Friendly Explanation

This project is a backend-oriented computer vision system, not just a model demo. The main design decision is separating detection from event semantics. YOLO answers "what objects are in the frame," tracking answers "which object is which over time," and the rule layer answers "does this behavior matter operationally?"

The pipeline is intentionally modular:

- The detector and tracker can be swapped behind small interfaces.
- Rules are loaded from configuration and evaluated against the same track list.
- Alert policy is isolated so cooldown behavior is testable.
- Persistence is behind a repository boundary and can target SQLite or PostgreSQL.
- FastAPI exposes read models for dashboards without coupling clients to the video runner.

In an interview, the system can be described as an event-driven architecture for video analytics:

1. Ingest frames from one or more camera sources.
2. Convert frames into detections and stable tracks.
3. Evaluate tracks against business rules.
4. Filter noisy repeats with alert policy.
5. Store event metadata and snapshots.
6. Expose APIs for monitoring, querying, and dashboard consumption.

The strongest engineering points are the clear boundaries between pipeline stages, config-driven rule behavior, database portability, API testability, and operational features such as camera health and event statistics.
