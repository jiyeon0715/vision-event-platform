from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from vision.inputs.base import FramePacket, FrameSource


class ImageSource(FrameSource):
    def __init__(
        self,
        image_path: Path | str,
        source_id: str,
        source_type: str = "image",
        cv2_module: Any | None = None,
    ) -> None:
        self.image_path = Path(image_path).expanduser()
        self.source_id = source_id
        self.source_type = source_type
        self._cv2 = cv2_module or self._load_cv2()
        self._frame = self._read_image()

    def __iter__(self) -> Iterator[FramePacket]:
        yield FramePacket(
            source_id=self.source_id,
            source_type=self.source_type,
            timestamp=0.0,
            frame_index=0,
            frame=self._frame,
        )

    def close(self) -> None:
        return None

    def _read_image(self) -> Any:
        if not self.image_path.is_file():
            raise FileNotFoundError(f"Image file not found: {self.image_path}")

        frame = self._cv2.imread(str(self.image_path))
        if frame is None:
            raise RuntimeError(f"Unable to read image file: {self.image_path}")

        return frame

    @staticmethod
    def _load_cv2() -> Any:
        import cv2

        return cv2
