import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from google.genai import types
from google.adk.events.event import Event
from app.db.repository import FirestoreRepository, reset_db_client
from app.schemas.contract import (
    Stage,
    Intent,
    ChatRequest,
    ChatResponse,
    Plan,
    PlanStep,
    StepStatus,
)
from app.services.agent_service import AgentService
from app.tools.project_memory import get_project, update_project
from app.tools.user_memory import get_user_preferences, save_user_preference
from project_partner.agent import root_agent, before_agent_lifecycle
from tests.test_adaptation_lifecycle import InMemoryFirestoreClient, create_mock_context


@pytest.fixture(autouse=True)
def setup_in_memory_db():
    """Provides a fresh in-memory Firestore client for every test in the suite."""
    mock_client = InMemoryFirestoreClient()
    reset_db_client(mock_client)
    yield
    reset_db_client(None)


def create_agent_service_with_mock_runner(simulated_text: str = "Response text", plan_to_inject: Plan | None = None) -> AgentService:
    """Helper to instantiate AgentService with deterministic LLM streaming simulation."""
    service = AgentService()

    async def mock_run_async(*args, **kwargs):
        # Yield a single event with the simulated response text
        content = types.Content(
            role="model",
            parts=[types.Part.from_text(text=simulated_text)],
        )
        yield Event(content=content)

    service.runner.run_async = mock_run_async
    return service


# =============================================================================
# SCENARIO 1: Vague Goal -> Clarification
# =============================================================================
@pytest.mark.unit
def test_scenario_1_vague_goal_clarification():
    """
    Scenario 1: Given a vague goal ('I want to build an AI app'), the agent
    must initialize in Stage.DISCOVERY and transition to Stage.CLARIFICATION.
    """
    user_id = "user_demo"
    session_id = "proj_vague_goal"
    vague_message = "I want to build an AI app."

    ctx = create_mock_context(user_id=user_id, session_id=session_id, user_text=vague_message)
    before_agent_lifecycle(ctx)

    assert ctx.state["stage"] == Stage.DISCOVERY.value
    assert ctx.state["turn_count"] == 1
    assert ctx.state["feedback_detected"] is False


# =============================================================================
# SCENARIO 2: Enough Information -> Plan
# =============================================================================
@pytest.mark.unit
def test_scenario_2_enough_info_produces_plan():
    """
    Scenario 2: When technical constraints and goals are provided,
    update_project persists the structured sequential plan to Firestore.
    """
    user_id = "user_demo"
    project_id = "proj_recipe_app"

    res = update_project(
        user_id=user_id,
        project_id=project_id,
        title="Recipe Organizer MVP",
        goal="Organize weekly family meals with smart shopping list",
        constraints=["FastAPI", "Next.js", "PostgreSQL"],
        current_plan={
            "title": "3-Phase Implementation Roadmap",
            "steps": [
                {"id": "step_1", "description": "Set up database schema & models", "status": "pending", "assignee": "agent"},
                {"id": "step_2", "description": "Implement CRUD endpoints", "status": "pending", "assignee": "agent"},
                {"id": "step_3", "description": "Build Next.js UI components", "status": "pending", "assignee": "user"},
            ],
            "version": 1,
        },
        current_stage=Stage.PLANNING.value,
    )

    assert res["status"] == "success"
    assert res["project"]["current_stage"] == Stage.PLANNING.value
    assert len(res["project"]["current_plan"]["steps"]) == 3

    # Verify retrieval
    stored = get_project(user_id=user_id, project_id=project_id)
    assert stored["project"]["title"] == "Recipe Organizer MVP"


# =============================================================================
# SCENARIO 3: Explicit Preference -> Memory Update
# =============================================================================
@pytest.mark.unit
def test_scenario_3_explicit_preference_memory_update():
    """
    Scenario 3: An explicit user preference ('I always prefer Python with FastAPI')
    is classified as reusable preference and saved with high confidence and evidence.
    """
    user_id = "user_demo"
    pref_message = "I always prefer Python with FastAPI for backend projects."

    ctx = create_mock_context(user_id=user_id, session_id="proj_general", user_text=pref_message)
    before_agent_lifecycle(ctx)

    assert ctx.state["feedback_detected"] is True

    repo = FirestoreRepository()
    saved = repo.get_preference(user_id=user_id, preference_id="preferred_language_or_stack")
    assert saved is not None
    assert saved["key"] == "preferred_language_or_stack"
    assert saved["confidence"] >= 0.9
    assert saved["source"] == "explicit_user_statement"


# =============================================================================
# SCENARIO 4: Preference Persists Across Sessions in a NEW Project (CRITICAL)
# =============================================================================
@pytest.mark.unit
def test_scenario_4_cross_session_preference_persistence_in_new_project():
    """
    Scenario 4 (THE CRITICAL HACKATHON DEMO TEST):
    1. In Session 1 (Project A): User sets 'max_tasks_per_phase = 3'.
    2. In Session 2 (Project B, a BRAND NEW PROJECT): The preference is automatically
       preloaded into the agent's prompt context BEFORE generating the first token.
    """
    user_id = "user_hackathon_star"
    repo = FirestoreRepository()

    # Step 1: Session 1 (Project A) captures preference
    sess_1_msg = "Don't give me so many tasks at once, only give me three actions at a time."
    ctx_1 = create_mock_context(user_id=user_id, session_id="proj_A_ecommerce", user_text=sess_1_msg)
    before_agent_lifecycle(ctx_1)

    persisted_pref = repo.get_preference(user_id=user_id, preference_id="max_tasks_per_phase")
    assert persisted_pref is not None
    assert persisted_pref["value"] == 3

    # Step 2: Session 2 (Project B - BRAND NEW PROJECT) starts
    sess_2_msg = "Let's build an IoT smart home controller app."
    ctx_2 = create_mock_context(user_id=user_id, session_id="proj_B_smart_home", user_text=sess_2_msg)
    before_agent_lifecycle(ctx_2)

    # Assert: Session 2 state contains the loaded preference from Session 1
    injected_context = ctx_2.state.get("user_preferences_context", "")
    assert "max_tasks_per_phase: 3" in injected_context
    assert "{user_preferences_context?}" in root_agent.instruction


# =============================================================================
# SCENARIO 5: Project Memory Persists
# =============================================================================
@pytest.mark.unit
def test_scenario_5_project_memory_persists():
    """
    Scenario 5: Project-specific decisions, deadlines, and completed tasks
    persist in Firestore across multiple read/write operations.
    """
    user_id = "user_demo"
    project_id = "proj_telemetry"

    # Initial write
    update_project(
        user_id=user_id,
        project_id=project_id,
        title="Telemetry Pipeline",
        deadline="Friday 5PM",
        decisions=["Use MQTT protocol for IoT sensors", "Stream to InfluxDB"],
        completed_tasks=["task_0_spec"],
    )

    # Read back from clean repo handle
    repo = FirestoreRepository()
    proj = repo.get_project(user_id=user_id, project_id=project_id)
    assert proj["title"] == "Telemetry Pipeline"
    assert proj["deadline"] == "Friday 5PM"
    assert len(proj["decisions"]) == 2
    assert "task_0_spec" in proj["completed_tasks"]


# =============================================================================
# SCENARIO 6: Project Memory and User Memory Remain Separate
# =============================================================================
@pytest.mark.unit
def test_scenario_6_project_and_user_memory_remain_separate():
    """
    Scenario 6: Modifying project roadmap never writes to user preferences,
    and modifying user preferences never writes to project roadmap documents.
    """
    user_id = "user_isolation_check"
    project_id = "proj_isolation_check"

    # Write project memory
    update_project(
        user_id=user_id,
        project_id=project_id,
        title="Isolated Project",
        goal="Secret project goal"
    )

    # Write user preference
    save_user_preference(
        user_id=user_id,
        key="response_length",
        value="concise"
    )

    # Verify User Preferences collection contains ZERO project fields
    user_prefs = get_user_preferences(user_id=user_id)
    assert len(user_prefs["preferences"]) == 1
    assert "goal" not in user_prefs["preferences"][0]
    assert "Isolated Project" not in str(user_prefs)

    # Verify Project collection contains ZERO user preference keys
    proj_doc = get_project(user_id=user_id, project_id=project_id)["project"]
    assert proj_doc["title"] == "Isolated Project"
    assert "response_length" not in proj_doc


# =============================================================================
# SCENARIO 7: User Rejects a Plan -> Adaptation
# =============================================================================
@pytest.mark.unit
def test_scenario_7_user_rejects_plan_triggers_adaptation():
    """
    Scenario 7: When user gives critique ('Let's change the approach and drop Slack'),
    feedback detection sets stage=Stage.ADAPTATION and logs an adaptation audit record.
    """
    user_id = "user_demo"
    project_id = "proj_slack_bot"
    critique_msg = "Let's change the approach and drop Slack for this project."

    ctx = create_mock_context(user_id=user_id, session_id=project_id, user_text=critique_msg)
    before_agent_lifecycle(ctx)

    assert ctx.state["feedback_detected"] is True
    assert ctx.state["stage"] == Stage.ADAPTATION.value

    repo = FirestoreRepository()
    fb_records = repo.get_feedback_records(user_id=user_id, project_id=project_id)
    assert len(fb_records) == 1
    assert "drop Slack" in fb_records[0]["details"]


# =============================================================================
# SCENARIO 8: User Changes Goal -> Plan Updates
# =============================================================================
@pytest.mark.unit
def test_scenario_8_user_changes_goal_plan_updates():
    """
    Scenario 8: When the user amends the project direction, update_project
    updates the plan version, roadmap steps, and modified goal in Firestore.
    """
    user_id = "user_demo"
    project_id = "proj_dynamic_goal"

    # Initial Plan v1
    update_project(
        user_id=user_id,
        project_id=project_id,
        title="CLI Tool v1",
        current_plan={"title": "Plan v1", "steps": [{"id": "s1", "description": "Original step"}], "version": 1},
    )

    # User adjusts scope -> Plan v2
    update_project(
        user_id=user_id,
        project_id=project_id,
        title="CLI Tool v2 (Updated)",
        current_plan={"title": "Plan v2", "steps": [{"id": "s1", "description": "Revised step"}, {"id": "s2", "description": "New step"}], "version": 2},
    )

    repo = FirestoreRepository()
    updated_proj = repo.get_project(user_id=user_id, project_id=project_id)
    assert updated_proj["title"] == "CLI Tool v2 (Updated)"
    assert updated_proj["current_plan"]["version"] == 2
    assert len(updated_proj["current_plan"]["steps"]) == 2


# =============================================================================
# SCENARIO 9: Malformed Model Output -> Graceful Handling
# =============================================================================
@pytest.mark.unit
def test_scenario_9_malformed_model_output_graceful_handling():
    """
    Scenario 9: If the LLM generates an empty string or malformed response,
    AgentService catches the anomaly and returns a safe, compliant ChatResponse.
    """
    service = create_agent_service_with_mock_runner(simulated_text="")

    async def _test():
        req = ChatRequest(user_id="user_demo", project_id="proj_malformed", message="Hello")
        response = await service.process_chat(req)
        assert isinstance(response, ChatResponse)
        assert response.project_id == "proj_malformed"
        assert response.message != ""  # Populates fallback message
        assert response.requires_user_input is True

    asyncio.run(_test())


# =============================================================================
# SCENARIO 10: Database Failure -> Graceful Handling
# =============================================================================
@pytest.mark.unit
def test_scenario_10_database_failure_graceful_handling():
    """
    Scenario 10: When Firestore encounters an unexpected exception,
    tools and services catch the error, log it, and return structured error
    dictionaries without crashing the process or raising an unhandled exception.
    """
    # 1. Tool safety during DB failure
    with patch("app.db.repository.FirestoreRepository.get_project", side_effect=Exception("Firestore timeout")):
        result = get_project(user_id="u1", project_id="p1")
        assert result["status"] == "error"
        assert "Failed to retrieve project" in result["message"]

    # 2. Service safety during DB failure
    service = create_agent_service_with_mock_runner(simulated_text="I'm still here to help.")
    with patch("app.db.repository.FirestoreRepository.save_message", side_effect=Exception("Firestore connection lost")):
        async def _test_svc():
            req = ChatRequest(user_id="u1", project_id="p1", message="Continue")
            res = await service.process_chat(req)
            assert isinstance(res, ChatResponse)
            assert res.project_id == "p1"

        asyncio.run(_test_svc())
