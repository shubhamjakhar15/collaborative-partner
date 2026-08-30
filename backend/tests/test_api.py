import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.contract import Stage, Intent, ChatResponse
from app.db.repository import FirestoreRepository, reset_db_client
from tests.test_adaptation_lifecycle import InMemoryFirestoreClient


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    mock_client = InMemoryFirestoreClient()
    reset_db_client(mock_client)
    yield
    reset_db_client(None)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client: TestClient):
    """Verify GET /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_endpoint_valid_request(client: TestClient):
    """Verify POST /chat accepts ChatRequest and returns valid ChatResponse."""
    mock_response = ChatResponse(
        project_id="project-001",
        message="I'm ready to help! What type of AI code review bot do you want to build?",
        stage=Stage.DISCOVERY,
        intent=Intent.DISCOVER_CONTEXT,
        questions=[],
        feedback_detected=False,
        next_action="Awaiting user domain and requirements.",
        requires_user_input=True,
    )

    with patch("app.services.agent_service.AgentService.process_chat", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_response

        payload = {
            "user_id": "demo-user",
            "project_id": "project-001",
            "message": "I want to build an AI code review bot."
        }

        response = client.post("/chat", json=payload)
        assert response.status_code == 200

        data = response.json()
        assert data["project_id"] == "project-001"
        assert "message" in data
        assert data["stage"] == "discovery"
        assert data["intent"] == "discover_context"
        assert data["feedback_detected"] is False
        assert data["requires_user_input"] is True


def test_chat_endpoint_invalid_payload_rejected(client: TestClient):
    """Verify POST /chat returns 422 Unprocessable Entity on missing required fields."""
    response = client.post("/chat", json={"user_id": "demo-user", "message": "Hello"})
    assert response.status_code == 422


def test_get_user_preferences_endpoint(client: TestClient):
    """Verify GET /users/{user_id}/preferences returns persisted user preferences."""
    repo = FirestoreRepository()
    repo.set_preference(
        user_id="user_test_99",
        preference_id="max_tasks_per_phase",
        value=3,
        category="planning",
        confidence=1.0,
        source="explicit_user_statement"
    )

    response = client.get("/users/user_test_99/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["count"] == 1
    assert data["preferences"][0]["key"] == "max_tasks_per_phase"
    assert data["preferences"][0]["value"] == 3


def test_get_project_endpoint_found_and_not_found(client: TestClient):
    """Verify GET /users/{user_id}/projects/{project_id} returns project and handles 404."""
    user_id = "user_test_99"
    project_id = "proj_whiteboard"

    # 1. 404 Not Found before creation
    res_404 = client.get(f"/users/{user_id}/projects/{project_id}")
    assert res_404.status_code == 404

    # 2. Seed project and messages
    repo = FirestoreRepository()
    repo.set_project(
        user_id=user_id,
        project_id=project_id,
        data={
            "title": "Real-time Whiteboard",
            "goal": "Collaborative canvas for remote engineers",
            "current_stage": "planning"
        }
    )
    repo.save_message(
        user_id=user_id,
        project_id=project_id,
        message_id="msg_1",
        role="user",
        content="Hello!",
        stage="discovery"
    )

    # 3. 200 OK after creation with message history
    res_200 = client.get(f"/users/{user_id}/projects/{project_id}?include_messages=true")
    assert res_200.status_code == 200
    data = res_200.json()
    assert data["status"] == "success"
    assert data["project"]["title"] == "Real-time Whiteboard"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "Hello!"


def test_list_user_projects_endpoint(client: TestClient):
    """Verify GET /users/{user_id}/projects returns user's projects."""
    user_id = "user_list_test"
    repo = FirestoreRepository()
    repo.set_project(user_id, "proj_1", {"title": "App 1"})
    repo.set_project(user_id, "proj_2", {"title": "App 2"})

    response = client.get(f"/users/{user_id}/projects")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["projects"]) == 2
