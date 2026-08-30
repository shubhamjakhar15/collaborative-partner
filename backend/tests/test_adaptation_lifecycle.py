import pytest
from google.genai import types
from google.adk.sessions.session import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from app.db.repository import FirestoreRepository, reset_db_client
from app.schemas.contract import Stage
from project_partner.agent import (
    before_agent_lifecycle,
    after_agent_lifecycle,
    root_agent,
)


class InMemoryDocumentRef:
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
        from unittest.mock import MagicMock
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
        from unittest.mock import MagicMock
        docs = []
        prefix = f"{self.path}/"
        for k, v in list(self.storage.items()):
            if k.startswith(prefix) and "/" not in k[len(prefix):]:
                mock_snap = MagicMock()
                mock_snap.to_dict.return_value = v.copy()
                docs.append(mock_snap)
        return docs


class InMemoryFirestoreClient:
    def __init__(self):
        self.storage: dict[str, dict] = {}

    def collection(self, col_name: str):
        return InMemoryCollectionRef(self.storage, col_name)


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    mock_client = InMemoryFirestoreClient()
    reset_db_client(mock_client)
    yield
    reset_db_client(None)


def create_mock_context(user_id: str, session_id: str, user_text: str = "") -> CallbackContext:
    session = Session(
        id=session_id,
        app_name="project_partner",
        user_id=user_id,
        state={}
    )
    service = InMemorySessionService()
    user_content = (
        types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
        if user_text
        else None
    )

    inv_ctx = InvocationContext(
        session=session,
        session_service=service,
        invocation_id=f"inv_{session_id}",
        agent=root_agent,
        user_content=user_content,
    )
    return CallbackContext(invocation_context=inv_ctx)


def test_session_1_feedback_auto_persists_to_firestore():
    """
    Session 1 Test:
    User submits reusable-preference feedback.
    Verify that before_agent_lifecycle automatically persists the preference to Firestore.
    """
    user_id = "user_hackathon_demo"
    session_id = "sess_project_1_recipe_app"
    feedback_message = "Don't give me so many tasks at once, only give me three actions at a time."

    ctx = create_mock_context(user_id=user_id, session_id=session_id, user_text=feedback_message)
    before_agent_lifecycle(ctx)

    # 1. Verify feedback detected in state
    assert ctx.state["feedback_detected"] is True
    assert "Saved user preference: max_tasks_per_phase = 3" in ctx.state["last_adaptation_event"]

    # 2. Verify persisted in Firestore
    repo = FirestoreRepository()
    saved_pref = repo.get_preference(user_id=user_id, preference_id="max_tasks_per_phase")
    assert saved_pref is not None
    assert saved_pref["value"] == 3
    assert saved_pref["category"] == "planning"


def test_session_2_new_project_preloads_learned_preferences():
    """
    Session 2 Test (Cross-Project Adaptation Demo):
    In a brand new project session, verify that the stored preference from Session 1
    is loaded into the agent's context BEFORE generating the first response.
    """
    user_id = "user_hackathon_demo"
    # Seed prior preference from Session 1
    repo = FirestoreRepository()
    repo.set_preference(
        user_id=user_id,
        preference_id="max_tasks_per_phase",
        value=3,
        category="planning",
        confidence=1.0,
        source="explicit_user_statement",
    )

    # Start Session 2 with a completely different project
    session_2_id = "sess_project_2_iot_dashboard"
    new_project_goal = "Let's plan an IoT telemetry dashboard app."

    ctx = create_mock_context(user_id=user_id, session_id=session_2_id, user_text=new_project_goal)
    before_agent_lifecycle(ctx)

    # Verify that the preference was pre-loaded into state for prompt injection
    pref_context = ctx.state.get("user_preferences_context", "")
    assert "max_tasks_per_phase: 3" in pref_context
    assert "{user_preferences_context?}" in root_agent.instruction


def test_project_specific_feedback_routes_to_project_adaptation():
    """
    Verify project-specific feedback sets stage='adaptation' and saves to project feedback collection.
    """
    user_id = "user_hackathon_demo"
    project_id = "proj_whiteboard_app"
    feedback_message = "Let's change the approach and drop Slack for this project."

    ctx = create_mock_context(user_id=user_id, session_id=project_id, user_text=feedback_message)
    before_agent_lifecycle(ctx)

    assert ctx.state["feedback_detected"] is True
    assert ctx.state["stage"] == Stage.ADAPTATION.value

    repo = FirestoreRepository()
    fb_records = repo.get_feedback_records(user_id=user_id, project_id=project_id)
    assert len(fb_records) == 1
    assert fb_records[0]["details"] == feedback_message
