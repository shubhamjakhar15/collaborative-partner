import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.contract import ChatRequest
from app.services.agent_service import AgentService
from app.tools.project_memory import update_project
from app.tools.user_memory import save_user_preference
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


def test_invalid_request_body_returns_standard_error_response(client: TestClient):
    """
    Failure Mode 1: Invalid request body (missing required fields / extra fields).
    Asserts a clean 422 ErrorResponse schema without raw traceback.
    """
    # 1. Missing message
    res = client.post("/chat", json={"user_id": "demo-user", "project_id": "proj-1"})
    assert res.status_code == 422
    data = res.json()
    assert data["error"] == "validation_error"
    assert "Request payload validation failed" in data["message"]
    assert data["status_code"] == 422
    assert "timestamp" in data

    # 2. Missing project_id
    res_no_proj = client.post("/chat", json={"user_id": "demo-user", "message": "Hi"})
    assert res_no_proj.status_code == 422
    assert res_no_proj.json()["error"] == "validation_error"


def test_missing_project_returns_404_error_response(client: TestClient):
    """
    Failure Mode 2: Project not found.
    Asserts a clean 404 ErrorResponse.
    """
    res = client.get("/users/demo-user/projects/non_existent_project")
    assert res.status_code == 404
    data = res.json()
    assert data["error"] == "http_error"
    assert "not found" in data["message"]
    assert data["status_code"] == 404


def test_firestore_failure_returns_sanitized_500_error_response(client: TestClient):
    """
    Failure Mode 3: Firestore database exception.
    Asserts sanitized 500 ErrorResponse without exposing internal traceback.
    """
    with patch("app.db.repository.FirestoreRepository.get_all_preferences", side_effect=Exception("Database connection timeout")):
        res = client.get("/users/demo-user/preferences")
        assert res.status_code == 500
        data = res.json()
        assert data["error"] == "http_error"
        assert "Failed to fetch user preferences" in data["message"]
        # Ensure raw traceback / internal details are NOT exposed to the client
        assert "Traceback" not in data["message"]


def test_tool_argument_validation_failures_safe_response():
    """
    Failure Mode 4: Tool argument validation failures.
    Asserts tools fail safely and return error dictionaries instead of throwing.
    """
    # 1. Empty IDs
    res_empty_user = update_project(user_id="", project_id="p1", title="Title")
    assert res_empty_user["status"] == "error"
    assert "user_id cannot be empty" in res_empty_user["message"]

    res_empty_proj = update_project(user_id="u1", project_id="", title="Title")
    assert res_empty_proj["status"] == "error"
    assert "project_id cannot be empty" in res_empty_proj["message"]

    # 2. No fields passed
    res_no_fields = update_project(user_id="u1", project_id="p1")
    assert res_no_fields["status"] == "warning"


def test_user_memory_whitelist_and_trivial_rejection():
    """
    Failure Mode 5: User memory whitelist violation & trivial confirmation rejection.
    Asserts safe rejection without database corruption.
    """
    # 1. Non-whitelisted key
    res_unwhitelisted = save_user_preference(user_id="u1", key="arbitrary_bad_key", value="val")
    assert res_unwhitelisted["status"] == "error"
    assert "not in the allowed preference whitelist" in res_unwhitelisted["message"]

    # 2. Trivial statement
    res_trivial = save_user_preference(user_id="u1", key="response_length", value="sounds good")
    assert res_trivial["status"] == "error"
    assert "Refusing to save trivial confirmation" in res_trivial["message"]


def test_llm_api_failure_graceful_recovery():
    """
    Failure Mode 6: Gemini API failure / timeout during chat turn.
    Asserts AgentService catches the failure and returns a graceful in-character fallback response.
    """
    service = AgentService()

    async def _run_test():
        with patch.object(service.runner, "run_async", side_effect=Exception("Gemini API quota exceeded")):
            req = ChatRequest(
                user_id="demo-user",
                project_id="proj-resilience",
                message="Let's build a microservice."
            )

            response = await service.process_chat(req)
            assert response.project_id == "proj-resilience"
            assert "temporary connection issue" in response.message
            assert response.stage != ""
            assert response.requires_user_input is True

    asyncio.run(_run_test())
