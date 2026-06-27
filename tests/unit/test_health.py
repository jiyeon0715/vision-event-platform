from fastapi.testclient import TestClient

from app.services.camera_health import camera_health_registry
from main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cameras_health_endpoint_returns_runtime_state() -> None:
    camera_health_registry.reset()
    camera_health_registry.register_camera("gate_01", "data/videos/gate_01.mp4")
    camera_health_registry.mark_frame("gate_01")
    client = TestClient(app)

    response = client.get("/cameras/health")

    camera_health_registry.reset()
    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["camera_id"] == "gate_01"
    assert payload[0]["source"] == "data/videos/gate_01.mp4"
    assert payload[0]["status"] == "online"
    assert payload[0]["last_frame_at"] is not None
    assert payload[0]["processed_frame_count"] == 1
    assert payload[0]["emitted_event_count"] == 0
