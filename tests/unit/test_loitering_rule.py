from __future__ import annotations

from app.rules.loitering_rule import LoiteringRule
from app.tracker.bytetrack_tracker import Track


ROI = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))


def make_track(
    track_id: int = 1,
    bbox: tuple[float, float, float, float] = (40.0, 40.0, 60.0, 60.0),
    label: str = "person",
) -> Track:
    return Track(
        track_id=track_id,
        class_id=0,
        label=label,
        confidence=0.9,
        bbox=bbox,
    )


def test_loitering_rule_emits_after_person_stays_inside_roi() -> None:
    rule = LoiteringRule(roi=ROI, threshold_sec=5.0, notify_interval_sec=10.0)
    track = make_track(track_id=7)

    assert rule.evaluate([track], timestamp=1.0) == []
    events = rule.evaluate([track], timestamp=6.0)

    assert len(events) == 1
    assert events[0].event_type == "loitering"
    assert events[0].track_id == 7
    assert events[0].timestamp == 6.0
    assert events[0].message == "Track 7 stayed inside the ROI."


def test_loitering_rule_resets_when_person_leaves_roi() -> None:
    rule = LoiteringRule(roi=ROI, threshold_sec=5.0, notify_interval_sec=10.0)
    inside_track = make_track()
    outside_track = make_track(bbox=(140.0, 140.0, 160.0, 160.0))

    assert rule.evaluate([inside_track], timestamp=1.0) == []
    assert rule.evaluate([outside_track], timestamp=3.0) == []
    assert rule.evaluate([inside_track], timestamp=4.0) == []
    assert rule.evaluate([inside_track], timestamp=8.0) == []


def test_loitering_rule_ignores_non_person_tracks() -> None:
    rule = LoiteringRule(roi=ROI, threshold_sec=0.0)

    assert rule.evaluate([make_track(label="car")], timestamp=1.0) == []
    assert rule.states == {}
