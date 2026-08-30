from datetime import datetime, timezone
from typing import Any, Optional
from app.db.repository import FirestoreRepository, get_db_client


def get_project(
    user_id: str,
    project_id: str,
) -> dict[str, Any]:
    """
    Retrieves the persistent project memory and state for a specific project.
    Fetches the project goal, target audience, technical constraints, deadline,
    recorded architectural decisions, active plan, completed tasks, and current stage.

    Args:
        user_id (str): The unique identifier of the user who owns the project.
        project_id (str): The unique identifier of the project to retrieve.

    Returns:
        dict[str, Any]: A dictionary with 'status': 'success' and 'project' data if found,
                       or 'status': 'not_found' if the project does not exist yet.
    """
    try:
        repo = FirestoreRepository()
        project_data = repo.get_project(user_id=user_id, project_id=project_id)

        if not project_data:
            return {
                "status": "not_found",
                "message": f"Project '{project_id}' was not found for user '{user_id}'. You may initialize it by calling update_project.",
                "project": None,
            }

        return {
            "status": "success",
            "message": f"Retrieved project '{project_id}' successfully.",
            "project": project_data,
        }
    except Exception as e:
        # Safe failure: never crash the LLM execution turn on unexpected database errors
        return {
            "status": "error",
            "message": f"Failed to retrieve project '{project_id}': {str(e)}",
            "project": None,
        }


def update_project(
    user_id: str,
    project_id: str,
    title: Optional[str] = None,
    goal: Optional[str] = None,
    target_user: Optional[str] = None,
    constraints: Optional[list[str]] = None,
    deadline: Optional[str] = None,
    decisions: Optional[list[str]] = None,
    current_plan: Optional[dict[str, Any]] = None,
    completed_tasks: Optional[list[str]] = None,
    current_stage: Optional[str] = None,
) -> dict[str, Any]:
    """
    Creates or updates the persistent project memory and roadmap in Firestore.
    Use this tool whenever new requirements are clarified, decisions are made,
    the plan is adapted, or tasks are completed.

    Args:
        user_id (str): The unique identifier of the user who owns the project.
        project_id (str): The unique identifier of the project to update.
        title (str, optional): The name/title of the project.
        goal (str, optional): The core objective or problem statement of the project.
        target_user (str, optional): The intended target audience or user persona.
        constraints (list[str], optional): Technical limits, required tech stack, or budget constraints.
        deadline (str, optional): Project timeline or target completion date/milestone.
        decisions (list[str], optional): Key architectural or product decisions agreed upon.
        current_plan (dict, optional): The active sequential roadmap/steps.
        completed_tasks (list[str], optional): List of step IDs or task descriptions marked complete.
        current_stage (str, optional): Lifecycle stage (e.g. 'discovery', 'planning', 'execution').

    Returns:
        dict[str, Any]: A dictionary with 'status': 'success' and the updated project payload,
                       or 'status': 'error' with an explanatory message.
    """
    try:
        # 1. Basic validation
        if not user_id or not user_id.strip():
            return {"status": "error", "message": "user_id cannot be empty."}
        if not project_id or not project_id.strip():
            return {"status": "error", "message": "project_id cannot be empty."}

        # 2. Build non-null payload update dictionary
        updates: dict[str, Any] = {}
        if title is not None:
            updates["title"] = title
        if goal is not None:
            updates["goal"] = goal
        if target_user is not None:
            updates["target_user"] = target_user
        if constraints is not None:
            updates["constraints"] = constraints
        if deadline is not None:
            updates["deadline"] = deadline
        if decisions is not None:
            updates["decisions"] = decisions
        if current_plan is not None:
            updates["current_plan"] = current_plan
        if completed_tasks is not None:
            updates["completed_tasks"] = completed_tasks
        if current_stage is not None:
            updates["current_stage"] = current_stage

        if not updates:
            return {
                "status": "warning",
                "message": "No update fields provided. Project was not modified.",
            }

        # 3. Persist to Firestore via repository
        repo = FirestoreRepository()
        saved_project = repo.set_project(
            user_id=user_id,
            project_id=project_id,
            data=updates,
        )

        return {
            "status": "success",
            "message": f"Project '{project_id}' updated successfully.",
            "project": saved_project,
        }
    except Exception as e:
        # Safe failure: return structured error dictionary rather than raising unhandled exceptions
        return {
            "status": "error",
            "message": f"Failed to update project '{project_id}': {str(e)}",
        }
