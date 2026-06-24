from __future__ import annotations

from app.core.config import (
    AppSettings,
    DatabaseSettings,
    EventSettings,
    RuleSettings,
    Settings,
    TrackerSettings,
    YoloSettings,
)
from app.rules.danger_zone_rule import DangerZoneRule
from app.rules.loader import load_rules
from app.rules.loitering_rule import LoiteringRule
from app.rules.person_count_rule import PersonCountRule


def make_settings(rules: tuple[RuleSettings, ...]) -> Settings:
    return Settings(
        app=AppSettings(name="test", environment="test"),
        database=DatabaseSettings(url="sqlite://"),
        yolo=YoloSettings(
            model_path="models/test.pt",
            confidence_threshold=0.5,
            device="cpu",
        ),
        tracker=TrackerSettings(type="bytetrack", max_age=30, min_hits=3),
        event=EventSettings(
            danger_zone=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0)),
            threshold_sec=3,
            notify_interval_sec=20,
        ),
        rules=rules,
    )


def test_load_rules_builds_enabled_rules_from_settings() -> None:
    settings = make_settings(
        (
            RuleSettings(
                type="danger_zone",
                config={
                    "danger_zone": [[0, 0], [10, 0], [10, 10]],
                    "threshold_sec": 3,
                    "notify_interval_sec": 20,
                },
            ),
            RuleSettings(
                type="loitering",
                config={
                    "roi": [[0, 0], [10, 0], [10, 10]],
                    "threshold_sec": 5,
                    "notify_interval_sec": 30,
                },
            ),
            RuleSettings(
                type="person_count",
                config={"threshold": 2, "notify_interval_sec": 10},
            ),
        )
    )

    rules = load_rules(settings)

    assert [type(rule) for rule in rules] == [
        DangerZoneRule,
        LoiteringRule,
        PersonCountRule,
    ]


def test_load_rules_skips_disabled_rules() -> None:
    settings = make_settings(
        (
            RuleSettings(
                type="person_count",
                enabled=False,
                config={"threshold": 2},
            ),
        )
    )

    assert load_rules(settings) == []


def test_load_rules_falls_back_to_legacy_danger_zone_settings() -> None:
    settings = make_settings(())

    rules = load_rules(settings)

    assert len(rules) == 1
    assert isinstance(rules[0], DangerZoneRule)
