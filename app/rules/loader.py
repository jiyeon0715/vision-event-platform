from __future__ import annotations

from collections.abc import Mapping
from ast import literal_eval
from typing import Any

from app.core.config import RuleSettings, Settings, get_settings
from app.rules.base import BaseRule
from app.rules.danger_zone_rule import DangerZoneRule
from app.rules.loitering_rule import LoiteringRule
from app.rules.person_count_rule import PersonCountRule


def load_rules(settings: Settings | None = None) -> list[BaseRule]:
    resolved_settings = settings or get_settings()
    if not resolved_settings.rules:
        return [DangerZoneRule(settings=resolved_settings)]

    return [
        _build_rule(rule_config)
        for rule_config in resolved_settings.rules
        if rule_config.enabled
    ]


def _build_rule(rule_config: RuleSettings) -> BaseRule:
    config = rule_config.config

    if rule_config.type == "danger_zone":
        return DangerZoneRule(
            danger_zone=_required_polygon(config, "danger_zone"),
            threshold_sec=_required_float(config, "threshold_sec"),
            notify_interval_sec=_optional_float(config, "notify_interval_sec", 0.0),
        )

    if rule_config.type == "loitering":
        return LoiteringRule(
            roi=_required_polygon(config, "roi"),
            threshold_sec=_required_float(config, "threshold_sec"),
            notify_interval_sec=_optional_float(config, "notify_interval_sec", 0.0),
        )

    if rule_config.type == "person_count":
        return PersonCountRule(
            threshold=_required_int(config, "threshold"),
            notify_interval_sec=_optional_float(config, "notify_interval_sec", 0.0),
        )

    raise ValueError(f"Unsupported rule type: {rule_config.type}")


def _required_polygon(
    config: Mapping[str, Any],
    key: str,
) -> tuple[tuple[float, float], ...]:
    value = _required_value(config, key)
    if isinstance(value, str):
        value = literal_eval(value)

    points = []
    for point in value:
        x, y = point
        points.append((float(x), float(y)))
    return tuple(points)


def _required_float(config: Mapping[str, Any], key: str) -> float:
    return float(_required_value(config, key))


def _optional_float(config: Mapping[str, Any], key: str, default: float) -> float:
    return float(config.get(key, default))


def _required_int(config: Mapping[str, Any], key: str) -> int:
    return int(_required_value(config, key))


def _required_value(config: Mapping[str, Any], key: str) -> Any:
    if key not in config:
        raise ValueError(f"Rule configuration is missing required key: {key}")
    return config[key]
