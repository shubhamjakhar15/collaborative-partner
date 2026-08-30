import pytest
from unittest.mock import MagicMock
from app.db.repository import (
    FirestoreRepository,
    WHITELISTED_PREFERENCE_KEYS,
)


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


@pytest.fixture
def repo():
    mock_client = InMemoryFirestoreClient()
    return FirestoreRepository(client=mock_client)


def test_user_crud_operations(repo: FirestoreRepository):
    """Test creating, reading, and deleting a user document."""
    user_id = "test_user_001"
    profile_data = {"display_name": "Alex Developer", "role": "Fullstack"}

    # 1. Write User
    created = repo.set_user(user_id, profile_data)
    assert created["user_id"] == user_id
    assert created["display_name"] == "Alex Developer"
    assert "updated_at" in created

    # 2. Read User
    fetched = repo.get_user(user_id)
    assert fetched is not None
    assert fetched["display_name"] == "Alex Developer"

    # 3. Delete User
    repo.delete_user(user_id)
    assert repo.get_user(user_id) is None


def test_preference_whitelisting_and_crud(repo: FirestoreRepository):
    """Test preference storage with whitelist enforcement and metadata."""
    user_id = "test_user_001"

    # 1. Valid whitelisted preference
    pref = repo.set_preference(
        user_id=user_id,
        preference_id="preferred_stack",
        value="FastAPI + React",
        confidence=0.95,
        source_turn=2
    )
    assert pref["key"] == "preferred_stack"
    assert pref["value"] == "FastAPI + React"
    assert pref["confidence"] == 0.95
    assert pref["source_turn"] == 2

    # 2. Read back
    fetched_pref = repo.get_preference(user_id, "preferred_stack")
    assert fetched_pref is not None
    assert fetched_pref["value"] == "FastAPI + React"

    # 3. Invalid non-whitelisted key rejection
    with pytest.raises(ValueError) as excinfo:
        repo.set_preference(
            user_id=user_id,
            preference_id="unauthorized_arbitrary_key",
            value="malicious_data"
        )
    assert "Invalid preference key" in str(excinfo.value)

    # 4. Delete preference
    repo.delete_preference(user_id, "preferred_stack")
    assert repo.get_preference(user_id, "preferred_stack") is None


def test_project_and_nested_messages_crud(repo: FirestoreRepository):
    """Test project roadmap storage and nested message history."""
    user_id = "test_user_001"
    project_id = "proj_hackathon_99"

    # 1. Create Project
    project_data = {
        "title": "Collaborative Whiteboard",
        "stage": "planning",
        "plan_version": 1
    }
    repo.set_project(user_id, project_id, project_data)

    fetched_proj = repo.get_project(user_id, project_id)
    assert fetched_proj is not None
    assert fetched_proj["title"] == "Collaborative Whiteboard"

    # 2. Save Messages under project
    repo.save_message(
        user_id=user_id,
        project_id=project_id,
        message_id="msg_1",
        role="user",
        content="I need a real-time whiteboard app.",
        stage="discovery"
    )
    repo.save_message(
        user_id=user_id,
        project_id=project_id,
        message_id="msg_2",
        role="agent",
        content="Here are 2 clarifying questions.",
        stage="clarification"
    )

    messages = repo.get_messages(user_id, project_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "agent"

    # 3. Delete Message and Project
    repo.delete_message(user_id, project_id, "msg_1")
    remaining = repo.get_messages(user_id, project_id)
    assert len(remaining) == 1

    repo.delete_project(user_id, project_id)
    assert repo.get_project(user_id, project_id) is None


def test_feedback_logging_and_crud(repo: FirestoreRepository):
    """Test feedback and adaptation logging."""
    user_id = "test_user_001"
    project_id = "proj_hackathon_99"
    feedback_id = "fb_01"

    # 1. Save Feedback
    repo.save_feedback(
        user_id=user_id,
        project_id=project_id,
        feedback_id=feedback_id,
        feedback_type="scope_reduction",
        details="User requested removing Slack integration",
        resolution="Replaced step with local CHANGELOG.md generation"
    )

    # 2. Read back
    records = repo.get_feedback_records(user_id, project_id)
    assert len(records) == 1
    assert records[0]["feedback_type"] == "scope_reduction"
    assert records[0]["resolution"] == "Replaced step with local CHANGELOG.md generation"

    # 3. Clean up
    repo.delete_feedback(user_id, project_id, feedback_id)
    records_after = repo.get_feedback_records(user_id, project_id)
    assert len(records_after) == 0
