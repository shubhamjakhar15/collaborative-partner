import pytest
from google.adk.sessions.session import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.callback_context import CallbackContext
from app.db.repository import reset_db_client
from tests.test_adaptation_lifecycle import InMemoryFirestoreClient
from app.schemas.contract import Stage
from project_partner.agent import (
    before_agent_lifecycle,
    after_agent_lifecycle,
    root_agent,
)


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    mock_client = InMemoryFirestoreClient()
    reset_db_client(mock_client)
    yield
    reset_db_client(None)


def create_mock_callback_context(initial_state: dict | None = None) -> CallbackContext:
    """Helper factory creating an authentic ADK CallbackContext for testing."""
    session = Session(
        id="test_session_1",
        app_name="project_partner",
        user_id="user_123",
        state=initial_state or {}
    )
    service = InMemorySessionService()
    inv_context = InvocationContext(
        session=session,
        session_service=service,
        invocation_id="inv_test_1",
        agent=root_agent
    )
    return CallbackContext(invocation_context=inv_context)


def test_session_state_initialization():
    """Verify that before_agent_lifecycle initializes session state keys."""
    context = create_mock_callback_context(initial_state={})

    before_agent_lifecycle(context)

    # Verify session-scoped keys
    assert context.state["stage"] == Stage.DISCOVERY.value
    assert context.state["turn_count"] == 1
    assert "user_preferences_context" in context.state


def test_turn_counter_increment():
    """Verify that multiple turns increment the turn_count correctly."""
    context = create_mock_callback_context(
        initial_state={"stage": Stage.DISCOVERY.value, "turn_count": 1}
    )

    before_agent_lifecycle(context)
    assert context.state["turn_count"] == 2


def test_state_progression_lifecycle():
    """Verify that after_agent_lifecycle transitions stages across multi-turn flow."""
    # Turn 1: Discovery -> Clarification
    context = create_mock_callback_context(
        initial_state={"stage": Stage.DISCOVERY.value, "turn_count": 1}
    )
    after_agent_lifecycle(context)
    assert context.state["stage"] == Stage.CLARIFICATION.value

    # Turn 2: Clarification -> Planning
    context.state["turn_count"] = 2
    after_agent_lifecycle(context)
    assert context.state["stage"] == Stage.PLANNING.value

    # Turn 3: Planning -> Review
    context.state["turn_count"] = 3
    after_agent_lifecycle(context)
    assert context.state["stage"] == Stage.REVIEW.value


def test_scoped_state_key_semantics():
    """Verify scoped key prefixes behavior."""
    initial_state = {
        "stage": Stage.DISCOVERY.value,            # session-scoped
        "user:preferred_stack": "FastAPI + React", # user-scoped
        "app:build_version": "1.0.0",             # app-scoped
        "temp:scratch_flag": True                 # temporary
    }

    context = create_mock_callback_context(initial_state=initial_state)
    before_agent_lifecycle(context)

    assert context.state["user:preferred_stack"] == "FastAPI + React"
    assert context.state["app:build_version"] == "1.0.0"
    assert context.state["temp:scratch_flag"] is True
    assert context.state["turn_count"] == 1


def test_agent_template_instruction_contains_state_placeholders():
    """Verify that root_agent instruction has the required ADK state template placeholders."""
    assert "{stage?}" in root_agent.instruction
    assert "{turn_count?}" in root_agent.instruction
    assert "{user_preferences_context?}" in root_agent.instruction
