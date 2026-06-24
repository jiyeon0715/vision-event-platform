from pathlib import Path

from app.core.config import load_settings


def write_config(config_path: Path) -> None:
    config_path.write_text(
        """
app:
  name: test-platform
  environment: test
database:
  url: postgresql://from-config/test
yolo:
  model_path: models/test-yolo.pt
  confidence_threshold: 0.75
  device: cpu
tracker:
  type: bytetrack
  max_age: 20
  min_hits: 2
event:
  danger_zone: [[0, 0], [10, 0], [10, 10], [0, 10]]
  threshold_sec: 3
  notify_interval_sec: 20
  danger_zone_threshold: 0.9
  cooldown_seconds: 15
rules:
  - type: danger_zone
    enabled: true
    config:
      danger_zone: [[0, 0], [10, 0], [10, 10], [0, 10]]
      threshold_sec: 3
      notify_interval_sec: 20
  - type: person_count
    enabled: false
    config:
      threshold: 2
      notify_interval_sec: 5
alert_policy:
  default_cooldown_sec: 10
  rules:
    danger_zone:
      cooldown_sec: 10
    loitering:
      cooldown_sec: 30
""".lstrip(),
        encoding="utf-8",
    )


def test_load_settings_from_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path)

    settings = load_settings(config_path=config_path, environ={})

    assert settings.app.name == "test-platform"
    assert settings.app.environment == "test"
    assert settings.database.url == "postgresql://from-config/test"
    assert settings.yolo.model_path == "models/test-yolo.pt"
    assert settings.yolo.confidence_threshold == 0.75
    assert settings.tracker.type == "bytetrack"
    assert settings.tracker.max_age == 20
    assert settings.event.danger_zone == (
        (0.0, 0.0),
        (10.0, 0.0),
        (10.0, 10.0),
        (0.0, 10.0),
    )
    assert settings.event.threshold_sec == 3
    assert settings.event.notify_interval_sec == 20
    assert settings.event.cooldown_seconds == 15
    assert settings.alert_policy.default_cooldown_sec == 10
    assert settings.alert_policy.rules["danger_zone"].cooldown_sec == 10
    assert settings.alert_policy.rules["loitering"].cooldown_sec == 30
    assert [rule.type for rule in settings.rules] == ["danger_zone", "person_count"]
    assert settings.rules[0].enabled is True
    assert settings.rules[0].config["threshold_sec"] == 3
    assert settings.rules[1].enabled is False
    assert settings.rules[1].config["threshold"] == 2


def test_database_url_can_be_overridden_by_environment(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    write_config(config_path)

    settings = load_settings(
        config_path=config_path,
        environ={"DATABASE_URL": "postgresql://from-env/test"},
    )

    assert settings.database.url == "postgresql://from-env/test"
