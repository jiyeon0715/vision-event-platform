from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from vision.inputs.base import FramePacket, FrameSource


class VideoFileSource(FrameSource):
    def __init__(
        self,
        video_path: Path | str,
        source_id: str,
        source_type: str = "video_file",
        cv2_module: Any | None = None,
    ) -> None:
        self.video_path = Path(video_path).expanduser()
        self.source_id = source_id
        self.source_type = source_type
        self._cv2 = cv2_module or self._load_cv2()
        self._capture: Any | None = None
        self._fps = 0.0
        self._open()

    def __iter__(self) -> Iterator[FramePacket]:
        frame_index = 0
        while self._capture is not None:
            ok, frame = self._capture.read()
            if not ok:
                break

            yield FramePacket(
                source_id=self.source_id,
                source_type=self.source_type,
                timestamp=self._frame_timestamp(frame_index),
                frame_index=frame_index,
                frame=frame,
            )
            frame_index += 1

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def _open(self) -> None:
        if not self.video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

        capture = self._cv2.VideoCapture(str(self.video_path))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"Unable to open video file: {self.video_path}")

        self._capture = capture
        self._fps = float(capture.get(self._cv2.CAP_PROP_FPS) or 0.0)

    def _frame_timestamp(self, frame_index: int) -> float:
        if self._capture is None:
            return float(frame_index)

        timestamp_msec = self._capture.get(self._cv2.CAP_PROP_POS_MSEC)
        if timestamp_msec > 0:
            return float(timestamp_msec) / 1000.0

        if self._fps > 0:
            return frame_index / self._fps

        return float(frame_index)

    @staticmethod
    def _load_cv2() -> Any:
        import cv2

        return cv2
