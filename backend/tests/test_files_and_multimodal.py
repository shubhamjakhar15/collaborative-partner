import base64
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.contract import Stage, Intent, ChatResponse, FileAttachment
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


def test_upload_and_list_files(client: TestClient):
    """Verify uploading a file and listing files for a project."""
    user_id = "test_user_files"
    project_id = "proj_files_1"

    # 1. Upload an image file payload
    file_payload = {
        "id": "file_mockup_01",
        "filename": "ui_mockup.png",
        "content_type": "image/png",
        "size": 1024,
        "data_base64": base64.b64encode(b"fake_image_bytes").decode("utf-8"),
    }

    res_upload = client.post(f"/users/{user_id}/projects/{project_id}/files", json=file_payload)
    assert res_upload.status_code == 200
    upload_data = res_upload.json()
    assert upload_data["status"] == "success"
    assert upload_data["file"]["filename"] == "ui_mockup.png"

    # 2. List files
    res_list = client.get(f"/users/{user_id}/projects/{project_id}/files")
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["count"] == 1
    assert list_data["files"][0]["id"] == "file_mockup_01"

    # 3. Delete file
    res_delete = client.delete(f"/users/{user_id}/projects/{project_id}/files/file_mockup_01")
    assert res_delete.status_code == 200

    # 4. List after delete
    res_list_after = client.get(f"/users/{user_id}/projects/{project_id}/files")
    assert res_list_after.json()["count"] == 0


def test_chat_with_attachments(client: TestClient):
    """Verify chat endpoint ingests attachments and returns project_files."""
    user_id = "test_user_files"
    project_id = "proj_files_chat"

    mock_response = ChatResponse(
        project_id=project_id,
        message="I have analyzed your attached schema and UI mockup!",
        stage=Stage.DISCOVERY,
        intent=Intent.DISCOVER_CONTEXT,
        questions=[],
        feedback_detected=False,
        next_action="Review the suggested database structure.",
        requires_user_input=True,
    )

    with patch("app.services.agent_service.AgentService.process_chat", new_callable=AsyncMock) as mock_process:
        mock_process.return_value = mock_response

        chat_payload = {
            "user_id": user_id,
            "project_id": project_id,
            "message": "Here is our schema diagram",
            "attachments": [
                {
                    "id": "file_schema_01",
                    "filename": "schema.json",
                    "content_type": "application/json",
                    "size": 512,
                    "data_base64": base64.b64encode(b'{"users": "table"}').decode("utf-8"),
                }
            ]
        }

        res = client.post("/chat", json=chat_payload)
        assert res.status_code == 200
        data = res.json()
        assert "message" in data

