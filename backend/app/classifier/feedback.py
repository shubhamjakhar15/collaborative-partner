import os
import re
from enum import Enum
from typing import Any, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field
from google import genai
from google.genai import types

load_dotenv()


class FeedbackTarget(str, Enum):
    """
    Target scope of the detected feedback:
    - NONE: Message is standard informational input (goal description, answering questions).
    - PROJECT_SPECIFIC: Critique, scope change, or constraint bound ONLY to the current project.
    - REUSABLE_PREFERENCE: Enduring habit, communication preference, or workflow style across all projects.
    - HYBRID: Contains both project-specific course correction and general user preferences.
    """
    NONE = "none"
    PROJECT_SPECIFIC = "project_specific"
    REUSABLE_PREFERENCE = "reusable_preference"
    HYBRID = "hybrid"


class FeedbackClassification(BaseModel):
    """Structured result of feedback detection and classification."""
    model_config = ConfigDict(extra="forbid")

    is_feedback: bool = Field(
        ...,
        description="True if the message is a critique, suggestion, preference, or course-correction; False for ordinary goal statements or factual answers."
    )
    target: FeedbackTarget = Field(
        ...,
        description="Scope of feedback: 'project_specific', 'reusable_preference', 'hybrid', or 'none'."
    )
    category: Optional[str] = Field(
        default=None,
        description="Domain category: 'communication', 'planning', 'technical', or 'scope'."
    )
    suggested_key: Optional[str] = Field(
        default=None,
        description="Whitelisted preference key if reusable (e.g., 'response_length', 'planning_style', 'include_code_examples')."
    )
    suggested_value: Optional[Any] = Field(
        default=None,
        description="The extracted preference value (e.g., 'concise', True, 3)."
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Classification confidence (1.0 for explicit commands, 0.7 for subtle cues)."
    )
    reasoning: str = Field(
        ...,
        description="Concise rationale explaining the classification decision."
    )


CLASSIFICATION_PROMPT = """
You are an expert feedback classifier for an AI coding partner assistant.

Your task is to analyze the user's message and determine:
1. Is this FEEDBACK / CRITIQUE / COURSE-CORRECTION (True) or standard information/goal description (False)?
2. If feedback, is it:
   - "project_specific": Modifies the current project's scope, architecture, milestones, or libraries.
   - "reusable_preference": An enduring user trait or habit across ALL projects (e.g. "Give me shorter answers", "I always prefer code examples", "Don't give me so many tasks at once").
   - "hybrid": Contains both.
   - "none": Not feedback.
""".strip()


def heuristic_feedback_classifier(message: str) -> FeedbackClassification:
    """
    High-speed deterministic heuristic classifier used as a baseline and fallback.
    """
    msg = message.strip().lower()

    # Rule 1: Reusable Preference - Response Brevity
    if any(p in msg for p in ["shorter answers", "too long", "too verbose", "be concise", "keep it brief", "less text"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.REUSABLE_PREFERENCE,
            category="communication",
            suggested_key="response_length",
            suggested_value="concise",
            confidence=0.95,
            reasoning="User explicitly requested concise responses across conversations."
        )

    # Rule 2: Reusable Preference - Code Examples
    if any(p in msg for p in ["prefer examples", "show examples", "include examples", "with code samples"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.REUSABLE_PREFERENCE,
            category="communication",
            suggested_key="include_code_examples",
            suggested_value=True,
            confidence=0.95,
            reasoning="User stated a persistent preference for code examples."
        )

    # Rule 3: Reusable Preference - Tech Stack / Language Defaults
    if any(p in msg for p in ["always prefer python", "prefer python", "prefer fastapi", "preferred stack", "always prefer"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.REUSABLE_PREFERENCE,
            category="technical",
            suggested_key="preferred_language_or_stack",
            suggested_value="Python + FastAPI",
            confidence=0.95,
            reasoning="User stated an explicit language and tech stack preference."
        )

    # Rule 4: Reusable Preference - Task Throttling
    if any(p in msg for p in ["too many tasks", "so many tasks at once", "fewer tasks", "limit tasks", "three actions at a time"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.REUSABLE_PREFERENCE,
            category="planning",
            suggested_key="max_tasks_per_phase",
            suggested_value=3,
            confidence=0.90,
            reasoning="User expressed frustration with task overload; set task throttle."
        )

    # Rule 5: Reusable Preference - Planning Style
    if any(p in msg for p in ["always use step-by-step", "always plan step by step", "prefer step by step"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.REUSABLE_PREFERENCE,
            category="planning",
            suggested_key="planning_style",
            suggested_value="step_by_step",
            confidence=0.95,
            reasoning="User expressed a cross-project step-by-step planning rule."
        )

    # Rule 6: Project-Specific Feedback - Scope / Approach Change
    if any(p in msg for p in ["change the approach", "this project should", "drop slack", "instead of rest", "milestones instead of"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.PROJECT_SPECIFIC,
            category="scope",
            confidence=0.90,
            reasoning="User requested a modification specifically for the current project's scope/architecture."
        )

    # Rule 7: General Complexity Critique
    if any(p in msg for p in ["too complicated", "too complex", "simplify this"]):
        return FeedbackClassification(
            is_feedback=True,
            target=FeedbackTarget.REUSABLE_PREFERENCE,
            category="communication",
            suggested_key="response_length",
            suggested_value="concise",
            confidence=0.85,
            reasoning="User indicated communication is overly complex; suggest simplifying presentation."
        )

    # Default: Non-Feedback (Informational / Goal input)
    return FeedbackClassification(
        is_feedback=False,
        target=FeedbackTarget.NONE,
        category=None,
        suggested_key=None,
        suggested_value=None,
        confidence=0.90,
        reasoning="Message contains domain information, goals, or standard dialogue without critique."
    )


def classify_feedback(
    message: str,
    current_stage: Optional[str] = None,
    use_llm: bool = True,
) -> FeedbackClassification:
    """
    Classifies whether user input contains feedback and determines its target scope.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not use_llm or not api_key:
        return heuristic_feedback_classifier(message)

    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""
{CLASSIFICATION_PROMPT}

Current Project Stage: {current_stage or 'unknown'}
User Message: "{message}"

Classify this message accurately according to the JSON schema.
""".strip()

        model_name = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-2.5-flash"
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FeedbackClassification,
                temperature=0.0,
            ),
        )

        if response.text:
            return FeedbackClassification.model_validate_json(response.text)
        return heuristic_feedback_classifier(message)
    except Exception:
        return heuristic_feedback_classifier(message)
