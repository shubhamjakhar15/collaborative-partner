import base64
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from dotenv import load_dotenv
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.db.repository import FirestoreRepository
from app.schemas.contract import (
    Stage,
    Intent,
    StepStatus,
    PlanStep,
    Plan,
    QuestionItem,
    MemoryType,
    MemoryUpdate,
    FileAttachment,
    ChatRequest,
    ChatResponse,
)
from project_partner.agent import root_agent

load_dotenv()
logger = logging.getLogger("project_partner.service")


class AgentService:
    """
    Core business orchestration service for Project Partner.
    Manages the ADK Runner, session lifecycle per request, and maps
    conversational events into strongly-typed ChatResponse objects.
    """

    def __init__(self, session_service: Optional[InMemorySessionService] = None):
        self.app_name = "project_partner"
        self.session_service = session_service or InMemorySessionService()
        self.runner = Runner(
            agent=root_agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

    async def process_chat(self, req: ChatRequest) -> ChatResponse:
        """
        Executes a single chat turn with comprehensive error hardening:
        1. Ensures session is initialized in SessionService.
        2. Ingests and persists incoming file/image attachments.
        3. Dispatches user message and multimodal parts to ADK Runner with fallback error recovery.
        4. Collects generated tokens and inspects resulting session state.
        5. Hydrates project memory, files & logs message to Firestore repository.
        6. Returns strongly-typed ChatResponse.
        """
        user_id = req.user_id
        project_id = req.project_id or req.session_id or "default_project"
        user_message = req.message
        turn_id = f"turn_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        repo = FirestoreRepository()

        # 1. Retrieve or Initialize ADK Session
        try:
            session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=project_id,
            )
            if not session:
                session = await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=project_id,
                    state={"stage": Stage.DISCOVERY.value, "turn_count": 0},
                )
                
                # Auto-initialize the project in Firestore with the first message as title
                title_snippet = (user_message[:40] + "...") if len(user_message) > 40 else user_message
                try:
                    proj_exists = repo.get_project(user_id, project_id)
                    if not proj_exists or not proj_exists.get("title"):
                        repo.set_project(
                            user_id=user_id,
                            project_id=project_id,
                            data={"title": title_snippet}
                        )
                except Exception as e:
                    logger.warning(f"Failed to auto-initialize project document: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize session for project '{project_id}': {e}")
            session = None

        # 2. Process and persist any attached files/images
        parts = []
        saved_attachments = []
        if req.attachments:
            for att in req.attachments:
                file_id = att.id or f"file_{uuid.uuid4().hex[:12]}"
                file_record = {
                    "id": file_id,
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "size": att.size,
                    "data_base64": att.data_base64,
                    "url": att.url,
                    "summary": att.summary,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                }
                # Persist to project files repository
                try:
                    repo.save_file(user_id=user_id, project_id=project_id, file_id=file_id, data=file_record)
                    saved_attachments.append(file_record)
                except Exception as e:
                    logger.warning(f"Failed to persist file '{att.filename}': {e}")

                # Build multimodal GenAI parts
                if att.data_base64:
                    try:
                        raw_bytes = base64.b64decode(att.data_base64)
                        if att.content_type.startswith("image/"):
                            parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=att.content_type))
                        else:
                            try:
                                text_content = raw_bytes.decode("utf-8", errors="replace")
                                parts.append(types.Part.from_text(text=f"[Attached File: {att.filename} ({att.content_type})]\n{text_content}"))
                            except Exception:
                                parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=att.content_type))
                    except Exception as e:
                        logger.warning(f"Failed to decode attachment '{att.filename}': {e}")
                        if att.summary:
                            parts.append(types.Part.from_text(text=f"[Attached File Summary: {att.filename}]\n{att.summary}"))
                elif att.summary:
                    parts.append(types.Part.from_text(text=f"[Attached File Summary: {att.filename}]\n{att.summary}"))

        # Add the conversational text prompt
        parts.append(types.Part.from_text(text=user_message))

        # 3. Log incoming user message to Firestore with attachments
        try:
            repo.save_message(
                user_id=user_id,
                project_id=project_id,
                message_id=f"msg_user_{turn_id}",
                role="user",
                content=user_message,
                stage=session.state.get("stage", Stage.DISCOVERY.value) if session else Stage.DISCOVERY.value,
                attachments=saved_attachments,
            )
        except Exception as e:
            logger.warning(f"Failed to log user message to Firestore: {e}")

        # 4. Dispatch to ADK Runner with Multimodal Parts
        agent_text = ""
        try:
            content = types.Content(
                role="user",
                parts=parts,
            )

            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=project_id,
                new_message=content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            agent_text += part.text
        except Exception as e:
            logger.error(f"Error during ADK Runner execution: {e}", exc_info=True)
            # Fallback gracefully with in-character response rather than an unhandled 500 crash
            agent_text = (
                "I encountered a temporary connection issue communicating with the AI service. "
                "I've preserved our notes, files, and project context. Please retry your message."
            )

        # 4. Fetch updated session state safely
        state_dict = {}
        try:
            updated_session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=project_id,
            )
            if updated_session:
                state_dict = updated_session.state
        except Exception as e:
            logger.warning(f"Failed to retrieve updated session state: {e}")

        current_stage_str = state_dict.get("stage", Stage.DISCOVERY.value)
        try:
            current_stage = Stage(current_stage_str)
        except ValueError:
            current_stage = Stage.DISCOVERY

        feedback_detected = state_dict.get("feedback_detected", False)

        # 5. Fetch project roadmap from Firestore if available
        project_plan: Optional[Plan] = None
        try:
            proj_data = repo.get_project(user_id=user_id, project_id=project_id)
            if proj_data and "current_plan" in proj_data:
                raw_plan = proj_data["current_plan"]
                steps_data = []
                for s in raw_plan.get("steps", []):
                    try:
                        status_enum = StepStatus(s.get("status", "pending"))
                    except ValueError:
                        status_enum = StepStatus.PENDING

                    steps_data.append(
                        PlanStep(
                            id=s.get("id", "step_1"),
                            description=s.get("description", "Execute task"),
                            status=status_enum,
                            assignee=s.get("assignee", "agent"),
                        )
                    )
                project_plan = Plan(
                    title=raw_plan.get("title", proj_data.get("title", "Project Plan")),
                    summary=raw_plan.get("summary", ""),
                    steps=steps_data,
                    version=raw_plan.get("version", 1),
                )
        except Exception as e:
            logger.warning(f"Failed to parse project plan from Firestore: {e}")
            project_plan = None

        # 6. Determine Fine-Grained Intent
        if feedback_detected:
            intent = Intent.PROCESS_FEEDBACK
        elif current_stage == Stage.DISCOVERY:
            intent = Intent.DISCOVER_CONTEXT
        elif current_stage == Stage.CLARIFICATION:
            intent = Intent.CLARIFY_GOAL
        elif current_stage in (Stage.PLANNING, Stage.ADAPTATION):
            intent = Intent.GENERATE_PLAN
        elif current_stage == Stage.REVIEW:
            intent = Intent.REQUEST_REVIEW
        elif current_stage == Stage.EXECUTION:
            intent = Intent.EXECUTE_STEP
        else:
            intent = Intent.GENERAL_CHAT

        # 7. Extract Note Updates for Response Contract
        memory_updates = []
        adaptation_event = state_dict.get("last_adaptation_event")
        if adaptation_event:
            memory_updates.append(
                MemoryUpdate(
                    id=f"mem_{turn_id}",
                    type=MemoryType.PREFERENCE if "user preference" in adaptation_event else MemoryType.DECISION,
                    content=adaptation_event,
                )
            )

        # 8. Determine Next Action Guidance
        if current_stage == Stage.DISCOVERY:
            next_action = "Awaiting user response to explore project domain and objectives."
        elif current_stage == Stage.CLARIFICATION:
            next_action = "Awaiting answers to technical constraints and scope clarification questions."
        elif current_stage == Stage.PLANNING:
            next_action = "Review the proposed sequential roadmap."
        elif current_stage == Stage.REVIEW:
            next_action = "Awaiting user approval to proceed with execution."
        elif current_stage == Stage.ADAPTATION:
            next_action = "Reviewing adapted roadmap changes based on feedback."
        else:
            next_action = "Continue collaborative dialogue."

        # 9. Log assistant response to Firestore
        try:
            repo.save_message(
                user_id=user_id,
                project_id=project_id,
                message_id=f"msg_agent_{turn_id}",
                role="agent",
                content=agent_text,
                stage=current_stage.value,
            )
        except Exception:
            pass

        # 10. Hydrate All Project Files
        project_files_data: list[FileAttachment] = []
        try:
            raw_files = repo.get_files(user_id=user_id, project_id=project_id)
            for f in raw_files:
                project_files_data.append(
                    FileAttachment(
                        id=f.get("id"),
                        filename=f.get("filename", "unnamed_file"),
                        content_type=f.get("content_type", "application/octet-stream"),
                        size=f.get("size"),
                        data_base64=f.get("data_base64"),
                        url=f.get("url"),
                        summary=f.get("summary"),
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to fetch project files: {e}")

        return ChatResponse(
            project_id=project_id,
            message=agent_text or "I am ready to assist with your project.",
            stage=current_stage,
            intent=intent,
            questions=[],
            plan=project_plan,
            feedback_detected=feedback_detected,
            memory_updates=memory_updates,
            attachments=req.attachments,
            project_files=project_files_data,
            next_action=next_action,
            requires_user_input=True,
        )

    async def process_chat_stream(self, req: ChatRequest):
        """
        Executes a chat turn and yields Server-Sent Events (SSE) for streaming text chunks.
        Yields a final event containing metadata (plan, memory, stage, etc.).
        """
        import json
        user_id = req.user_id
        project_id = req.project_id or req.session_id or "default_project"
        user_message = req.message
        turn_id = f"turn_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        repo = FirestoreRepository()

        # 1. Retrieve or Initialize ADK Session
        try:
            session = await self.session_service.get_session(
                app_name=self.app_name,
                user_id=user_id,
                session_id=project_id,
            )
            if not session:
                session = await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=project_id,
                    state={"stage": Stage.DISCOVERY.value, "turn_count": 0},
                )
                
                # Auto-initialize the project in Firestore with the first message as title
                title_snippet = (user_message[:40] + "...") if len(user_message) > 40 else user_message
                try:
                    proj_exists = repo.get_project(user_id, project_id)
                    if not proj_exists or not proj_exists.get("title"):
                        repo.set_project(
                            user_id=user_id,
                            project_id=project_id,
                            data={"title": title_snippet}
                        )
                except Exception as e:
                    logger.warning(f"Failed to auto-initialize project document: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize session: {e}")
            session = None

        # 2. Process attachments
        parts = []
        saved_attachments = []
        if req.attachments:
            for att in req.attachments:
                file_id = att.id or f"file_{uuid.uuid4().hex[:12]}"
                file_record = {
                    "id": file_id,
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "size": att.size,
                    "data_base64": att.data_base64,
                    "url": att.url,
                    "summary": att.summary,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    repo.save_file(user_id=user_id, project_id=project_id, file_id=file_id, data=file_record)
                    saved_attachments.append(file_record)
                except Exception:
                    pass

                if att.data_base64:
                    try:
                        raw_bytes = base64.b64decode(att.data_base64)
                        if att.content_type.startswith("image/"):
                            parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=att.content_type))
                        else:
                            parts.append(types.Part.from_bytes(data=raw_bytes, mime_type=att.content_type))
                    except Exception:
                        pass
                elif att.summary:
                    parts.append(types.Part.from_text(text=f"[Attached File Summary: {att.filename}]\n{att.summary}"))

        parts.append(types.Part.from_text(text=user_message))

        # 3. Log user message
        try:
            repo.save_message(
                user_id=user_id,
                project_id=project_id,
                message_id=f"msg_user_{turn_id}",
                role="user",
                content=user_message,
                stage=session.state.get("stage", Stage.DISCOVERY.value) if session else Stage.DISCOVERY.value,
                attachments=saved_attachments,
            )
        except Exception:
            pass

        # 4. Dispatch to ADK Runner and YIELD STREAM CHUNKS
        agent_text = ""
        import asyncio
        try:
            content = types.Content(role="user", parts=parts)
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=project_id,
                new_message=content,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            text_chunk = part.text
                            agent_text += text_chunk
                            
                            # Artificially stream the chunk so it appears word-by-word
                            # This bypasses any internal ADK/Model buffering
                            chunk_size = 8
                            for i in range(0, len(text_chunk), chunk_size):
                                tiny_chunk = text_chunk[i:i+chunk_size]
                                yield f"data: {json.dumps({'type': 'chunk', 'text': tiny_chunk})}\n\n"
                                await asyncio.sleep(0.02)
                                
        except Exception as e:
            logger.error(f"Error during ADK Runner execution: {e}")
            fallback_text = "I encountered a connection issue. Please retry."
            agent_text += fallback_text
            for i in range(0, len(fallback_text), 8):
                yield f"data: {json.dumps({'type': 'chunk', 'text': fallback_text[i:i+8]})}\n\n"
                await asyncio.sleep(0.02)

        # 5. Fetch updated session state safely
        state_dict = {}
        try:
            updated_session = await self.session_service.get_session(
                app_name=self.app_name, user_id=user_id, session_id=project_id
            )
            if updated_session:
                state_dict = updated_session.state
        except Exception:
            pass

        current_stage_str = state_dict.get("stage", Stage.DISCOVERY.value)
        try:
            current_stage = Stage(current_stage_str)
        except ValueError:
            current_stage = Stage.DISCOVERY

        feedback_detected = state_dict.get("feedback_detected", False)

        # 6. Fetch project roadmap
        project_plan = None
        try:
            proj_data = repo.get_project(user_id=user_id, project_id=project_id)
            if proj_data and "current_plan" in proj_data:
                project_plan = proj_data["current_plan"] # dictionary form is fine for json serialization
        except Exception:
            pass

        # 7. Extract Note Updates
        memory_updates = []
        adaptation_event = state_dict.get("last_adaptation_event")
        if adaptation_event:
            memory_updates.append({
                "id": f"mem_{turn_id}",
                "type": "preference" if "user preference" in adaptation_event else "decision",
                "content": adaptation_event,
            })

        # 8. Log assistant response
        try:
            repo.save_message(
                user_id=user_id,
                project_id=project_id,
                message_id=f"msg_agent_{turn_id}",
                role="agent",
                content=agent_text,
                stage=current_stage.value,
            )
        except Exception:
            pass

        # 9. Yield FINAL metadata event
        final_metadata = {
            "type": "metadata",
            "message_id": f"msg_agent_{turn_id}",
            "stage": current_stage.value,
            "plan": project_plan,
            "feedback_detected": feedback_detected,
            "memory_updates": memory_updates,
        }
        yield f"data: {json.dumps(final_metadata)}\n\n"

_agent_service: Optional[AgentService] = None

def get_agent_service() -> AgentService:
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service
