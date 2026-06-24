from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.rules.base import BaseRule, Event
from app.rules.danger_zone_rule import Polygon, _bbox_center, point_in_polygon
from app.tracker.bytetrack_tracker import Track


@dataclass
class LoiteringState:
    track_id: int
    entered_at: float | None
    last_event_at: float | None
    is_inside: bool


class LoiteringRule(BaseRule):
    """Emit an event when a person stays inside an ROI long enough."""

    def __init__(
        self,
        roi: Polygon,
        threshold_sec: float,
        notify_interval_sec: float = 0.0,
    ) -> None:
        self._roi = tuple(roi)
        self._threshold_sec = float(threshold_sec)
        self._notify_interval_sec = float(notify_interval_sec)
        self._states: dict[int, LoiteringState] = {}

    @property
    def states(self) -> dict[int, LoiteringState]:
        return self._states

    def evaluate(self, tracks: Sequence[Track], timestamp: float) -> list[Event]:
        events: list[Event] = []

        for track in tracks:
            if track.label and track.label != "person":
                continue

            state = self._states.setdefault(
                track.track_id,
                LoiteringState(
                    track_id=track.track_id,
                    entered_at=None,
                    last_event_at=None,
                    is_inside=False,
                ),
            )
            is_inside = point_in_polygon(_bbox_center(track.bbox), self._roi)

            if not is_inside:
                state.entered_at = None
                state.is_inside = False
                continue

            if not state.is_inside or state.entered_at is None:
                state.entered_at = timestamp

            state.is_inside = True
            if timestamp - state.entered_at < self._threshold_sec:
                continue

            if not self._notification_allowed(state.last_event_at, timestamp):
                continue

            state.last_event_at = timestamp
            events.append(
                Event(
                    event_type="loitering",
                    track_id=track.track_id,
                    timestamp=timestamp,
                    message=f"Track {track.track_id} stayed inside the ROI.",
                )
            )

        return events

    def _notification_allowed(
        self,
        last_event_at: float | None,
        timestamp: float,
    ) -> bool:
        return (
            last_event_at is None
            or timestamp - last_event_at >= self._notify_interval_sec
        )
