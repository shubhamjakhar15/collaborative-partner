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
    include_files: bool = Query(default=True, description="Whether to include project files/images"),
) -> dict[str, Any]:
    """
    Retrieves project roadmap, goals, constraints, decisions, files, and chat history.
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

        if include_files:
            files = repo.get_files(user_id=user_id, project_id=project_id)
            response_payload["files"] = files

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


# -----------------------------------------------------------------------------
# 5. PROJECT FILES & IMAGES (Persistent Multi-Modal Assets)
# -----------------------------------------------------------------------------
@router.get("/users/{user_id}/projects/{project_id}/files")
async def list_project_files_endpoint(
    user_id: str,
    project_id: str,
) -> dict[str, Any]:
    """
    Retrieves all persistent files and images uploaded to a project.
    """
    repo = FirestoreRepository()
    try:
        files = repo.get_files(user_id=user_id, project_id=project_id)
        return {
            "status": "success",
            "user_id": user_id,
            "project_id": project_id,
            "count": len(files),
            "files": files,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list project files: {str(e)}")


@router.post("/users/{user_id}/projects/{project_id}/files")
async def upload_project_file_endpoint(
    user_id: str,
    project_id: str,
    file_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Persists an uploaded file/image metadata and data in project memory.
    """
    repo = FirestoreRepository()
    try:
        import uuid
        file_id = file_payload.get("id") or f"file_{uuid.uuid4().hex[:12]}"
        saved_file = repo.save_file(
            user_id=user_id,
            project_id=project_id,
            file_id=file_id,
            data=file_payload,
        )
        return {
            "status": "success",
            "file": saved_file,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.delete("/users/{user_id}/projects/{project_id}/files/{file_id}")
async def delete_project_file_endpoint(
    user_id: str,
    project_id: str,
    file_id: str,
) -> dict[str, Any]:
    """
    Deletes a file attachment from project memory.
    """
    repo = FirestoreRepository()
    try:
        repo.delete_file(user_id=user_id, project_id=project_id, file_id=file_id)
        return {
            "status": "success",
            "message": f"File '{file_id}' deleted successfully.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
