from __future__ import annotations

import json
import os
from datetime import datetime, time, timezone
from html import escape
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse

from app.core.security import add_security_headers, docs_config, require_api_key
from app.services.camera_health import camera_health_registry
from storage.event_repository import EventRepository

DEFAULT_DB_PATH = Path("data/events.db")
DEFAULT_SNAPSHOT_DIR = Path("data/snapshots")

app = FastAPI(title="Vision Events API", **docs_config())
add_security_headers(app)


def get_db_path() -> Path:
    return Path(os.environ.get("EVENT_DB_PATH", DEFAULT_DB_PATH))


def get_snapshot_dir() -> Path:
    return Path(os.environ.get("SNAPSHOT_DIR", DEFAULT_SNAPSHOT_DIR))


def get_event_repository(
    db_path: Annotated[Path, Depends(get_db_path)],
) -> EventRepository:
    return EventRepository(db_path)


@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    db_path: Annotated[Path, Depends(get_db_path)],
    repository: Annotated[EventRepository, Depends(get_event_repository)],
    camera_id: str | None = None,
) -> HTMLResponse:
    service_status = health(db_path)["status"].upper()
    event_stats = repository.stats(camera_id=camera_id)
    today_stats = repository.stats(start_at=_today_start_utc(), camera_id=camera_id)
    camera_health_rows = cameras_health()
    events = latest_events(repository, limit=10, camera_id=camera_id)

    return HTMLResponse(
        _render_dashboard(
            service_status=service_status,
            db_path=db_path,
            camera_id=camera_id,
            today_event_count=today_stats["total_event_count"],
            event_count_by_rule_name=event_stats["event_count_by_rule_name"],
            event_count_by_camera_id=event_stats["event_count_by_camera_id"],
            latest_event_timestamp=event_stats["latest_event_timestamp"],
            camera_health_rows=camera_health_rows,
            latest_event_rows=events,
        )
    )


@app.get("/health")
def health(db_path: Annotated[Path, Depends(get_db_path)]) -> dict[str, str]:
    return {
        "status": "ok",
        "db_path": str(db_path),
    }


@app.get("/events", dependencies=[Depends(require_api_key)])
def list_events(
    repository: Annotated[EventRepository, Depends(get_event_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    event_type: str | None = None,
    camera_id: str | None = None,
) -> list[dict]:
    events = repository.list_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        camera_id=camera_id,
    )
    return [_format_event(event) for event in events]


@app.get("/events/latest", dependencies=[Depends(require_api_key)])
def latest_events(
    repository: Annotated[EventRepository, Depends(get_event_repository)],
    limit: Annotated[int, Query(ge=1, le=500)] = 10,
    camera_id: str | None = None,
) -> list[dict]:
    events = repository.list_latest_events(limit=limit, camera_id=camera_id)
    return [_format_event(event) for event in events]


@app.get("/stats", dependencies=[Depends(require_api_key)])
@app.get("/events/stats", dependencies=[Depends(require_api_key)])
def event_stats_summary(
    repository: Annotated[EventRepository, Depends(get_event_repository)],
    start_at: str | None = None,
    end_at: str | None = None,
    camera_id: str | None = None,
    rule_name: str | None = None,
) -> dict:
    return repository.stats(
        start_at=start_at,
        end_at=end_at,
        camera_id=camera_id,
        rule_name=rule_name,
    )


@app.get("/cameras/health", dependencies=[Depends(require_api_key)])
def cameras_health() -> list[dict]:
    return [
        {
            "camera_id": health.camera_id,
            "source": health.source,
            "status": health.status,
            "last_frame_at": _format_optional_datetime(health.last_frame_at),
            "last_event_at": _format_optional_datetime(health.last_event_at),
            "processed_frame_count": health.processed_frame_count,
            "emitted_event_count": health.emitted_event_count,
            "last_error": health.last_error,
        }
        for health in camera_health_registry.list_health()
    ]


@app.get("/snapshots/{snapshot_path:path}")
def get_snapshot(
    snapshot_path: str,
    snapshot_dir: Annotated[Path, Depends(get_snapshot_dir)],
) -> FileResponse:
    resolved_snapshot_path = _resolve_snapshot_path(snapshot_dir, snapshot_path)
    if not resolved_snapshot_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )

    return FileResponse(resolved_snapshot_path, media_type="image/jpeg")


def _format_event(event: dict) -> dict:
    readable_event = {
        "id": event["id"],
        "event_type": event["event_type"],
        "camera_id": event["camera_id"],
        "track_id": event["track_id"],
        "timestamp": event["timestamp"],
        "created_at": event["created_at"],
        "payload": _parse_payload(event["payload_json"]),
    }
    if event.get("snapshot_path") is not None:
        readable_event["snapshot_path"] = event["snapshot_path"]
    return readable_event


def _parse_payload(payload_json: str) -> dict:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return {"raw": payload_json}

    if isinstance(payload, dict):
        return payload

    return {"value": payload}


def _render_dashboard(
    service_status: str,
    db_path: Path,
    camera_id: str | None,
    today_event_count: int,
    event_count_by_rule_name: dict[str, int],
    event_count_by_camera_id: dict[str, int],
    latest_event_timestamp: str | None,
    camera_health_rows: list[dict],
    latest_event_rows: list[dict],
) -> str:
    rule_rows = _render_count_rows(event_count_by_rule_name, "rule_name")
    camera_rows = _render_count_rows(event_count_by_camera_id, "camera_id")
    health_rows = _render_camera_health_rows(camera_health_rows)
    event_rows = _render_latest_event_rows(latest_event_rows)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vision Events Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --background: #f7f8fa;
      --panel: #ffffff;
      --border: #d8dde6;
      --text: #1f2937;
      --muted: #667085;
      --accent: #1d4ed8;
      --success: #0f7a4f;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      background: var(--background);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}

    main {{
      width: min(1100px, calc(100% - 32px));
      margin: 32px auto;
    }}

    header {{
      margin-bottom: 24px;
    }}

    h1, h2 {{
      margin: 0;
    }}

    h1 {{
      font-size: 28px;
    }}

    h2 {{
      font-size: 18px;
      margin-bottom: 12px;
    }}

    .subtitle {{
      margin: 6px 0 0;
      color: var(--muted);
    }}

    .summary {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }}

    .card, .section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}

    .label {{
      color: var(--muted);
      font-size: 13px;
      margin: 0 0 6px;
    }}

    .value {{
      font-size: 28px;
      font-weight: 700;
      margin: 0;
    }}

    .status {{
      color: var(--success);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}

    .section {{
      margin-top: 16px;
      overflow-x: auto;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 720px;
    }}

    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}

    th {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
      background: #fbfcfe;
    }}

    tr:last-child td {{
      border-bottom: 0;
    }}

    .empty {{
      color: var(--muted);
      margin: 0;
    }}

    .db-path {{
      color: var(--muted);
      font-size: 13px;
      word-break: break-all;
    }}

    .filter-form {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: end;
    }}

    .filter-field {{
      display: grid;
      gap: 4px;
    }}

    .filter-field label {{
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}

    .filter-field input {{
      border: 1px solid var(--border);
      border-radius: 6px;
      font: inherit;
      padding: 8px 10px;
    }}

    .filter-form button, .filter-form a {{
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      padding: 8px 12px;
      text-decoration: none;
    }}

    .filter-form a {{
      background: #fff;
      color: var(--accent);
    }}

    .snapshot-link {{
      display: inline-flex;
      border: 1px solid var(--border);
      border-radius: 4px;
      overflow: hidden;
      background: #fff;
    }}

    .snapshot-thumb {{
      width: 88px;
      height: 56px;
      object-fit: cover;
      display: block;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Vision Events Dashboard</h1>
      <p class="subtitle">Saved SQLite vision events</p>
    </header>

    <section class="summary" aria-label="Service summary">
      <div class="card">
        <p class="label">Service status</p>
        <p class="value status">{_html(service_status)}</p>
      </div>
      <div class="card">
        <p class="label">Today total events</p>
        <p class="value">{today_event_count}</p>
      </div>
      <div class="card">
        <p class="label">Recent event time</p>
        <p class="db-path">{_html(latest_event_timestamp or "No events yet")}</p>
      </div>
      <div class="card">
        <p class="label">Camera filter</p>
        <p class="db-path">{_html(camera_id or "all cameras")}</p>
      </div>
      <div class="card">
        <p class="label">SQLite database</p>
        <p class="db-path">{_html(str(db_path))}</p>
      </div>
    </section>

    <section class="section">
      <h2>Events By Rule</h2>
      {rule_rows}
    </section>

    <section class="section">
      <h2>Events By Camera</h2>
      {camera_rows}
    </section>

    <section class="section">
      <h2>Camera Health</h2>
      {health_rows}
    </section>

    <section class="section">
      <h2>Latest Events</h2>
      {_render_camera_filter(camera_id)}
      {event_rows}
    </section>
  </main>
</body>
</html>"""


def _render_count_rows(counts: dict[str, int], label: str) -> str:
    if not counts:
        return '<p class="empty">No saved events yet.</p>'

    rows = "\n".join(
        f"<tr><td>{_html(name)}</td><td>{count}</td></tr>"
        for name, count in counts.items()
    )
    return f"""<table>
  <thead>
    <tr>
      <th>{_html(label)}</th>
      <th>count</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


def _render_camera_health_rows(camera_health_rows: list[dict]) -> str:
    if not camera_health_rows:
        return '<p class="empty">No runtime camera health reported yet.</p>'

    rows = "\n".join(
        f"""<tr>
      <td>{_html(row["camera_id"])}</td>
      <td>{_html(row.get("source") or "")}</td>
      <td>{_html(row["status"])}</td>
      <td>{_html(row.get("last_frame_at") or "")}</td>
      <td>{_html(row.get("last_event_at") or "")}</td>
      <td>{row["processed_frame_count"]}</td>
      <td>{row["emitted_event_count"]}</td>
      <td>{_html(row.get("last_error") or "")}</td>
    </tr>"""
        for row in camera_health_rows
    )
    return f"""<table>
  <thead>
    <tr>
      <th>camera_id</th>
      <th>source</th>
      <th>status</th>
      <th>last_frame_at</th>
      <th>last_event_at</th>
      <th>frames</th>
      <th>events</th>
      <th>last_error</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


def _render_latest_event_rows(events: list[dict]) -> str:
    if not events:
        return '<p class="empty">No latest events to show.</p>'

    rows = "\n".join(
        f"""<tr>
      <td>{event["id"]}</td>
      <td>{_html(event["event_type"])}</td>
      <td>{_html(event["camera_id"])}</td>
      <td>{_html(event["track_id"])}</td>
      <td>{_html(event["timestamp"])}</td>
      <td>{_render_snapshot_cell(event.get("snapshot_path"))}</td>
      <td>{_html(event["created_at"])}</td>
    </tr>"""
        for event in events
    )
    return f"""<table>
  <thead>
    <tr>
      <th>id</th>
      <th>event_type</th>
      <th>camera_id</th>
      <th>track_id</th>
      <th>timestamp</th>
      <th>Snapshot</th>
      <th>created_at</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>"""


def _render_camera_filter(camera_id: str | None) -> str:
    return f"""<form class="filter-form" method="get" action="/dashboard">
  <div class="filter-field">
    <label for="camera_id">camera_id</label>
    <input id="camera_id" name="camera_id" value="{_html(camera_id or "")}">
  </div>
  <button type="submit">Filter</button>
  <a href="/dashboard">Clear</a>
</form>"""


def _render_snapshot_cell(snapshot_path: object) -> str:
    if not snapshot_path:
        return '<span class="empty">Missing</span>'

    relative_path = _snapshot_url_path(Path(str(snapshot_path)))
    if not relative_path:
        return '<span class="empty">Missing</span>'

    snapshot_url = f"/snapshots/{quote(relative_path)}"
    escaped_url = _html(snapshot_url)
    return (
        f'<a class="snapshot-link" href="{escaped_url}" target="_blank" '
        f'rel="noopener noreferrer">'
        f'<img class="snapshot-thumb" src="{escaped_url}" alt="Event snapshot">'
        "</a>"
    )


def _html(value: object) -> str:
    return escape(str(value))


def _today_start_utc() -> str:
    return datetime.combine(
        datetime.now(timezone.utc).date(),
        time.min,
        tzinfo=timezone.utc,
    ).isoformat()


def _format_optional_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _snapshot_url_path(snapshot_path: Path) -> str:
    snapshot_dir = get_snapshot_dir()
    try:
        return snapshot_path.relative_to(snapshot_dir).as_posix()
    except ValueError:
        return snapshot_path.name


def _resolve_snapshot_path(snapshot_dir: Path, snapshot_path: str) -> Path:
    requested_path = Path(snapshot_path)
    if requested_path.is_absolute() or ".." in requested_path.parts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )

    candidate = snapshot_dir.joinpath(*requested_path.parts)
    resolved_dir = snapshot_dir.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_candidate == resolved_dir or resolved_dir not in resolved_candidate.parents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not found",
        )
    return resolved_candidate
