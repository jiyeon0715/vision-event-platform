from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass(frozen=True)
class FramePacket:
    source_id: str
    source_type: str
    timestamp: float
    frame_index: int
    frame: Any


class FrameSource(ABC):
    source_id: str
    source_type: str

    @abstractmethod
    def __iter__(self) -> Iterator[FramePacket]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> "FrameSource":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
