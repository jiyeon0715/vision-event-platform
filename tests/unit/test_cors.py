from fastapi.testclient import TestClient

from app.core.security import DEFAULT_CORS_ORIGINS, get_cors_origins
from main import app


def test_get_cors_origins_defaults_to_localhost_3000(monkeypatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert get_cors_origins() == DEFAULT_CORS_ORIGINS


def test_get_cors_origins_reads_comma_separated_env_var(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000, https://dashboard.example.com")

    assert get_cors_origins() == [
        "http://localhost:3000",
        "https://dashboard.example.com",
    ]


def test_cors_headers_present_for_allowed_origin() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_allows_configured_origin() -> None:
    client = TestClient(app)

    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unlisted_origin() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://evil.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
