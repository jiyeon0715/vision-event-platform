from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.api.routes import get_camera_repository
from app.schemas.cameras import CameraCreate, CameraUpdate
from main import app


@dataclass(frozen=True)
class FakeCamera:
    id: int
    name: str
    source_type: str
    source_uri: str
    location: str | None
    status: str
    last_seen_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FakeCameraRepository:
    def __init__(self, cameras: list[FakeCamera] | None = None) -> None:
        self.cameras = cameras or []
        self.next_id = max((camera.id for camera in self.cameras), default=0) + 1

    def create(self, camera: CameraCreate) -> FakeCamera:
        now = datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc)
        values = _schema_values(camera, exclude_unset=False)
        created = FakeCamera(
            id=self.next_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        self.next_id += 1
        self.cameras.append(created)
        return created

    def list_cameras(
        self,
        page: int = 1,
        limit: int = 100,
        status: str | None = None,
        source_type: str | None = None,
    ) -> dict[str, object]:
        cameras = self.cameras
        if status is not None:
            cameras = [camera for camera in cameras if camera.status == status]
        if source_type is not None:
            cameras = [
                camera for camera in cameras if camera.source_type == source_type
            ]
        start = (page - 1) * limit
        return {"items": cameras[start : start + limit], "total": len(cameras)}

    def get_by_id(self, camera_id: int) -> FakeCamera | None:
        return next((camera for camera in self.cameras if camera.id == camera_id), None)

    def update(self, camera_id: int, camera: CameraUpdate) -> FakeCamera | None:
        existing = self.get_by_id(camera_id)
        if existing is None:
            return None

        values = _schema_values(camera, exclude_unset=True)
        updated = replace(
            existing,
            updated_at=datetime(2026, 7, 7, 10, 5, tzinfo=timezone.utc),
            **values,
        )
        self.cameras = [
            updated if camera.id == camera_id else camera for camera in self.cameras
        ]
        return updated

    def deactivate(self, camera_id: int) -> FakeCamera | None:
        existing = self.get_by_id(camera_id)
        if existing is None:
            return None

        updated = replace(
            existing,
            status="inactive",
            updated_at=datetime(2026, 7, 7, 10, 10, tzinfo=timezone.utc),
        )
        self.cameras = [
            updated if camera.id == camera_id else camera for camera in self.cameras
        ]
        return updated


def make_camera(camera_id: int = 1, status: str = "active") -> FakeCamera:
    now = datetime(2026, 7, 7, 10, 0, tzinfo=timezone.utc)
    return FakeCamera(
        id=camera_id,
        name="Gate 01",
        source_type="rtsp",
        source_uri="rtsp://example.test/gate-01",
        location="North gate",
        status=status,
        last_seen_at=None,
        created_at=now,
        updated_at=now,
    )


def make_client(repository: FakeCameraRepository) -> TestClient:
    app.dependency_overrides[get_camera_repository] = lambda: repository
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_KEY", raising=False)


@pytest.fixture(autouse=True)
def clear_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def test_create_camera() -> None:
    repository = FakeCameraRepository()
    client = make_client(repository)

    response = client.post(
        "/cameras",
        json={
            "name": "Gate 01",
            "source_type": "rtsp",
            "source_uri": "rtsp://example.test/gate-01",
            "location": "North gate",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["name"] == "Gate 01"
    assert response.json()["status"] == "active"


def test_list_cameras() -> None:
    repository = FakeCameraRepository(
        [make_camera(camera_id=1), make_camera(camera_id=2, status="inactive")]
    )
    client = make_client(repository)

    response = client.get("/cameras?status=active")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [camera["id"] for camera in response.json()["items"]] == [1]


def test_get_camera_detail() -> None:
    repository = FakeCameraRepository([make_camera(camera_id=7)])
    client = make_client(repository)

    response = client.get("/cameras/7")

    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["source_type"] == "rtsp"


def test_update_camera() -> None:
    repository = FakeCameraRepository([make_camera(camera_id=1)])
    client = make_client(repository)

    response = client.patch(
        "/cameras/1",
        json={"name": "Updated Gate", "status": "error"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Gate"
    assert response.json()["status"] == "error"


def test_get_missing_camera_returns_404() -> None:
    repository = FakeCameraRepository()
    client = make_client(repository)

    response = client.get("/cameras/404")

    assert response.status_code == 404
    assert response.json() == {"detail": "Camera not found"}


def test_delete_camera_marks_inactive() -> None:
    repository = FakeCameraRepository([make_camera(camera_id=1)])
    client = make_client(repository)

    response = client.delete("/cameras/1")

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert repository.get_by_id(1).status == "inactive"


def _schema_values(
    schema: CameraCreate | CameraUpdate,
    exclude_unset: bool,
) -> dict[str, object]:
    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_unset=exclude_unset)
    return schema.dict(exclude_unset=exclude_unset)
