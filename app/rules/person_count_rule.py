from __future__ import annotations

from typing import Sequence

from app.rules.base import BaseRule, Event
from app.tracker.bytetrack_tracker import Track


class PersonCountRule(BaseRule):
    """Emit an event when the number of tracked people exceeds a threshold."""

    def __init__(
        self,
        threshold: int,
        notify_interval_sec: float = 0.0,
    ) -> None:
        self._threshold = int(threshold)
        self._notify_interval_sec = float(notify_interval_sec)
        self._last_event_at: float | None = None

    @property
    def last_event_at(self) -> float | None:
        return self._last_event_at

    def evaluate(self, tracks: Sequence[Track], timestamp: float) -> list[Event]:
        person_count = sum(1 for track in tracks if not track.label or track.label == "person")
        if person_count <= self._threshold:
            return []

        if not self._notification_allowed(timestamp):
            return []

        self._last_event_at = timestamp
        return [
            Event(
                event_type="person_count",
                track_id=0,
                timestamp=timestamp,
                message=(
                    f"Person count {person_count} exceeded threshold "
                    f"{self._threshold}."
                ),
            )
        ]

    def _notification_allowed(self, timestamp: float) -> bool:
        return (
            self._last_event_at is None
            or timestamp - self._last_event_at >= self._notify_interval_sec
        )
