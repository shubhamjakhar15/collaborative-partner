import pytest
from unittest.mock import MagicMock
from app.db.repository import FirestoreRepository, reset_db_client
from app.tools.project_memory import get_project, update_project


class InMemoryDocumentRef:
    """Mock document reference storing data in an in-memory dictionary."""
    def __init__(self, storage: dict, path: str):
        self.storage = storage
        self.path = path

    def set(self, data: dict, merge: bool = False):
        if merge and self.path in self.storage:
            self.storage[self.path].update(data)
        else:
            self.storage[self.path] = data.copy()

    def get(self):
        exists = self.path in self.storage
        data = self.storage.get(self.path, {})
        mock_snapshot = MagicMock()
        mock_snapshot.exists = exists
        mock_snapshot.to_dict.return_value = data.copy() if exists else None
        return mock_snapshot

    def delete(self):
        if self.path in self.storage:
            del self.storage[self.path]

    def collection(self, col_name: str):
        return InMemoryCollectionRef(self.storage, f"{self.path}/{col_name}")


class InMemoryCollectionRef:
    """Mock collection reference routing document paths."""
    def __init__(self, storage: dict, path: str):
        self.storage = storage
        self.path = path

    def document(self, doc_id: str):
        return InMemoryDocumentRef(self.storage, f"{self.path}/{doc_id}")

    def order_by(self, field: str, direction=None):
        return self

    def limit(self, count: int):
        return self

    def stream(self):
        docs = []
        prefix = f"{self.path}/"
        for k, v in list(self.storage.items()):
            if k.startswith(prefix) and "/" not in k[len(prefix):]:
                mock_snap = MagicMock()
                mock_snap.to_dict.return_value = v.copy()
                docs.append(mock_snap)
        return docs


class InMemoryFirestoreClient:
    """Mock Firestore client providing full in-memory tree storage for tests."""
    def __init__(self):
        self.storage: dict[str, dict] = {}

    def collection(self, col_name: str):
        return InMemoryCollectionRef(self.storage, col_name)


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    """Inject an in-memory client for all tool tests and clean up afterwards."""
    mock_client = InMemoryFirestoreClient()
    reset_db_client(mock_client)
    yield
    reset_db_client(None)


def test_get_nonexistent_project_fails_safely():
    """Verify get_project returns 'not_found' without crashing."""
    result = get_project(user_id="user_123", project_id="proj_nonexistent")
    assert result["status"] == "not_found"
    assert result["project"] is None
    assert "was not found" in result["message"]


def test_create_and_read_project_memory_via_tools():
    """Verify creating a project memory via update_project and reading it back."""
    user_id = "user_hackathon"
    project_id = "proj_whiteboard"

    # 1. Initialize project memory
    create_result = update_project(
        user_id=user_id,
        project_id=project_id,
        title="Real-time Whiteboard",
        goal="Collaborative diagramming tool for remote engineers",
        target_user="Software architects & engineering teams",
        constraints=["FastAPI", "Canvas API", "48h deadline"],
        deadline="Sunday 12:00 PM",
        decisions=["Use WebSockets for cursor sync", "No heavy canvas frameworks"],
        current_stage="clarification",
    )

    assert create_result["status"] == "success"
    assert create_result["project"]["goal"] == "Collaborative diagramming tool for remote engineers"

    # 2. Retrieve project memory via get_project
    read_result = get_project(user_id=user_id, project_id=project_id)
    assert read_result["status"] == "success"
    assert read_result["project"]["title"] == "Real-time Whiteboard"
    assert len(read_result["project"]["constraints"]) == 3
    assert len(read_result["project"]["decisions"]) == 2
    assert read_result["project"]["current_stage"] == "clarification"


def test_update_plan_and_stage_partial_modification():
    """Verify updating the plan preserves existing constraints and metadata."""
    user_id = "user_hackathon"
    project_id = "proj_whiteboard"

    # 1. Seed initial project
    update_project(
        user_id=user_id,
        project_id=project_id,
        title="Whiteboard MVP",
        constraints=["FastAPI", "WebSockets"],
    )

    # 2. Update only plan and stage
    new_plan = {
        "title": "3-Step Implementation Plan",
        "steps": [
            {"id": "step_1", "description": "Build WebSocket server", "status": "completed"},
            {"id": "step_2", "description": "Implement Canvas frontend", "status": "in_progress"},
            {"id": "step_3", "description": "Deploy to Cloud Run", "status": "pending"},
        ],
        "version": 1,
    }

    update_result = update_project(
        user_id=user_id,
        project_id=project_id,
        current_plan=new_plan,
        completed_tasks=["step_1"],
        current_stage="planning",
    )

    assert update_result["status"] == "success"

    # 3. Verify that constraints remain intact while plan and completed_tasks are updated
    fetched = get_project(user_id=user_id, project_id=project_id)
    project = fetched["project"]
    assert project["constraints"] == ["FastAPI", "WebSockets"]
    assert project["current_stage"] == "planning"
    assert project["completed_tasks"] == ["step_1"]
    assert len(project["current_plan"]["steps"]) == 3


def test_tool_validation_errors():
    """Verify that empty user_id or project_id returns error status without crashing."""
    res_empty_user = update_project(user_id="", project_id="proj_1", title="Test")
    assert res_empty_user["status"] == "error"

    res_empty_proj = update_project(user_id="user_1", project_id="", title="Test")
    assert res_empty_proj["status"] == "error"

    res_no_fields = update_project(user_id="user_1", project_id="proj_1")
    assert res_no_fields["status"] == "warning"
