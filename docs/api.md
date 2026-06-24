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

- `limit`: Maximum number of events to return. Defaults to `100`; allowed range is `1` to `500`.

Response:

```json
[
  {
    "id": 1,
    "event_type": "danger_zone",
    "track_id": 42,
    "timestamp": 123.45,
    "message": "Track 42 stayed inside the danger zone.",
    "created_at": "2026-06-22T10:30:00Z"
  }
]
```

### `GET /events/latest`

Returns the latest persisted events ordered by creation time, newest first.
Defaults to `limit=10`; allowed range is `1` to `500`.

### `GET /events/{event_id}`

Returns a single event by id.

Response:

```json
{
  "id": 1,
  "event_type": "danger_zone",
  "track_id": 42,
  "timestamp": 123.45,
  "message": "Track 42 stayed inside the danger zone.",
  "created_at": "2026-06-22T10:30:00Z"
}
```

Returns `404` with `{"detail": "Event not found"}` when the event does not exist.
