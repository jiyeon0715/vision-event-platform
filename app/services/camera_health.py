from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


CameraStatus = str


@dataclass(frozen=True)
class CameraHealth:
    camera_id: str
    source: str | None
    status: CameraStatus
    last_frame_at: datetime | None
    last_event_at: datetime | None
    processed_frame_count: int
    emitted_event_count: int
    last_error: str | None = None


@dataclass
class _MutableCameraHealth:
    camera_id: str
    source: str | None = None
    status: CameraStatus = "unknown"
    last_frame_at: datetime | None = None
    last_event_at: datetime | None = None
    processed_frame_count: int = 0
    emitted_event_count: int = 0
    last_error: str | None = None

    def snapshot(self) -> CameraHealth:
        return CameraHealth(
            camera_id=self.camera_id,
            source=self.source,
            status=self.status,
            last_frame_at=self.last_frame_at,
            last_event_at=self.last_event_at,
            processed_frame_count=self.processed_frame_count,
            emitted_event_count=self.emitted_event_count,
            last_error=self.last_error,
        )


class CameraHealthRegistry:
    """Track current per-camera runtime health in memory."""

    def __init__(self) -> None:
        self._cameras: dict[str, _MutableCameraHealth] = {}
        self._lock = Lock()

    def register_camera(self, camera_id: str, source: str | None = None) -> None:
        with self._lock:
            health = self._cameras.get(camera_id)
            if health is None:
                self._cameras[camera_id] = _MutableCameraHealth(
                    camera_id=camera_id,
                    source=source,
                )
                return

            if source is not None:
                health.source = source

    def mark_frame(
        self,
        camera_id: str,
        source: str | None = None,
        captured_at: datetime | None = None,
    ) -> None:
        now = captured_at or _utc_now()
        with self._lock:
            health = self._get_or_create(camera_id)
            if source is not None:
                health.source = source
            health.status = "online"
            health.last_frame_at = now
            health.processed_frame_count += 1
            health.last_error = None

    def mark_events(
        self,
        camera_id: str,
        count: int,
        source: str | None = None,
        emitted_at: datetime | None = None,
    ) -> None:
        if count <= 0:
            return

        now = emitted_at or _utc_now()
        with self._lock:
            health = self._get_or_create(camera_id)
            if source is not None:
                health.source = source
            health.status = "online"
            health.last_event_at = now
            health.emitted_event_count += count

    def mark_error(
        self,
        camera_id: str,
        error: str,
        source: str | None = None,
    ) -> None:
        with self._lock:
            health = self._get_or_create(camera_id)
            if source is not None:
                health.source = source
            health.status = "offline"
            health.last_error = error

    def mark_offline(self, camera_id: str, source: str | None = None) -> None:
        with self._lock:
            health = self._get_or_create(camera_id)
            if source is not None:
                health.source = source
            health.status = "offline"

    def list_health(self) -> list[CameraHealth]:
        with self._lock:
            return [
                health.snapshot()
                for health in sorted(
                    self._cameras.values(),
                    key=lambda camera: camera.camera_id,
                )
            ]

    def reset(self) -> None:
        with self._lock:
            self._cameras.clear()

    def _get_or_create(self, camera_id: str) -> _MutableCameraHealth:
        health = self._cameras.get(camera_id)
        if health is None:
            health = _MutableCameraHealth(camera_id=camera_id)
            self._cameras[camera_id] = health
        return health


camera_health_registry = CameraHealthRegistry()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)
