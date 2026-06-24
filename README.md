# Vision Event Platform

A real-time vision event platform built with YOLO, ByteTrack, FastAPI, PostgreSQL, and Docker.

The goal of this project is to transform object detection results into an event-driven system that can be monitored, queried, and managed through APIs.

## Architecture

```text
Camera definitions
    ├─ gate_01 source
    │   ↓
    │   VisionEventPipeline context
    │   ├─ YOLO Detector
    │   ├─ ByteTrack Tracker
    │   ├─ Rule Engine
    │   └─ AlertPolicy
    │       ↓
    │       gate_01 events + snapshots
    └─ gate_02 source
        ↓
        VisionEventPipeline context
        ├─ YOLO Detector
        ├─ ByteTrack Tracker
        ├─ Rule Engine
        └─ AlertPolicy
            ↓
            gate_02 events + snapshots
                ↓
          SQLite/PostgreSQL
                ↓
          FastAPI API + Dashboard
```

The event evaluation layer is plugin-based. Each configured camera gets its own
`VisionEventPipeline` context with independent detector, tracker, rule, and
`AlertPolicy` instances. Within that context, the pipeline detects and tracks
each frame once, then passes the same track list to every enabled rule loaded
from `config/config.yaml`. Each emitted event is stamped with the camera id
before alert filtering, persistence, printing, and snapshot creation.

```mermaid
flowchart LR
    A["config/config.yaml cameras[]"] --> B["gate_01 source"]
    A --> C["gate_02 source"]
    B --> D["Pipeline context: gate_01"]
    C --> E["Pipeline context: gate_02"]
    D --> F["Detector + Tracker + Rules"]
    E --> G["Detector + Tracker + Rules"]
    F --> H["gate_01 AlertPolicy"]
    G --> I["gate_02 AlertPolicy"]
    H --> J["Events with camera_id"]
    I --> J
    J --> K["Camera snapshot folders"]
    J --> L["SQLite/PostgreSQL"]
    L --> M["API and Dashboard camera filters"]
```

```mermaid
flowchart LR
    A["Frame"] --> B["Detection"]
    B --> C["Tracking"]
    C --> D["Rules"]
    D --> E["AlertPolicy"]
    E --> F["Snapshot"]
    F --> G["DB/API/Dashboard"]
```

## Features

### Current

- FastAPI application
- Health check endpoint
- Project structure initialization
- Docker environment
- PostgreSQL integration skeleton
- Event processing architecture
- SQLite event persistence
- Read-only saved event API
- Event frame snapshot storage and dashboard thumbnails
- Multi-camera configuration and camera-filtered event queries
- Plugin-based rule engine
- Danger zone, loitering, and person-count rules

### Planned

- YOLO object detection
- ByteTrack object tracking
- Event persistence
- Event query APIs
- Dashboard integration
- CI/CD pipeline

## Tech Stack

### Vision

- OpenCV
- YOLO
- ByteTrack

### Backend

- FastAPI
- PostgreSQL

### DevOps

- Docker
- GitHub Actions

## Run Locally

Install the full runtime dependency set before running the application:

```bash
pip install -r requirements.txt
```

Start the FastAPI app locally:

```bash
uvicorn main:app --reload
```

Health check:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

The app reads database settings from `config/config.yaml` by default. Set
`DATABASE_URL` to override the configured database without editing the file:

```bash
DATABASE_URL=sqlite:///data/events.db uvicorn main:app --reload
```

SQLite remains available for local development and tests through standard
SQLAlchemy SQLite URLs such as `sqlite:///data/events.db`. PostgreSQL URLs can
use the common `postgresql://...` form; the app selects the psycopg driver at
runtime.

## Run With Docker

Build the image directly:

```bash
docker build -f docker/Dockerfile -t vision-event-platform .
```

Run the FastAPI app container:

```bash
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=sqlite:///data/events.db \
  -v "$PWD/data/snapshots:/app/data/snapshots" \
  vision-event-platform
```

Build and start the FastAPI app with PostgreSQL:

```bash
docker compose up --build
```

The API is exposed at `http://localhost:8000`.

Compose starts a `postgres` service and passes this URL to the app:

```text
DATABASE_URL=postgresql://vision:vision@postgres:5432/vision_events
```

PostgreSQL data is stored in the named `postgres_data` volume. The host `./data`
directory is mounted into the app container at `/app/data`, so local videos and
event snapshot JPEGs are available to the container.

Verify PostgreSQL event persistence end to end:

```bash
docker compose up --build
```

In another shell, place a video under `data/videos/`, then run the pipeline
inside the app container. The container already has `DATABASE_URL` set to the
Compose PostgreSQL service, so `--save-events` writes through the SQLAlchemy
PostgreSQL repository:

```bash
docker compose exec app python scripts/run_video.py /app/data/videos/sample.mp4 --save-events
```

Check the latest persisted events through the API:

```bash
curl "http://localhost:8000/events/latest?limit=5"
```

Restart the containers without removing volumes:

```bash
docker compose restart app postgres
```

Confirm the same events remain after restart:

```bash
curl "http://localhost:8000/events/latest?limit=5"
```

The startup logs include the active database backend and a redacted database URL,
for example `Database backend active: postgresql (...)`.

Run the local video pipeline against a video file:

```bash
python scripts/run_video.py /path/to/video.mp4
```

The legacy single-video command is still supported. Events use
`camera_id=default` unless `--camera-id` is provided:

```bash
python scripts/run_video.py /path/to/video.mp4 --camera-id gate_01
```

For multi-camera runs, define cameras in `config/config.yaml` and run without a
positional video path:

```yaml
cameras:
  - id: gate_01
    source: data/videos/video1.mp4

  - id: gate_02
    source: data/videos/video2.mp4
```

```bash
python scripts/run_video.py --config config/config.yaml
```

The runner reads frames with OpenCV, creates one `VisionEventPipeline` per
camera, prints emitted events to the console, and exits gracefully when each
source reaches the end of the file.

Save emitted events to a local SQLite database while still printing JSON lines:

```bash
python scripts/run_video.py /path/to/video.mp4 --save-events --db-path data/events.db
```

If `DATABASE_URL` is set, `--save-events` writes to that SQLAlchemy database URL.
If no database URL is set, the video runner keeps the local SQLite behavior and
writes to `data/events.db` unless `--db-path` is provided.
When the runner emits an event, it writes the current frame to a per-camera
snapshot folder such as `data/snapshots/gate_01/` and stores the snapshot path
with the saved event. The camera folder plus UUID filename avoids collisions
across sources.
Use `--snapshot-dir` to choose a different local snapshot directory:

```bash
python scripts/run_video.py /path/to/video.mp4 --save-events --snapshot-dir data/snapshots
```

## Rule Configuration

Rules are loaded from `config/config.yaml`. Multiple enabled rules run on the
same tracked frame, and their emitted events are combined before `AlertPolicy`
decides which ones should be emitted.

```yaml
alert_policy:
  default_cooldown_sec: 10
  rules:
    danger_zone:
      cooldown_sec: 10
    loitering:
      cooldown_sec: 30
    person_count:
      cooldown_sec: 15

rules:
  - type: danger_zone
    enabled: true
    config:
      danger_zone: [[100, 100], [500, 100], [500, 500], [100, 500]]
      threshold_sec: 3
      notify_interval_sec: 60

  - type: loitering
    enabled: true
    config:
      roi: [[120, 120], [480, 120], [480, 480], [120, 480]]
      threshold_sec: 10
      notify_interval_sec: 60

  - type: person_count
    enabled: true
    config:
      threshold: 5
      notify_interval_sec: 30
```

Alert policy behavior:

- The first event for a deduplication key is emitted immediately.
- Repeated events inside the cooldown window are suppressed and are not printed,
  saved to SQLite, or given snapshots.
- Deduplication prefers `camera_id + rule_name + track_id`, falls back to
  `camera_id + rule_name` when `track_id` is missing, and uses
  `rule_name + track_id` or `rule_name` when `camera_id` is missing.
- Rule-specific `cooldown_sec` values override `default_cooldown_sec`.

Rule behavior:

- `danger_zone`: emits `danger_zone` when a person remains inside the configured
  polygon longer than `threshold_sec`.
- `loitering`: emits `loitering` when a person remains inside the configured ROI
  for `threshold_sec`.
- `person_count`: emits `person_count` when the number of tracked people exceeds
  `threshold`.

To add another rule, create a class that extends `BaseRule`, implement
`evaluate(tracks, timestamp)`, and register its `type` in the rule loader.

List saved SQLite events as JSON lines:

```bash
python scripts/list_events.py --db-path data/events.db
```

Start the read-only saved events API:

```bash
EVENT_DB_PATH=data/events.db uvicorn api.main:app --reload
```

`EVENT_DB_PATH` is optional. If it is not set, the API reads from
`data/events.db`.

Open the saved events dashboard in a browser:

```text
http://localhost:8000/
http://localhost:8000/dashboard
```

The dashboard is server-rendered by FastAPI. It shows service status, total
event count, event count by type, and the latest saved events from the same
SQLite database used by the API. Latest events include `camera_id` and a
Snapshot column with a thumbnail when `snapshot_path` is present. Add
`?camera_id=gate_01` to show latest events for one camera. Clicking a thumbnail
opens the full-size JPEG from `GET /snapshots/{camera_id}/{filename}`. Missing
snapshot files return a 404 from the snapshot endpoint and do not prevent the
dashboard from rendering.

Example API requests:

```bash
curl http://localhost:8000/health
curl "http://localhost:8000/events?limit=25&offset=0"
curl "http://localhost:8000/events?event_type=danger_zone&limit=10"
curl "http://localhost:8000/events?camera_id=gate_01&limit=10"
curl "http://localhost:8000/events/latest?limit=5"
curl "http://localhost:8000/events/latest?camera_id=gate_01&limit=5"
curl http://localhost:8000/snapshots/gate_01/example.jpg
curl http://localhost:8000/stats
```

## Tests

GitHub Actions installs the lean unit-test dependency set from `requirements-ci.txt`.
The full local runtime stack, including OpenCV, Ultralytics, ByteTrack, and psycopg,
remains documented in `requirements.txt`.

```bash
pip install -r requirements-ci.txt
pytest
```

## Project Status

🚧 Under Active Development
