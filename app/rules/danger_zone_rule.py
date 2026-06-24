from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.core.config import Settings, get_settings
from app.rules.base import BaseRule, Event
from app.tracker.bytetrack_tracker import Track


Point = tuple[float, float]
Polygon = Sequence[Point]


@dataclass
class PersonState:
    track_id: int
    entered_at: float | None
    last_event_at: float | None
    is_inside: bool


class DangerZoneRule(BaseRule):
    """Evaluate tracked people against a configured danger zone polygon."""

    def __init__(
        self,
        settings: Settings | None = None,
        danger_zone: Polygon | None = None,
        threshold_sec: float | None = None,
        notify_interval_sec: float | None = None,
    ) -> None:
        event_settings = (settings or get_settings()).event
        self._danger_zone = tuple(danger_zone or event_settings.danger_zone)
        self._threshold_sec = float(
            threshold_sec
            if threshold_sec is not None
            else event_settings.threshold_sec or 0.0
        )
        self._notify_interval_sec = float(
            notify_interval_sec
            if notify_interval_sec is not None
            else event_settings.notify_interval_sec or 0.0
        )
        self._states: dict[int, PersonState] = {}

    @property
    def states(self) -> dict[int, PersonState]:
        return self._states

    def evaluate(self, tracks: Sequence[Track], timestamp: float) -> list[Event]:
        events: list[Event] = []

        for track in tracks:
            if track.label and track.label != "person":
                continue

            state = self._states.setdefault(
                track.track_id,
                PersonState(
                    track_id=track.track_id,
                    entered_at=None,
                    last_event_at=None,
                    is_inside=False,
                ),
            )
            is_inside = point_in_polygon(_bbox_center(track.bbox), self._danger_zone)

            if not is_inside:
                state.entered_at = None
                state.is_inside = False
                continue

            if not state.is_inside or state.entered_at is None:
                state.entered_at = timestamp

            state.is_inside = True
            if not self._threshold_met(state.entered_at, timestamp):
                continue

            if not self._notification_allowed(state.last_event_at, timestamp):
                continue

            state.last_event_at = timestamp
            events.append(
                Event(
                    event_type="danger_zone",
                    track_id=track.track_id,
                    timestamp=timestamp,
                    message=f"Track {track.track_id} stayed inside the danger zone.",
                )
            )

        return events

    def _threshold_met(self, entered_at: float, timestamp: float) -> bool:
        return timestamp - entered_at > self._threshold_sec

    def _notification_allowed(
        self,
        last_event_at: float | None,
        timestamp: float,
    ) -> bool:
        return (
            last_event_at is None
            or timestamp - last_event_at >= self._notify_interval_sec
        )


def _bbox_center(bbox: tuple[float, float, float, float]) -> Point:
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def point_in_polygon(point: Point, polygon: Polygon) -> bool:
    if len(polygon) < 3:
        return False

    x, y = point
    inside = False
    previous = polygon[-1]

    for current in polygon:
        x1, y1 = previous
        x2, y2 = current

        if _point_on_segment(point, previous, current):
            return True

        crosses = (y1 > y) != (y2 > y)
        if crosses:
            intersect_x = ((x2 - x1) * (y - y1) / (y2 - y1)) + x1
            if x < intersect_x:
                inside = not inside

        previous = current

    return inside


def _point_on_segment(point: Point, start: Point, end: Point) -> bool:
    x, y = point
    x1, y1 = start
    x2, y2 = end
    cross_product = (y - y1) * (x2 - x1) - (x - x1) * (y2 - y1)
    if abs(cross_product) > 1e-9:
        return False

    return (
        min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9
        and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9
    )


DangerZoneEvaluator = DangerZoneRule
