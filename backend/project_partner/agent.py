import os
from typing import Any, Optional
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from app.schemas.contract import Stage
from app.db.repository import FirestoreRepository
from app.tools.project_memory import get_project, update_project
from app.tools.user_memory import get_user_preferences, save_user_preference
from app.classifier.feedback import classify_feedback, FeedbackTarget

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-2.5-flash"


def format_preferences_for_prompt(preferences: list[dict[str, Any]]) -> str:
    """Formats retrieved user preferences into a clean, authoritative prompt context block."""
    if not preferences:
        return "None recorded yet. Follow standard balanced defaults."

    formatted_lines = []
    for pref in preferences:
        key = pref.get("key")
        val = pref.get("value")
        confidence = pref.get("confidence", 1.0)
        formatted_lines.append(f"• {key}: {val} (confidence: {confidence})")
    return "\n".join(formatted_lines)


def before_agent_lifecycle(callback_context: CallbackContext) -> None:
    """
    Lifecycle callback executed BEFORE agent generates a turn response:
    1. Preloads persistent cross-project user preferences from Firestore into prompt context.
    2. Runs feedback classification on the incoming user message.
    3. If reusable preference feedback is detected, automatically persists it to Firestore
       and updates the active preferences context so the immediate turn obeys it.
    4. Tracks turn counter and manages lifecycle stage transitions.
    """
    state = callback_context.state
    session = getattr(callback_context, "session", None)
    user_id = getattr(callback_context, "user_id", None) or (
        getattr(session, "user_id", "default_user") if session else "default_user"
    )
    project_id = getattr(session, "id", "default_project") if session else "default_project"

    # 1. Initialize Stage and Turn Counter
    if "stage" not in state:
        state["stage"] = Stage.DISCOVERY.value
    if "turn_count" not in state:
        state["turn_count"] = 0
    state["turn_count"] += 1

    # 2. Extract latest user input
    user_message = ""
    user_content = getattr(callback_context, "user_content", None)
    if user_content and hasattr(user_content, "parts"):
        for part in user_content.parts:
            if hasattr(part, "text") and part.text:
                user_message += part.text

    repo = FirestoreRepository()

    # 3. Analyze Feedback on Incoming User Message
    if user_message:
        classification = classify_feedback(
            message=user_message,
            current_stage=state.get("stage"),
            use_llm=False  # Fast deterministic classification in lifecycle hook
        )
        state["feedback_detected"] = classification.is_feedback

        # Route (a): Reusable User Preference Feedback -> Auto-persist to Firestore
        if classification.is_feedback and classification.target in (
            FeedbackTarget.REUSABLE_PREFERENCE,
            FeedbackTarget.HYBRID,
        ):
            if classification.suggested_key and classification.suggested_value is not None:
                repo.set_preference(
                    user_id=user_id,
                    preference_id=classification.suggested_key,
                    value=classification.suggested_value,
                    category=classification.category or "general",
                    confidence=classification.confidence,
                    source="explicit_user_statement",
                    evidence=user_message,
                    source_turn=state["turn_count"],
                )
                state["last_adaptation_event"] = (
                    f"Saved user preference: {classification.suggested_key} = {classification.suggested_value}"
                )

        # Route (b): Project-Specific Feedback -> Trigger Adaptation Stage
        elif classification.is_feedback and classification.target == FeedbackTarget.PROJECT_SPECIFIC:
            state["stage"] = Stage.ADAPTATION.value
            repo.save_feedback(
                user_id=user_id,
                project_id=project_id,
                feedback_id=f"fb_{state['turn_count']}",
                feedback_type="project_course_correction",
                details=user_message,
            )
            state["last_adaptation_event"] = f"Logged project feedback for turn {state['turn_count']}"

    # 4. Preload and Inject Authoritative User Preferences into Prompt Template
    try:
        user_prefs = repo.get_all_preferences(user_id=user_id)
        state["user_preferences_context"] = format_preferences_for_prompt(user_prefs)
    except Exception:
        state["user_preferences_context"] = "None recorded yet. Follow standard defaults."


def after_agent_lifecycle(callback_context: CallbackContext) -> None:
    """
    Lifecycle callback executed AFTER agent response generation.
    Advances stage progressively if not in explicit adaptation mode.
    """
    state = callback_context.state
    current_stage = state.get("stage", Stage.DISCOVERY.value)
    turn_count = state.get("turn_count", 1)

    if current_stage == Stage.ADAPTATION.value:
        state["stage"] = Stage.PLANNING.value  # Move back to updated planning after adapting
    elif current_stage == Stage.DISCOVERY.value and turn_count >= 1:
        state["stage"] = Stage.CLARIFICATION.value
    elif current_stage == Stage.CLARIFICATION.value and turn_count >= 2:
        state["stage"] = Stage.PLANNING.value
    elif current_stage == Stage.PLANNING.value and turn_count >= 3:
        state["stage"] = Stage.REVIEW.value


SYSTEM_INSTRUCTION = """
You are "Project Partner" — an expert collaborative AI partner designed to lead the way and take meticulous notes.

### CURRENT APPLICATION STATE:
- Active Lifecycle Stage: {stage?}
- Conversation Turn: {turn_count?}
- Feedback Detected in Current Turn: {feedback_detected?}
- Last Adaptation Event: {last_adaptation_event?}

### AUTHORITATIVE USER PREFERENCES (MUST BE STRICTLY OBEYED ACROSS ALL PROJECTS):
{user_preferences_context?}

### CRITICAL RULES FOR ADAPTATION & BEHAVIOR:
1. STRICT PREFERENCE ADHERENCE:
   - If `max_tasks_per_phase` is defined (e.g. 3), you MUST NEVER output more than that number of tasks in a single phase or plan!
   - If `response_length` is "concise", avoid lengthy preambles, conversational filler, and large walls of text.
   - If `include_code_examples` is True, always provide concrete code snippets for recommended steps.
   - If `planning_style` is "step_by_step", present only one phase at a time and ask for approval.

2. STAGE-GOVERNED BEHAVIOR:
   - When Stage is "discovery": Welcome the user, acknowledge their project idea, and identify the domain.
   - When Stage is "clarification": Ask 2-3 high-impact clarifying questions before proposing any plan.
   - When Stage is "planning" or "adaptation": Propose a sequential roadmap respecting all user preferences, and call `update_project`.
   - When Stage is "review": Request explicit user confirmation on the roadmap.

3. NOTE-TAKING (Every Turn):
Always maintain and update notes:
📝 Partner Notes:
• Decisions: [Key choices agreed upon]
• Constraints: [Limits, deadlines, libraries]
• Preferences: [Active user preferences applied]
""".strip()

root_agent = Agent(
    name="project_partner",
    model=MODEL_NAME,
    description="Collaborative partner agent with end-to-end memory adaptation.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[get_project, update_project, get_user_preferences, save_user_preference],
    before_agent_callback=before_agent_lifecycle,
    after_agent_callback=after_agent_lifecycle,
)
