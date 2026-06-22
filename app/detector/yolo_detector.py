from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from app.core.config import Settings, get_settings

PERSON_CLASS_ID = 0
PERSON_LABEL = "person"


@dataclass(frozen=True)
class Detection:
    class_id: int
    label: str
    confidence: float
    bbox: tuple[float, float, float, float]


class YoloModel(Protocol):
    def predict(self, source: object, **kwargs: object) -> Sequence[object]:
        ...


ModelFactory = Callable[[str], YoloModel]


class YoloDetector:
    """YOLO detector wrapper for person detections."""

    def __init__(
        self,
        settings: Settings | None = None,
        model_factory: ModelFactory | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._model = self._load_model(model_factory)

    def detect(self, frame: object) -> list[Detection]:
        results = self._model.predict(
            source=frame,
            conf=self._settings.yolo.confidence_threshold,
            device=self._settings.yolo.device,
            classes=[PERSON_CLASS_ID],
            verbose=False,
        )

        detections: list[Detection] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            xyxy_values = _to_python(getattr(boxes, "xyxy", []))
            confidence_values = _to_python(getattr(boxes, "conf", []))
            class_values = _to_python(getattr(boxes, "cls", []))

            for bbox, confidence, class_id in zip(
                xyxy_values,
                confidence_values,
                class_values,
                strict=False,
            ):
                normalized_class_id = int(class_id)
                if normalized_class_id != PERSON_CLASS_ID:
                    continue

                detections.append(
                    Detection(
                        class_id=normalized_class_id,
                        label=PERSON_LABEL,
                        confidence=float(confidence),
                        bbox=_normalize_bbox(bbox),
                    )
                )

        return detections

    def _load_model(self, model_factory: ModelFactory | None) -> YoloModel:
        if model_factory is not None:
            return model_factory(self._settings.yolo.model_path)

        try:
            from ultralytics import YOLO
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "ultralytics is required to load the YOLO detector model"
            ) from exc

        return YOLO(self._settings.yolo.model_path)


def _to_python(value: Any) -> Any:
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def _normalize_bbox(value: object) -> tuple[float, float, float, float]:
    coordinates = list(value)  # type: ignore[arg-type]
    if len(coordinates) != 4:
        raise ValueError("YOLO bbox must contain exactly four coordinates")

    return tuple(float(coordinate) for coordinate in coordinates)  # type: ignore[return-value]

