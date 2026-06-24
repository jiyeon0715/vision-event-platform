from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from ast import literal_eval
from typing import Any, Mapping

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "config.yaml"
DATABASE_URL_ENV = "DATABASE_URL"


@dataclass(frozen=True)
class AppSettings:
    name: str
    environment: str


@dataclass(frozen=True)
class DatabaseSettings:
    url: str


@dataclass(frozen=True)
class YoloSettings:
    model_path: str
    confidence_threshold: float
    device: str


@dataclass(frozen=True)
class TrackerSettings:
    type: str
    max_age: int
    min_hits: int


@dataclass(frozen=True)
class CameraSettings:
    id: str
    source: str


@dataclass(frozen=True)
class EventSettings:
    danger_zone: tuple[tuple[float, float], ...] | str = ()
    threshold_sec: float | None = None
    notify_interval_sec: float | None = None
    danger_zone_threshold: float | None = None
    cooldown_seconds: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "danger_zone", _normalize_polygon(self.danger_zone))
        if self.threshold_sec is None:
            object.__setattr__(
                self,
                "threshold_sec",
                float(self.danger_zone_threshold or 0.0),
            )
        if self.notify_interval_sec is None:
            object.__setattr__(
                self,
                "notify_interval_sec",
                float(self.cooldown_seconds or 0.0),
            )


@dataclass(frozen=True)
class RuleSettings:
    type: str
    enabled: bool = True
    config: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "config", dict(self.config or {}))


@dataclass(frozen=True)
class AlertPolicyRuleSettings:
    cooldown_sec: float | None = None


@dataclass(frozen=True)
class AlertPolicySettings:
    default_cooldown_sec: float = 0.0
    rules: Mapping[str, AlertPolicyRuleSettings] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parsed_rules = {}
        for rule_name, rule_config in (self.rules or {}).items():
            if isinstance(rule_config, AlertPolicyRuleSettings):
                parsed_rules[rule_name] = rule_config
            elif isinstance(rule_config, Mapping):
                parsed_rules[rule_name] = AlertPolicyRuleSettings(**rule_config)
            else:
                raise ValueError(
                    "Each alert policy rule configuration must be a mapping"
                )

        object.__setattr__(
            self,
            "default_cooldown_sec",
            float(self.default_cooldown_sec),
        )
        object.__setattr__(self, "rules", parsed_rules)


@dataclass(frozen=True)
class Settings:
    app: AppSettings
    database: DatabaseSettings
    yolo: YoloSettings
    tracker: TrackerSettings
    event: EventSettings
    cameras: tuple[CameraSettings, ...] = ()
    alert_policy: AlertPolicySettings = field(default_factory=AlertPolicySettings)
    rules: tuple[RuleSettings, ...] = ()


def _read_yaml(config_path: Path) -> Mapping[str, Any]:
    with config_path.open("r", encoding="utf-8") as config_file:
        if yaml is not None:
            config_data = yaml.safe_load(config_file) or {}
        else:
            config_data = _read_simple_yaml(config_file.read())

    if not isinstance(config_data, Mapping):
        raise ValueError(f"Configuration file must contain a mapping: {config_path}")

    return config_data


def _read_simple_yaml(config_text: str) -> dict[str, Any]:
    lines = [
        (len(line) - len(line.lstrip(" ")), line.strip())
        for line in config_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    def parse_mapping(index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(lines):
            current_indent, text = lines[index]
            if current_indent < indent or text.startswith("- "):
                break
            if current_indent > indent:
                raise ValueError("Invalid indentation in configuration file")

            key, value = text.split(":", maxsplit=1)
            value = value.strip()
            index += 1
            if value:
                result[key] = _parse_scalar(value)
                continue

            if index >= len(lines) or lines[index][0] <= current_indent:
                result[key] = {}
                continue

            next_indent, next_text = lines[index]
            if next_text.startswith("- "):
                result[key], index = parse_list(index, next_indent)
            else:
                result[key], index = parse_mapping(index, next_indent)

        return result, index

    def parse_list(index: int, indent: int) -> tuple[list[dict[str, Any]], int]:
        result: list[dict[str, Any]] = []
        while index < len(lines):
            current_indent, text = lines[index]
            if current_indent < indent:
                break
            if current_indent != indent or not text.startswith("- "):
                raise ValueError("Invalid list item in configuration file")

            item: dict[str, Any] = {}
            content = text[2:].strip()
            index += 1
            if content:
                key, value = content.split(":", maxsplit=1)
                item[key] = _parse_scalar(value.strip())

            while index < len(lines) and lines[index][0] > indent:
                nested_indent = lines[index][0]
                nested, index = parse_mapping(index, nested_indent)
                item.update(nested)

            result.append(item)

        return result, index

    config_data, index = parse_mapping(0, 0)
    if index != len(lines):
        raise ValueError("Unable to parse configuration file")

    return config_data


def _parse_scalar(value: str) -> Any:
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        return value


def _normalize_polygon(value: object) -> tuple[tuple[float, float], ...]:
    if isinstance(value, str):
        value = literal_eval(value)

    points = []
    for point in value:  # type: ignore[union-attr]
        x, y = point
        points.append((float(x), float(y)))

    return tuple(points)


def _section(config_data: Mapping[str, Any], section_name: str) -> Mapping[str, Any]:
    section = config_data.get(section_name)

    if not isinstance(section, Mapping):
        raise ValueError(f"Missing or invalid configuration section: {section_name}")

    return section


def _rules(config_data: Mapping[str, Any]) -> tuple[RuleSettings, ...]:
    rules = config_data.get("rules", ())
    if rules in (None, ()):
        return ()
    if not isinstance(rules, list):
        raise ValueError("Configuration section must be a list: rules")

    parsed_rules = []
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise ValueError("Each rule configuration must be a mapping")
        parsed_rules.append(RuleSettings(**rule))

    return tuple(parsed_rules)


def _alert_policy(config_data: Mapping[str, Any]) -> AlertPolicySettings:
    alert_policy = config_data.get("alert_policy", {})
    if alert_policy in (None, {}):
        return AlertPolicySettings()
    if not isinstance(alert_policy, Mapping):
        raise ValueError("Configuration section must be a mapping: alert_policy")

    return AlertPolicySettings(**alert_policy)


def _cameras(config_data: Mapping[str, Any]) -> tuple[CameraSettings, ...]:
    cameras = config_data.get("cameras", ())
    if cameras in (None, ()):
        return ()
    if not isinstance(cameras, list):
        raise ValueError("Configuration section must be a list: cameras")

    parsed_cameras = []
    seen_ids: set[str] = set()
    for camera in cameras:
        if not isinstance(camera, Mapping):
            raise ValueError("Each camera configuration must be a mapping")
        parsed_camera = CameraSettings(**camera)
        if parsed_camera.id in seen_ids:
            raise ValueError(f"Duplicate camera id in configuration: {parsed_camera.id}")
        seen_ids.add(parsed_camera.id)
        parsed_cameras.append(parsed_camera)

    return tuple(parsed_cameras)


def load_settings(
    config_path: Path = CONFIG_PATH,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    env = environ if environ is not None else os.environ
    config_data = _read_yaml(config_path)

    database_config = dict(_section(config_data, "database"))
    if database_url := env.get(DATABASE_URL_ENV):
        database_config["url"] = database_url

    return Settings(
        app=AppSettings(**_section(config_data, "app")),
        database=DatabaseSettings(**database_config),
        yolo=YoloSettings(**_section(config_data, "yolo")),
        tracker=TrackerSettings(**_section(config_data, "tracker")),
        cameras=_cameras(config_data),
        event=EventSettings(**_section(config_data, "event")),
        alert_policy=_alert_policy(config_data),
        rules=_rules(config_data),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
