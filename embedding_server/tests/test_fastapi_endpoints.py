"""Tests FastAPI endpoints."""

from http import HTTPStatus

from fastapi.testclient import TestClient

from embedding_server.server import app


def test_ready() -> None:
    """Tests /ready endpoint."""
    with TestClient(app) as client:
        response = client.get("/ready")
        assert response.status_code == HTTPStatus.OK


def test_insert() -> None:
    """Tests /insert endpoint."""
    with TestClient(app) as client:
        response = client.post(
            "/insert",
            json={
                "text": "Spam and eggs is a delicious breakfast.",
                "test_db": "unit_test",
            },
        )
        assert response.status_code == HTTPStatus.OK
