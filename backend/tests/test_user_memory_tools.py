import pytest
from unittest.mock import MagicMock
from app.db.repository import FirestoreRepository, reset_db_client
from app.tools.project_memory import get_project, update_project
from app.tools.user_memory import get_user_preferences, save_user_preference


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


def test_save_and_retrieve_user_preference_fresh_session():
    """Verify saving a preference and retrieving it in a fresh repository session."""
    user_id = "user_dev_42"

    # 1. Save explicit user preference
    save_res = save_user_preference(
        user_id=user_id,
        key="planning_style",
        value="iterative",
        category="planning",
        confidence=1.0,
        source="explicit_user_statement",
        evidence="I always prefer iterative milestones over massive upfront plans."
    )

    assert save_res["status"] == "success"
    assert save_res["preference"]["key"] == "planning_style"
    assert save_res["preference"]["confidence"] == 1.0

    # 2. Simulate fresh session / new instance retrieval
    fresh_repo = FirestoreRepository()
    fresh_prefs = fresh_repo.get_all_preferences(user_id=user_id)

    assert len(fresh_prefs) == 1
    assert fresh_prefs[0]["key"] == "planning_style"
    assert fresh_prefs[0]["value"] == "iterative"
    assert fresh_prefs[0]["evidence"] == "I always prefer iterative milestones over massive upfront plans."


def test_unwhitelisted_key_rejection():
    """Verify that arbitrary unwhitelisted keys are rejected cleanly."""
    res = save_user_preference(
        user_id="user_dev_42",
        key="arbitrary_hallucinated_key",
        value="something"
    )
    assert res["status"] == "error"
    assert "not in the allowed preference whitelist" in res["message"]


def test_trivial_statement_filtering():
    """Verify that trivial confirmations ('ok', 'sounds good', 'yes') are not saved as preferences."""
    for trivial_val in ["ok", "sounds good", "yes", "Cool", "THANKS"]:
        res = save_user_preference(
            user_id="user_dev_42",
            key="response_length",
            value=trivial_val
        )
        assert res["status"] == "error"
        assert "Refusing to save trivial confirmation" in res["message"]


def test_strict_isolation_between_project_and_user_memory():
    """
    Critical Boundary Test:
    Verify that saving project memory never leaks into user preferences,
    and saving user preferences never leaks into project memory.
    """
    user_id = "user_boundary_test"
    project_id = "proj_analytics_dashboard"

    # 1. Save Project Memory
    update_project(
        user_id=user_id,
        project_id=project_id,
        title="Analytics Dashboard",
        goal="Real-time telemetry dashboard for IoT devices",
        decisions=["Use PostgreSQL with TimescaleDB extension"]
    )

    # 2. Save User Memory
    save_user_preference(
        user_id=user_id,
        key="response_length",
        value="concise",
        category="communication",
        confidence=0.9
    )

    # 3. Retrieve User Preferences and verify NO project data is present
    user_prefs_res = get_user_preferences(user_id=user_id)
    assert user_prefs_res["status"] == "success"
    assert len(user_prefs_res["preferences"]) == 1
    assert user_prefs_res["preferences"][0]["key"] == "response_length"
    assert "goal" not in user_prefs_res["preferences"][0]
    assert "Analytics Dashboard" not in str(user_prefs_res["preferences"])

    # 4. Retrieve Project Memory and verify NO user preference data is present
    proj_res = get_project(user_id=user_id, project_id=project_id)
    assert proj_res["status"] == "success"
    project_doc = proj_res["project"]
    assert project_doc["title"] == "Analytics Dashboard"
    assert "response_length" not in project_doc
