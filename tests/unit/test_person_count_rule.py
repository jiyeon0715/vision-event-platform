from __future__ import annotations

from app.rules.person_count_rule import PersonCountRule
from app.tracker.bytetrack_tracker import Track


def make_track(track_id: int, label: str = "person") -> Track:
    return Track(
        track_id=track_id,
        class_id=0,
        label=label,
        confidence=0.9,
        bbox=(0.0, 0.0, 10.0, 10.0),
    )


def test_person_count_rule_emits_when_count_exceeds_threshold() -> None:
    rule = PersonCountRule(threshold=2, notify_interval_sec=10.0)

    events = rule.evaluate(
        [make_track(1), make_track(2), make_track(3)],
        timestamp=3.0,
    )

    assert len(events) == 1
    assert events[0].event_type == "person_count"
    assert events[0].track_id == 0
    assert events[0].timestamp == 3.0
    assert events[0].message == "Person count 3 exceeded threshold 2."


def test_person_count_rule_does_not_emit_at_or_below_threshold() -> None:
    rule = PersonCountRule(threshold=2)

    assert rule.evaluate([make_track(1), make_track(2)], timestamp=1.0) == []


def test_person_count_rule_uses_notify_interval() -> None:
    rule = PersonCountRule(threshold=1, notify_interval_sec=10.0)

    assert len(rule.evaluate([make_track(1), make_track(2)], timestamp=1.0)) == 1
    assert rule.evaluate([make_track(1), make_track(2)], timestamp=5.0) == []
    assert len(rule.evaluate([make_track(1), make_track(2)], timestamp=11.0)) == 1


def test_person_count_rule_ignores_non_person_tracks() -> None:
    rule = PersonCountRule(threshold=1)

    assert rule.evaluate([make_track(1), make_track(2, label="car")], timestamp=1.0) == []
