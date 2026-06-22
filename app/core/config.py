from __future__ import annotations

import os
from dataclasses import dataclass
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
class Settings:
    app: AppSettings
    database: DatabaseSettings
    yolo: YoloSettings
    tracker: TrackerSettings
    event: EventSettings


def _read_yaml(config_path: Path) -> Mapping[str, Any]:
    with config_path.open("r", encoding="utf-8") as config_file:
        if yaml is not None:
            config_data = yaml.safe_load(config_file) or {}
        else:
            config_data = _read_simple_yaml(config_file.read())

    if not isinstance(config_data, Mapping):
        raise ValueError(f"Configuration file must contain a mapping: {config_path}")

    return config_data


def _read_simple_yaml(config_text: str) -> dict[str, dict[str, Any]]:
    config_data: dict[str, dict[str, Any]] = {}
    current_section: str | None = None

    for line in config_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if not line.startswith(" "):
            current_section = line.rstrip(":")
            config_data[current_section] = {}
            continue

        if current_section is None:
            raise ValueError("Configuration values must be nested under a section")

        key, value = line.strip().split(":", maxsplit=1)
        config_data[current_section][key] = _parse_scalar(value.strip())

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
        event=EventSettings(**_section(config_data, "event")),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
