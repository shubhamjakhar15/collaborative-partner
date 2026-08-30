import pytest
from pydantic import ValidationError
from app.schemas.contract import (
    Stage,
    Intent,
    StepStatus,
    PlanStep,
    Plan,
    QuestionItem,
    MemoryType,
    MemoryUpdate,
    PartnerRequest,
    PartnerResponse,
)


def test_valid_partner_request():
    """Verify that a standard valid PartnerRequest validates and parses properly."""
    req_data = {
        "session_id": "sess-123",
        "user_id": "user-456",
        "message": "Let's build a recipe organizer app.",
        "metadata": {"source": "web_chat"}
    }
    request = PartnerRequest.model_validate(req_data)
    assert request.session_id == "sess-123"
    assert request.user_id == "user-456"
    assert request.message == "Let's build a recipe organizer app."
    assert request.metadata == {"source": "web_chat"}


def test_invalid_partner_request_empty_fields():
    """Verify that empty session_id or empty message raises a ValidationError."""
    with pytest.raises(ValidationError):
        PartnerRequest(session_id="", message="Hello")

    with pytest.raises(ValidationError):
        PartnerRequest(session_id="sess-123", message="")


def test_invalid_partner_request_extra_fields():
    """Verify that unexpected extra fields are rejected (extra='forbid')."""
    with pytest.raises(ValidationError):
        PartnerRequest(
            session_id="sess-123",
            message="Hello",
            unauthorized_key="value"  # type: ignore
        )


def test_valid_minimal_partner_response():
    """Verify minimal PartnerResponse with default empty lists and plan=None."""
    res_data = {
        "session_id": "sess-123",
        "message": "I'm here to help! What type of app are we designing?",
        "stage": "discovery",
        "intent": "discover_context",
        "next_action": "Wait for user to describe their project idea.",
        "requires_user_input": True,
    }
    response = PartnerResponse.model_validate(res_data)
    assert response.stage == Stage.DISCOVERY
    assert response.intent == Intent.DISCOVER_CONTEXT
    assert response.questions == []
    assert response.plan is None
    assert response.memory_updates == []
    assert response.feedback_detected is False
    assert response.requires_user_input is True


def test_valid_rich_partner_response():
    """Verify a rich PartnerResponse with questions, plan, and memory updates."""
    response = PartnerResponse(
        session_id="sess-123",
        message="Here is our proposed plan based on your requirements.",
        stage=Stage.PLANNING,
        intent=Intent.GENERATE_PLAN,
        questions=[
            QuestionItem(
                id="q1",
                text="Do you want to support dietary filters in MVP?",
                options=["Yes", "No", "Post-MVP"],
                is_optional=False
            )
        ],
        plan=Plan(
            title="Recipe Organizer MVP",
            summary="3-step roadmap to build the frontend and backend.",
            steps=[
                PlanStep(id="step_1", description="Define Pydantic schema", status=StepStatus.COMPLETED, assignee="agent"),
                PlanStep(id="step_2", description="Implement ADK workflow", status=StepStatus.IN_PROGRESS, assignee="agent"),
                PlanStep(id="step_3", description="Review UI mocks", status=StepStatus.PENDING, assignee="user"),
            ],
            version=1
        ),
        feedback_detected=False,
        memory_updates=[
            MemoryUpdate(
                id="mem-1",
                type=MemoryType.DECISION,
                content="Chose Firestore for persistent state storage."
            ),
            MemoryUpdate(
                id="mem-2",
                type=MemoryType.CONSTRAINT,
                content="Target launch within 24 hours."
            )
        ],
        next_action="Review the plan with the user and obtain confirmation.",
        requires_user_input=True
    )

    assert response.stage == Stage.PLANNING
    assert len(response.questions) == 1
    assert response.plan is not None
    assert len(response.plan.steps) == 3
    assert response.plan.steps[0].status == StepStatus.COMPLETED
    assert len(response.memory_updates) == 2
    assert response.memory_updates[0].type == MemoryType.DECISION

    # Verify JSON serialization round-trip
    json_output = response.model_dump_json()
    assert "Recipe Organizer MVP" in json_output
    assert "discovery" not in json_output  # it's planning
    assert "planning" in json_output


def test_invalid_stage_enum_raises_validation_error():
    """Verify that an invalid stage value fails validation."""
    with pytest.raises(ValidationError) as excinfo:
        PartnerResponse(
            session_id="sess-123",
            message="Hello",
            stage="invalid_stage_value",  # type: ignore
            intent=Intent.GENERAL_CHAT,
            next_action="Continue",
        )
    assert "Input should be 'discovery'" in str(excinfo.value) or "Input should be" in str(excinfo.value)


def test_invalid_plan_version_raises_validation_error():
    """Verify that a plan version less than 1 is rejected."""
    with pytest.raises(ValidationError):
        Plan(
            title="Invalid Plan",
            version=0  # ge=1 violated
        )


def test_json_schema_export():
    """Verify that OpenAPI / JSON schema generation works without error."""
    schema = PartnerResponse.model_json_schema()
    assert "properties" in schema
    assert "stage" in schema["properties"]
    assert "memory_updates" in schema["properties"]
    assert "plan" in schema["properties"]
