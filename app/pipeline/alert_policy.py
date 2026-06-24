from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from app.core.config import AlertPolicySettings


@dataclass
class AlertPolicy:
    """Throttle duplicate rule events before persistence and snapshots."""

    default_cooldown_sec: float = 0.0
    rule_cooldowns: Mapping[str, float] = field(default_factory=dict)
    _last_emitted_at: dict[tuple[tuple[str, str], ...], float] = field(
        init=False,
        default_factory=dict,
    )

    @classmethod
    def from_settings(cls, settings: AlertPolicySettings) -> "AlertPolicy":
        return cls(
            default_cooldown_sec=settings.default_cooldown_sec,
            rule_cooldowns={
                rule_name: rule_settings.cooldown_sec
                for rule_name, rule_settings in settings.rules.items()
                if rule_settings.cooldown_sec is not None
            },
        )

    def filter_events(self, events: list[Any]) -> list[Any]:
        return [event for event in events if self.should_emit(event)]

    def should_emit(self, event: Any) -> bool:
        rule_name = _event_value(event, "rule_name") or _event_value(
            event,
            "event_type",
        )
        if rule_name is None:
            return True

        timestamp = _event_value(event, "timestamp")
        if timestamp is None:
            return True

        cooldown_sec = float(
            self.rule_cooldowns.get(str(rule_name), self.default_cooldown_sec)
        )
        if cooldown_sec <= 0:
            return True

        dedupe_key = _dedupe_key(
            rule_name=str(rule_name),
            camera_id=_event_value(event, "camera_id"),
            track_id=_event_value(event, "track_id"),
        )
        event_time = float(timestamp)
        last_emitted_at = self._last_emitted_at.get(dedupe_key)
        if (
            last_emitted_at is not None
            and event_time - last_emitted_at < cooldown_sec
        ):
            return False

        self._last_emitted_at[dedupe_key] = event_time
        return True

    def __post_init__(self) -> None:
        self.default_cooldown_sec = float(self.default_cooldown_sec)
        self.rule_cooldowns = {
            rule_name: float(cooldown_sec)
            for rule_name, cooldown_sec in self.rule_cooldowns.items()
        }


def _dedupe_key(
    rule_name: str,
    camera_id: Any | None,
    track_id: Any | None,
) -> tuple[tuple[str, str], ...]:
    parts = []
    if camera_id is not None:
        parts.append(("camera_id", str(camera_id)))

    parts.append(("rule_name", rule_name))

    if track_id is not None:
        parts.append(("track_id", str(track_id)))

    return tuple(parts)


def _event_value(event: Any, key: str) -> Any | None:
    if isinstance(event, Mapping):
        return event.get(key)

    return getattr(event, key, None)
