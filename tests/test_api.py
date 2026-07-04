"""Tests for API endpoints (integration tests requiring live services)."""

import pytest
from httpx import AsyncClient, ASGITransport


pytestmark = pytest.mark.skip(
    reason="Integration tests — requires Qdrant, Redis, Postgres running"
)


@pytest.fixture
async def client():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestChatEndpoint:
    async def test_chat_returns_response(self, client):
        response = await client.post("/api/v1/chat", json={"query": "What is Law 36?"})
        assert response.status_code in (200, 422, 401)

    async def test_chat_requires_auth(self, client):
        response = await client.post("/api/v1/chat", json={"query": "test"})
        assert response.status_code == 401

    async def test_chat_validates_input(self, client):
        response = await client.post(
            "/api/v1/chat",
            json={"query": ""},
            headers={"X-API-Key": "admin-secret-key"},
        )
        assert response.status_code == 422


class TestSuggestionsEndpoint:
    async def test_suggestions_return_questions(self, client):
        response = await client.get(
            "/api/v1/suggestions",
            headers={"X-API-Key": "admin-secret-key"},
        )
        assert response.status_code == 200


class TestFeedbackEndpoint:
    async def test_feedback_accepted(self, client):
        response = await client.post(
            "/api/v1/feedback",
            json={"session_id": "s1", "query": "test", "response": "ok", "vote": "up"},
            headers={"X-API-Key": "admin-secret-key"},
        )
        assert response.status_code == 200


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
