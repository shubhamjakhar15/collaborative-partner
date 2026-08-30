from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Stage(str, Enum):
    """
    Lifecycle stages of the collaborative partner:
    - DISCOVERY: Initial phase uncovering user's project idea, domain, and vision.
    - CLARIFICATION: Asking targeted questions to resolve ambiguities and pin down scope.
    - PLANNING: Synthesizing goals into a concrete, multi-step structured plan.
    - REVIEW: Presenting the generated plan to the user for evaluation and approval.
    - FEEDBACK: Ingesting user critiques, modifications, or rejections.
    - ADAPTATION: Updating and re-versioning the plan based on feedback.
    - EXECUTION: Actively stepping through and executing agreed-upon tasks.
    - COMPLETE: All steps executed and final project summary presented.
    """
    DISCOVERY = "discovery"
    CLARIFICATION = "clarification"
    PLANNING = "planning"
    REVIEW = "review"
    FEEDBACK = "feedback"
    ADAPTATION = "adaptation"
    EXECUTION = "execution"
    COMPLETE = "complete"


class Intent(str, Enum):
    """Fine-grained intent of the agent in the current turn."""
    DISCOVER_CONTEXT = "discover_context"
    CLARIFY_GOAL = "clarify_goal"
    GENERATE_PLAN = "generate_plan"
    REQUEST_REVIEW = "request_review"
    PROCESS_FEEDBACK = "process_feedback"
    ADAPT_PLAN = "adapt_plan"
    EXECUTE_STEP = "execute_step"
    SUMMARIZE = "summarize"
    GENERAL_CHAT = "general_chat"


class StepStatus(str, Enum):
    """Status of an individual step in the project plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class PlanStep(BaseModel):
    """A discrete, actionable task within the project plan."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique step identifier (e.g. 'step_1')")
    description: str = Field(..., description="Actionable task description")
    status: StepStatus = Field(default=StepStatus.PENDING, description="Execution status")
    assignee: str = Field(default="agent", description="Responsible party: 'agent' or 'user'")


class Plan(BaseModel):
    """Structured plan outlining the roadmap and execution tasks."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., description="Title of the plan")
    summary: str = Field(default="", description="High-level plan summary")
    steps: list[PlanStep] = Field(default_factory=list, description="Ordered tasks")
    version: int = Field(default=1, ge=1, description="Incremented on plan modification")


class QuestionItem(BaseModel):
    """Targeted question presented to the user to guide decision-making."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique question identifier (e.g. 'q1')")
    text: str = Field(..., description="The question prompt presented to the user")
    options: Optional[list[str]] = Field(default=None, description="Suggested multiple-choice options")
    is_optional: bool = Field(default=False, description="Indicates if question can be skipped")


class MemoryType(str, Enum):
    """Category of captured collaborative partner note."""
    DECISION = "decision"
    CONSTRAINT = "constraint"
    PREFERENCE = "preference"
    NOTE = "note"


class MemoryUpdate(BaseModel):
    """A persistent note, decision, or constraint recorded during the turn."""
    model_config = ConfigDict(extra="forbid")

    id: Optional[str] = Field(default=None, description="Note identifier")
    type: MemoryType = Field(default=MemoryType.NOTE, description="Category of note")
    content: str = Field(..., description="Recorded note text or decision")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp"
    )


class FileAttachment(BaseModel):
    """Uploaded file or image attachment."""
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = Field(default=None, description="Unique file identifier")
    filename: str = Field(..., description="Original file name")
    content_type: str = Field(..., description="MIME type (e.g. image/png, application/json, text/plain)")
    size: Optional[int] = Field(default=None, description="File size in bytes")
    data_base64: Optional[str] = Field(default=None, description="Base64-encoded file data")
    url: Optional[str] = Field(default=None, description="Public or static preview/download URL")
    summary: Optional[str] = Field(default=None, description="Extracted text or brief content summary")
    uploaded_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Upload timestamp"
    )


class ChatRequest(BaseModel):
    """Incoming user request contract sent by the frontend."""
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(default="demo-user", min_length=1, description="User identifier")
    project_id: Optional[str] = Field(default=None, description="Project identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier alias")
    message: str = Field(..., min_length=1, description="User's input text")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Client metadata")
    attachments: list[FileAttachment] = Field(default_factory=list, description="Uploaded files/images for this turn")

    @model_validator(mode="after")
    def sync_request_ids(self) -> "ChatRequest":
        if not self.project_id and self.session_id:
            self.project_id = self.session_id
        elif not self.session_id and self.project_id:
            self.session_id = self.project_id
        if not self.project_id:
            raise ValueError("Either project_id or session_id must be provided and non-empty.")
        return self


# Backward-compatibility alias
PartnerRequest = ChatRequest


class PartnerResponse(BaseModel):
    """
    Standardized, strongly-typed response returned to frontend on every turn.
    """
    model_config = ConfigDict(extra="forbid")

    project_id: Optional[str] = Field(default=None, description="Project identifier")
    session_id: Optional[str] = Field(default=None, description="Session identifier alias")
    message: str = Field(..., description="Conversational text to display in chat")
    stage: Stage = Field(..., description="Current collaborative lifecycle stage")
    intent: Intent = Field(..., description="Agent intent for this turn")
    questions: list[QuestionItem] = Field(default_factory=list, description="Interactive questions")
    plan: Optional[Plan] = Field(default=None, description="Structured roadmap if active or updated")
    feedback_detected: bool = Field(default=False, description="True if user gave critique/feedback")
    memory_updates: list[MemoryUpdate] = Field(default_factory=list, description="Notes captured this turn")
    attachments: list[FileAttachment] = Field(default_factory=list, description="Attachments sent or processed in this turn")
    project_files: list[FileAttachment] = Field(default_factory=list, description="All persistent project files")
    next_action: str = Field(..., description="What the agent or user should do next")
    requires_user_input: bool = Field(default=True, description="Whether agent is awaiting user response")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC generation time"
    )

    @model_validator(mode="after")
    def sync_response_ids(self) -> "PartnerResponse":
        if not self.project_id and self.session_id:
            self.project_id = self.session_id
        elif not self.session_id and self.project_id:
            self.session_id = self.project_id
        return self


ChatResponse = PartnerResponse


class ErrorResponse(BaseModel):
    """
    Standardized error payload returned across all API endpoints.
    Guarantees internal tracebacks and raw exceptions are never leaked.
    """
    model_config = ConfigDict(extra="forbid")

    error: str = Field(..., description="Error category code (e.g. 'validation_error', 'not_found', 'service_error')")
    message: str = Field(..., description="Human-readable error explanation")
    detail: Optional[Any] = Field(default=None, description="Contextual error details or validation field breakdown")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of error occurrence"
    )
