# API

This document will describe the platform API.

## Health

`GET /health`

Returns a basic health check response.

`GET /health/db`

Returns database connectivity status and the active backend.

Response:

```json
{
  "status": "ok",
  "backend": "postgresql"
}
```

Returns `503` when the database cannot be reached.

## Events

### `GET /events`

Returns recent events ordered by creation time, newest first.

Query parameters:

- `page`: Page number to return. Defaults to `1`.
- `limit`: Maximum number of events to return. Defaults to `100`; allowed range is `1` to `500`.
- `camera_id`: Optional camera id filter.
- `event_type`: Optional event type filter.
- `severity`: Optional severity filter.
- `status`: Optional dashboard workflow status filter.
- `date_from`: Optional inclusive created-at lower bound.
- `date_to`: Optional inclusive created-at upper bound.
- `start_at` / `end_at`: Backward-compatible aliases for `date_from` / `date_to`.

Response:

```json
{
  "items": [
    {
      "id": 1,
      "event_type": "danger_zone",
      "camera_id": "gate_01",
      "track_id": 42,
      "timestamp": 123.45,
      "message": "Track 42 stayed inside the danger zone.",
      "severity": "critical",
      "status": "new",
      "created_at": "2026-06-22T10:30:00Z"
    }
  ],
  "page": 1,
  "limit": 100,
  "total": 1,
  "total_pages": 1
}
```

### `GET /events/latest`

Returns the latest persisted events ordered by creation time, newest first.
Defaults to `limit=10`; allowed range is `1` to `500`.
Accepts the same optional `camera_id` filter as `GET /events`.

### `GET /events/{event_id}`

Returns a single event by id.

Response:

```json
{
  "id": 1,
  "event_type": "danger_zone",
  "camera_id": "gate_01",
  "track_id": 42,
  "timestamp": 123.45,
  "message": "Track 42 stayed inside the danger zone.",
  "created_at": "2026-06-22T10:30:00Z"
}
```

Returns `404` with `{"detail": "Event not found"}` when the event does not exist.

### `GET /events/stats`

Returns aggregate event counts for dashboard summary views.

Query parameters:

- `camera_id`: Optional camera id filter.
- `event_type`: Optional event type filter.
- `rule_name`: Backward-compatible alias for event type.
- `severity`: Optional severity filter.
- `status`: Optional dashboard workflow status filter.
- `date_from`: Optional inclusive created-at lower bound.
- `date_to`: Optional inclusive created-at upper bound.

Response:

```json
{
  "total_event_count": 10,
  "event_count_by_type": {
    "danger_zone": 6,
    "loitering": 4
  },
  "event_count_by_rule_name": {
    "danger_zone": 6,
    "loitering": 4
  },
  "event_count_by_camera_id": {
    "gate_01": 7,
    "gate_02": 3
  },
  "event_count_by_status": {
    "new": 8,
    "acknowledged": 2
  },
  "hourly_event_counts": {
    "2026-06-22T10:00:00": 10
  },
  "latest_event_timestamp": "2026-06-22T10:30:00Z"
}
```
