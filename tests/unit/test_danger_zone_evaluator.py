from __future__ import annotations

from app.rules.danger_zone_evaluator import DangerZoneEvaluator
from app.tracker.bytetrack_tracker import Track


DANGER_ZONE = ((0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0))


def make_evaluator() -> DangerZoneEvaluator:
    return DangerZoneEvaluator(
        danger_zone=DANGER_ZONE,
        threshold_sec=5.0,
        notify_interval_sec=10.0,
    )


def make_track(
    track_id: int = 1,
    bbox: tuple[float, float, float, float] = (40.0, 40.0, 60.0, 60.0),
) -> Track:
    return Track(
        track_id=track_id,
        class_id=0,
        label="person",
        confidence=0.9,
        bbox=bbox,
    )


def test_person_outside_zone_does_not_emit_event() -> None:
    evaluator = make_evaluator()
    track = make_track(bbox=(140.0, 140.0, 160.0, 160.0))

    assert evaluator.evaluate([track], timestamp=0.0) == []

    state = evaluator.states[track.track_id]
    assert state.entered_at is None
    assert state.is_inside is False


def test_person_enters_zone_but_threshold_is_not_met() -> None:
    evaluator = make_evaluator()
    track = make_track()

    assert evaluator.evaluate([track], timestamp=10.0) == []
    assert evaluator.evaluate([track], timestamp=14.0) == []

    state = evaluator.states[track.track_id]
    assert state.entered_at == 10.0
    assert state.last_event_at is None
    assert state.is_inside is True


def test_person_stays_inside_longer_than_threshold_sec() -> None:
    evaluator = make_evaluator()
    track = make_track(track_id=12)

    assert evaluator.evaluate([track], timestamp=1.0) == []
    events = evaluator.evaluate([track], timestamp=7.0)

    assert len(events) == 1
    assert events[0].event_type == "danger_zone"
    assert events[0].track_id == 12
    assert events[0].timestamp == 7.0
    assert evaluator.states[12].last_event_at == 7.0


def test_repeated_events_are_blocked_by_notify_interval_sec() -> None:
    evaluator = make_evaluator()
    track = make_track()

    assert evaluator.evaluate([track], timestamp=0.0) == []
    assert len(evaluator.evaluate([track], timestamp=6.0)) == 1

    assert evaluator.evaluate([track], timestamp=12.0) == []
    assert evaluator.states[track.track_id].last_event_at == 6.0


def test_event_can_be_emitted_again_after_notify_interval_sec() -> None:
    evaluator = make_evaluator()
    track = make_track()

    assert evaluator.evaluate([track], timestamp=0.0) == []
    assert len(evaluator.evaluate([track], timestamp=6.0)) == 1
    events = evaluator.evaluate([track], timestamp=16.0)

    assert len(events) == 1
    assert events[0].track_id == track.track_id
    assert events[0].timestamp == 16.0
    assert evaluator.states[track.track_id].last_event_at == 16.0


def test_state_resets_when_person_leaves_zone() -> None:
    evaluator = make_evaluator()
    inside_track = make_track()
    outside_track = make_track(bbox=(140.0, 140.0, 160.0, 160.0))

    assert evaluator.evaluate([inside_track], timestamp=0.0) == []
    assert evaluator.evaluate([outside_track], timestamp=3.0) == []

    state = evaluator.states[inside_track.track_id]
    assert state.entered_at is None
    assert state.is_inside is False

    assert evaluator.evaluate([inside_track], timestamp=4.0) == []
    assert evaluator.evaluate([inside_track], timestamp=8.0) == []
    assert len(evaluator.evaluate([inside_track], timestamp=10.0)) == 1
    assert evaluator.states[inside_track.track_id].entered_at == 4.0
