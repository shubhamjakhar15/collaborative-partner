from typing import Any, Optional
from app.db.repository import FirestoreRepository, WHITELISTED_PREFERENCE_KEYS, TRIVIAL_STATEMENTS


def get_user_preferences(
    user_id: str,
) -> dict[str, Any]:
    """
    Retrieves all persistent cross-project user preferences for a given user.
    These represent long-term user habits, communication preferences, preferred tech stack,
    response brevity, and architectural style across all projects.

    Args:
        user_id (str): The unique identifier of the user.

    Returns:
        dict[str, Any]: A dictionary containing 'status': 'success' and a list of 'preferences'.
    """
    try:
        if not user_id or not user_id.strip():
            return {"status": "error", "message": "user_id cannot be empty."}

        repo = FirestoreRepository()
        preferences = repo.get_all_preferences(user_id=user_id)

        return {
            "status": "success",
            "message": f"Retrieved {len(preferences)} preferences for user '{user_id}'.",
            "preferences": preferences,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve user preferences: {str(e)}",
            "preferences": [],
        }


def save_user_preference(
    user_id: str,
    key: str,
    value: Any,
    category: str = "general",
    confidence: float = 1.0,
    source: str = "explicit_user_statement",
    evidence: Optional[str] = None,
) -> dict[str, Any]:
    """
    Saves a reusable, cross-project user preference to Firestore.
    Use this ONLY for enduring user-level traits (e.g. response length, planning style,
    default tech stack, inclusion of code examples). NEVER use this for project-specific goals.

    Allowed keys:
      - response_length (e.g. 'concise', 'detailed')
      - communication_tone (e.g. 'direct', 'collaborative', 'formal')
      - include_code_examples (e.g. True / False)
      - notes_format (e.g. 'markdown_bullets', 'structured_table')
      - planning_style (e.g. 'step_by_step', 'iterative', 'upfront_detailed')
      - include_tradeoffs (e.g. True / False)
      - max_tasks_per_phase (e.g. 3, 5)
      - technical_depth (e.g. 'expert', 'intermediate', 'beginner')
      - preferred_language_or_stack (e.g. 'Python + FastAPI', 'TypeScript + React')
      - target_cloud_provider (e.g. 'GCP', 'AWS', 'Firebase')

    Args:
        user_id (str): The unique identifier of the user.
        key (str): The whitelisted preference key.
        value (Any): The preference value. Trivial statements ('ok', 'sounds good') are rejected.
        category (str, optional): Category such as 'communication', 'planning', or 'technical'.
        confidence (float, optional): Confidence rating between 0.0 and 1.0 (1.0 for explicit user statements, 0.7 for inferred).
        source (str, optional): Source of preference ('explicit_user_statement', 'inferred_from_interaction', 'direct_feedback').
        evidence (str, optional): Direct user quote justifying this preference.

    Returns:
        dict[str, Any]: A dictionary with 'status': 'success' and the saved preference, or 'status': 'error'.
    """
    try:
        # 1. Validation
        if not user_id or not user_id.strip():
            return {"status": "error", "message": "user_id cannot be empty."}
        if not key or not key.strip():
            return {"status": "error", "message": "key cannot be empty."}

        clean_key = key.strip().lower()
        if clean_key not in WHITELISTED_PREFERENCE_KEYS:
            return {
                "status": "error",
                "message": f"Key '{clean_key}' is not in the allowed preference whitelist: {sorted(WHITELISTED_PREFERENCE_KEYS)}",
            }

        # 2. Filter trivial values
        if isinstance(value, str) and value.strip().lower() in TRIVIAL_STATEMENTS:
            return {
                "status": "error",
                "message": f"Refusing to save trivial confirmation '{value}' as a persistent user preference.",
            }

        # 3. Persist via repository
        repo = FirestoreRepository()
        saved = repo.set_preference(
            user_id=user_id,
            preference_id=clean_key,
            value=value,
            category=category,
            confidence=confidence,
            source=source,
            evidence=evidence,
        )

        return {
            "status": "success",
            "message": f"Saved user preference '{clean_key}' successfully.",
            "preference": saved,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save user preference: {str(e)}",
        }
