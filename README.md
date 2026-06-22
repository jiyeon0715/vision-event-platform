# Vision Event Platform

`vision-event-platform` is a Python-based foundation for detecting, tracking, evaluating, and serving vision events from video streams.

## Tech Stack

- Python
- OpenCV
- YOLO
- ByteTrack
- FastAPI
- PostgreSQL
- Docker
- GitHub Actions

## Current Status

This repository contains the initial project structure, placeholder modules, a basic FastAPI app, Docker configuration, and starter documentation. Model training, dashboard work, and production business logic are intentionally out of scope for this first scaffold.

## Run Locally

```bash
uvicorn main:app --reload
```

Then visit:

```text
GET http://localhost:8000/health
```
