# Vision Event Platform

A real-time vision event platform built with YOLO, ByteTrack, FastAPI, PostgreSQL, and Docker.

The goal of this project is to transform object detection results into an event-driven system that can be monitored, queried, and managed through APIs.

## Architecture

```text
Video Stream
    ↓
YOLO Detector
    ↓
ByteTrack Tracker
    ↓
Event Evaluator
    ↓
Event Service
    ↓
PostgreSQL
    ↓
FastAPI API
```

## Features

### Current

- FastAPI application
- Health check endpoint
- Project structure initialization
- Docker environment
- PostgreSQL integration skeleton
- Event processing architecture

### Planned

- YOLO object detection
- ByteTrack object tracking
- Danger zone event detection
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

```bash
uvicorn main:app --reload
```

Health Check

```text
GET http://localhost:8000/health
```

Run the local video pipeline against a video file:

```bash
python scripts/run_video.py /path/to/video.mp4
```

The runner reads frames with OpenCV, passes each frame through
`VisionEventPipeline.process_frame()`, prints any emitted events to the console,
and exits gracefully when it reaches the end of the file.

Save emitted events to a local SQLite database while still printing JSON lines:

```bash
python scripts/run_video.py /path/to/video.mp4 --save-events --db-path data/events.db
```

List saved SQLite events as JSON lines:

```bash
python scripts/list_events.py --db-path data/events.db
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
