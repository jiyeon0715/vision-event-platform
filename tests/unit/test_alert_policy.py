from app.pipeline.alert_policy import AlertPolicy


def make_event(
    timestamp: float,
    event_type: str = "danger_zone",
    track_id: int | None = 42,
    camera_id: str | None = "camera-1",
) -> dict[str, object]:
    event: dict[str, object] = {
        "event_type": event_type,
        "timestamp": timestamp,
    }
    if track_id is not None:
        event["track_id"] = track_id
    if camera_id is not None:
        event["camera_id"] = camera_id

    return event


def test_first_event_is_emitted() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0)) is True


def test_repeated_event_within_cooldown_is_suppressed() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0)) is True
    assert policy.should_emit(make_event(timestamp=5.0)) is False


def test_event_after_cooldown_is_emitted() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0)) is True
    assert policy.should_emit(make_event(timestamp=11.0)) is True


def test_different_rule_names_do_not_suppress_each_other() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0, event_type="danger_zone")) is True
    assert policy.should_emit(make_event(timestamp=2.0, event_type="loitering")) is True


def test_different_track_ids_do_not_suppress_each_other() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0, track_id=42)) is True
    assert policy.should_emit(make_event(timestamp=2.0, track_id=43)) is True


def test_rule_specific_cooldown_overrides_default_cooldown() -> None:
    policy = AlertPolicy(
        default_cooldown_sec=10,
        rule_cooldowns={"loitering": 30},
    )

    assert policy.should_emit(make_event(timestamp=1.0, event_type="loitering")) is True
    assert policy.should_emit(make_event(timestamp=20.0, event_type="loitering")) is False
    assert policy.should_emit(make_event(timestamp=31.0, event_type="loitering")) is True


def test_missing_track_id_uses_camera_and_rule_name() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0, track_id=None)) is True
    assert policy.should_emit(make_event(timestamp=2.0, track_id=None)) is False
    assert (
        policy.should_emit(
            make_event(timestamp=2.0, track_id=None, camera_id="camera-2")
        )
        is True
    )


def test_missing_camera_id_uses_rule_name_and_track_id() -> None:
    policy = AlertPolicy(default_cooldown_sec=10)

    assert policy.should_emit(make_event(timestamp=1.0, camera_id=None)) is True
    assert policy.should_emit(make_event(timestamp=2.0, camera_id=None)) is False
    assert (
        policy.should_emit(
            make_event(timestamp=2.0, camera_id=None, track_id=43)
        )
        is True
    )
