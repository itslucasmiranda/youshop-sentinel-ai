from fastapi.testclient import TestClient

from sentinel.main import app


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_home_is_in_brazilian_portuguese() -> None:
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert 'lang="pt-BR"' in response.text


def test_interactive_reference_uses_local_assets():
    with TestClient(app) as client:
        page = client.get("/redoc")
        assert page.status_code == 200
        assert 'src="/static/swagger-ui-bundle.js"' in page.text
        assert client.get("/static/swagger-ui.css").status_code == 200
