import pytest
from app.classifier.feedback import (
    FeedbackTarget,
    FeedbackClassification,
    heuristic_feedback_classifier,
    classify_feedback,
)


@pytest.mark.parametrize(
    "message, expected_is_feedback, expected_target, expected_key, expected_val",
    [
        # 1. Reusable Preference: Shorter answers
        (
            "Give me shorter answers",
            True,
            FeedbackTarget.REUSABLE_PREFERENCE,
            "response_length",
            "concise",
        ),
        # 2. Reusable Preference: Prefer examples
        (
            "I prefer examples whenever you explain code",
            True,
            FeedbackTarget.REUSABLE_PREFERENCE,
            "include_code_examples",
            True,
        ),
        # 3. Reusable Preference: Task throttling
        (
            "Don't give me so many tasks at once",
            True,
            FeedbackTarget.REUSABLE_PREFERENCE,
            "max_tasks_per_phase",
            3,
        ),
        # 4. Reusable Preference: General complexity critique
        (
            "This is too complicated, please simplify this",
            True,
            FeedbackTarget.REUSABLE_PREFERENCE,
            "response_length",
            "concise",
        ),
        # 5. Reusable Preference: Explicit planning rule
        (
            "Always use step-by-step planning for everything we do",
            True,
            FeedbackTarget.REUSABLE_PREFERENCE,
            "planning_style",
            "step_by_step",
        ),
        # 6. Project-Specific Feedback: Approach change
        (
            "Let's change the approach and drop Slack for this project",
            True,
            FeedbackTarget.PROJECT_SPECIFIC,
            None,
            None,
        ),
        # 7. Project-Specific Feedback: Milestone adjustment
        (
            "This project should have 3 milestones instead of 5",
            True,
            FeedbackTarget.PROJECT_SPECIFIC,
            None,
            None,
        ),
        # 8. Non-Feedback: Target audience clarification
        (
            "My target audience is senior healthcare administrators",
            False,
            FeedbackTarget.NONE,
            None,
            None,
        ),
        # 9. Non-Feedback: Initial project goal
        (
            "Let's build a real-time whiteboard app with WebSockets",
            False,
            FeedbackTarget.NONE,
            None,
            None,
        ),
    ],
)
def test_feedback_classification_cases(
    message: str,
    expected_is_feedback: bool,
    expected_target: FeedbackTarget,
    expected_key: str | None,
    expected_val: object,
):
    """Verify classification across the benchmark test suite."""
    result: FeedbackClassification = heuristic_feedback_classifier(message)

    assert result.is_feedback == expected_is_feedback
    assert result.target == expected_target

    if expected_key is not None:
        assert result.suggested_key == expected_key
    if expected_val is not None:
        assert result.suggested_value == expected_val


def test_classify_feedback_schema_validity():
    """Verify that classify_feedback returns a valid Pydantic model with extra='forbid'."""
    result = classify_feedback("Give me shorter answers", use_llm=False)
    assert isinstance(result, FeedbackClassification)
    assert result.confidence >= 0.0
    assert result.confidence <= 1.0
    assert len(result.reasoning) > 0
