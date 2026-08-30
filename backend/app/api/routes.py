from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.contract import ChatRequest, ChatResponse
from app.services.agent_service import AgentService, get_agent_service
from app.db.repository import FirestoreRepository

router = APIRouter()


# -----------------------------------------------------------------------------
# 1. CORE CHAT ENDPOINT (Conversational Turn)
# -----------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    req: ChatRequest,
    service: AgentService = Depends(get_agent_service),
) -> ChatResponse:
    """
    Primary Collaborative Partner Chat Endpoint.
    Accepts incoming user messages, executes the ADK Runner workflow,
    updates state & memory, and returns the strongly-typed ChatResponse.
    """
    return await service.process_chat(req)


# -----------------------------------------------------------------------------
# 2. USER PREFERENCES ENDPOINT (Cross-Project Memory Vault)
# -----------------------------------------------------------------------------
@router.get("/users/{user_id}/preferences")
async def get_user_preferences_endpoint(
    user_id: str,
) -> dict[str, Any]:
    """
    Retrieves all persistent cross-project preferences for a user.
    Powers the frontend 'User Memory Vault' / settings panel to visually
    demonstrate learned habits (e.g. response length, planning style, tech stack).
    """
    repo = FirestoreRepository()
    try:
        preferences = repo.get_all_preferences(user_id=user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "count": len(preferences),
            "preferences": preferences,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user preferences: {str(e)}")


# -----------------------------------------------------------------------------
# 3. PROJECT DETAIL ENDPOINT (Roadmap & State Hydration)
# -----------------------------------------------------------------------------
@router.get("/users/{user_id}/projects/{project_id}")
async def get_project_endpoint(
    user_id: str,
    project_id: str,
    include_messages: bool = Query(default=True, description="Whether to include chat message history"),
) -> dict[str, Any]:
    """
    Retrieves project roadmap, goals, constraints, decisions, and chat history.
    Allows the frontend to hydrate UI on page load, project switching, or refresh
    WITHOUT triggering an expensive LLM generation turn.
    """
    repo = FirestoreRepository()
    try:
        project_data = repo.get_project(user_id=user_id, project_id=project_id)
        if not project_data:
            raise HTTPException(
                status_code=404,
                detail=f"Project '{project_id}' not found for user '{user_id}'."
            )

        response_payload = {
            "status": "success",
            "project": project_data,
        }

        if include_messages:
            messages = repo.get_messages(user_id=user_id, project_id=project_id, limit=50)
            response_payload["messages"] = messages

        return response_payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")


# -----------------------------------------------------------------------------
# 4. USER PROJECTS LIST (Sidebar Project Switcher)
# -----------------------------------------------------------------------------
@router.get("/users/{user_id}/projects")
async def list_user_projects_endpoint(
    user_id: str,
) -> dict[str, Any]:
    """
    Lists all projects owned by a user.
    Powers the frontend sidebar project selector.
    """
    repo = FirestoreRepository()
    try:
        projects = repo.list_projects(user_id=user_id)
        return {
            "status": "success",
            "user_id": user_id,
            "count": len(projects),
            "projects": projects,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")
