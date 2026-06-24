from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Sequence

from app.tracker.bytetrack_tracker import Track


@dataclass(frozen=True)
class Event:
    event_type: str
    track_id: int
    timestamp: float
    message: str
    camera_id: str = "default"


class BaseRule(ABC):
    """Base class for frame-level event rules."""

    @abstractmethod
    def evaluate(self, tracks: Sequence[Track], timestamp: float) -> list[Event]:
        """Return events emitted for the current tracked frame."""
