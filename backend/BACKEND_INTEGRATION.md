# 🚀 Project Partner — Frontend Integration Guide

Welcome! This document contains everything you need to connect your frontend (Next.js, React, Vite, etc.) to the **Project Partner AI Backend**.

You do **not** need to understand the internal AI agent implementation, Google ADK, or database internals. You only interact with standard JSON REST endpoints.

---

## 🌐 1. Server & Connection Setup

* **Base URL (Local Development)**: `http://127.0.0.1:8000`
* **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
* **CORS**: Enabled for all origins (`*`), headers, and methods.
* **Content-Type**: Always send `Content-Type: application/json`.

### Running the Backend Locally
```bash
# In the backend directory:
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

---

## 🔑 2. ID & Session Conventions

| Parameter | Type | Required | Description & Recommended Pattern |
| :--- | :--- | :--- | :--- |
| `user_id` | `string` | Optional (default: `"demo-user"`) | Unique identifier for the user (e.g. `"user_alice"`, `"demo-user"`). Reusable preferences attach to this ID. |
| `project_id` | `string` | **Required** | Unique identifier for a project session (e.g. `"proj_whiteboard_app"`, `"recipe-organizer-01"`). State, roadmap, and chat history attach to this ID. |

---

## 📡 3. API Endpoints Overview

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/chat` | **Main conversational endpoint**. Sends user message and receives structured AI response. |
| `GET` | `/users/{user_id}/preferences` | **Memory Vault**: Fetches cross-project user preferences to display in a settings/profile drawer. |
| `GET` | `/users/{user_id}/projects/{project_id}` | **Page Hydration**: Fetches saved project roadmap and message history on page reload or project switch. |
| `GET` | `/users/{user_id}/projects` | **Project Switcher**: Lists all projects belonging to the user. |
| `GET` | `/health` | Health check endpoint returning `{"status": "ok"}`. |

---

## 📋 4. TypeScript Interfaces

```typescript
// --- REQUEST CONTRACT ---
export interface ChatRequest {
  user_id?: string;               // e.g. "demo-user"
  project_id: string;              // e.g. "project-001"
  message: string;                 // User input text
  metadata?: Record<string, any>; // Optional client metadata
}

// --- ENUMS ---
export type Stage = 
  | "discovery"
  | "clarification"
  | "planning"
  | "review"
  | "feedback"
  | "adaptation"
  | "execution"
  | "complete";

export type Intent =
  | "discover_context"
  | "clarify_goal"
  | "generate_plan"
  | "request_review"
  | "process_feedback"
  | "adapt_plan"
  | "execute_step"
  | "summarize"
  | "general_chat";

export type StepStatus = "pending" | "in_progress" | "completed" | "blocked";

// --- RESPONSE CONTRACT ---
export interface PlanStep {
  id: string;                      // e.g. "step_1"
  description: string;             // Actionable task
  status: StepStatus;              // "pending" | "in_progress" | "completed" | "blocked"
  assignee: "agent" | "user";      // Who owns the task
}

export interface Plan {
  title: string;                   // Plan name
  summary: string;                 // High-level summary
  steps: PlanStep[];               // Ordered task list
  version: number;                 // Incremented on revision (1, 2, 3...)
}

export interface QuestionItem {
  id: string;                      // e.g. "q1"
  text: string;                    // The question prompt
  options?: string[];              // Suggested choices if applicable
  is_optional: boolean;
}

export interface MemoryUpdate {
  id: string;
  type: "decision" | "constraint" | "preference" | "note";
  content: string;                 // e.g. "Saved user preference: max_tasks_per_phase = 3"
  timestamp: string;
}

export interface ChatResponse {
  project_id: string;
  message: string;                 // Conversational AI message to render in chat
  stage: Stage;                    // Active project lifecycle stage
  intent: Intent;                  // Fine-grained turn intent
  questions: QuestionItem[];       // Interactive questions if present
  plan: Plan | null;               // Structured roadmap if active/updated
  feedback_detected: boolean;      // True if user gave feedback or critique
  memory_updates: MemoryUpdate[];  // Notes or preferences captured this turn
  next_action: string;             // Suggested next step
  requires_user_input: boolean;   // True if awaiting user reply
  timestamp: string;
}

// --- ERROR CONTRACT ---
export interface ErrorResponse {
  error: "validation_error" | "http_error" | "internal_server_error";
  message: string;
  detail?: any;
  status_code: number;
  timestamp: string;
}
```

---

## 💡 5. Concrete Request / Response Examples

### Example 1: Fresh Goal Submission
**Request**: `POST /chat`
```json
{
  "user_id": "demo-user",
  "project_id": "recipe-organizer-01",
  "message": "I want to build a smart recipe organizer app."
}
```

**Response**: `200 OK`
```json
{
  "project_id": "recipe-organizer-01",
  "message": "Exciting project! A smart recipe organizer can streamline meal preparation. To help shape our roadmap, could you share:\n1. Who is your primary target user (e.g., busy parents, fitness enthusiasts)?\n2. What platforms or tech stack do you prefer?",
  "stage": "discovery",
  "intent": "discover_context",
  "questions": [],
  "plan": null,
  "feedback_detected": false,
  "memory_updates": [],
  "next_action": "Awaiting user response to explore project domain and objectives.",
  "requires_user_input": true,
  "timestamp": "2026-08-30T07:30:00.000000Z"
}
```

---

### Example 2: Clarification & Tech Constraints
**Request**: `POST /chat`
```json
{
  "user_id": "demo-user",
  "project_id": "recipe-organizer-01",
  "message": "Target users are busy families. Preferred stack is Next.js, FastAPI, and PostgreSQL."
}
```

**Response**: `200 OK`
```json
{
  "project_id": "recipe-organizer-01",
  "message": "Got it! Busy families with a Next.js + FastAPI + PostgreSQL stack. I've drafted our initial implementation roadmap.",
  "stage": "planning",
  "intent": "generate_plan",
  "questions": [],
  "plan": {
    "title": "Recipe Organizer MVP",
    "summary": "Full-stack implementation plan for recipe collection and automated shopping list.",
    "steps": [
      {
        "id": "step_1",
        "description": "Design PostgreSQL database schema for recipes and ingredients.",
        "status": "pending",
        "assignee": "agent"
      },
      {
        "id": "step_2",
        "description": "Build FastAPI REST endpoints for recipe CRUD and meal scheduling.",
        "status": "pending",
        "assignee": "agent"
      },
      {
        "id": "step_3",
        "description": "Create Next.js responsive UI with drag-and-drop meal calendar.",
        "status": "pending",
        "assignee": "user"
      }
    ],
    "version": 1
  },
  "feedback_detected": false,
  "memory_updates": [],
  "next_action": "Review the proposed sequential roadmap.",
  "requires_user_input": true,
  "timestamp": "2026-08-30T07:31:00.000000Z"
}
```

---

### Example 3: User Feedback (Auto-Adaptation & Habit Persistence)
**Request**: `POST /chat`
```json
{
  "user_id": "demo-user",
  "project_id": "recipe-organizer-01",
  "message": "Don't give me so many tasks at once, only give me three actions at a time."
}
```

**Response**: `200 OK`
```json
{
  "project_id": "recipe-organizer-01",
  "message": "Understood! I have updated my global settings: I will cap all future roadmaps and action lists at 3 tasks maximum.",
  "stage": "planning",
  "intent": "process_feedback",
  "questions": [],
  "plan": null,
  "feedback_detected": true,
  "memory_updates": [
    {
      "id": "mem_turn_20260830_073200",
      "type": "preference",
      "content": "Saved user preference: max_tasks_per_phase = 3",
      "timestamp": "2026-08-30T07:32:00.000000Z"
    }
  ],
  "next_action": "Review the proposed sequential roadmap.",
  "requires_user_input": true,
  "timestamp": "2026-08-30T07:32:00.000000Z"
}
```

---

### Example 4: Fetch User Memory Vault (Profile / Settings Drawer)
**Request**: `GET /users/demo-user/preferences`

**Response**: `200 OK`
```json
{
  "status": "success",
  "user_id": "demo-user",
  "count": 2,
  "preferences": [
    {
      "key": "max_tasks_per_phase",
      "value": 3,
      "category": "planning",
      "confidence": 1.0,
      "source": "explicit_user_statement",
      "evidence": "Don't give me so many tasks at once, only give me three actions at a time.",
      "updated_at": "2026-08-30T07:32:00.000000Z"
    },
    {
      "key": "preferred_language_or_stack",
      "value": "Python + FastAPI",
      "category": "technical",
      "confidence": 0.95,
      "source": "explicit_user_statement",
      "evidence": "I always prefer Python with FastAPI for backend projects.",
      "updated_at": "2026-08-30T07:29:00.000000Z"
    }
  ]
}
```

---

### Example 5: Page Reload / Project Hydration
**Request**: `GET /users/demo-user/projects/recipe-organizer-01?include_messages=true`

**Response**: `200 OK`
```json
{
  "status": "success",
  "project": {
    "project_id": "recipe-organizer-01",
    "title": "Recipe Organizer MVP",
    "goal": "Organize weekly family meals with smart shopping list",
    "constraints": ["FastAPI", "Next.js", "PostgreSQL"],
    "current_stage": "planning",
    "current_plan": {
      "title": "Recipe Organizer MVP",
      "steps": [
        { "id": "step_1", "description": "Design PostgreSQL database schema", "status": "pending", "assignee": "agent" },
        { "id": "step_2", "description": "Build FastAPI REST endpoints", "status": "pending", "assignee": "agent" },
        { "id": "step_3", "description": "Create Next.js responsive UI", "status": "pending", "assignee": "user" }
      ],
      "version": 1
    },
    "updated_at": "2026-08-30T07:31:00.000000Z"
  },
  "messages": [
    {
      "message_id": "msg_user_1",
      "role": "user",
      "content": "I want to build a smart recipe organizer app.",
      "stage": "discovery",
      "created_at": "2026-08-30T07:30:00.000000Z"
    },
    {
      "message_id": "msg_agent_1",
      "role": "agent",
      "content": "Exciting project! ...",
      "stage": "discovery",
      "created_at": "2026-08-30T07:30:02.000000Z"
    }
  ]
}
```

---

### Example 6: Error Handling (Missing Field)
**Request**: `POST /chat` (missing `message` and `project_id`)
```json
{
  "user_id": "demo-user"
}
```

**Response**: `422 Unprocessable Entity`
```json
{
  "error": "validation_error",
  "message": "Request payload validation failed. Check request fields.",
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "message"],
      "msg": "Field required"
    },
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, Either project_id or session_id must be provided and non-empty."
    }
  ],
  "status_code": 422,
  "timestamp": "2026-08-30T07:33:00.000000Z"
}
```

---

## 🎨 6. UI Recommendations for Hackathon Presentation

1. **Left Sidebar**: List projects using `GET /users/{user_id}/projects` and let the user create a new project.
2. **Main Panel (Chat View)**: Display conversational messages from `POST /chat`. If `response.feedback_detected === true`, show a subtle toast notification: *"⚡ Habit Learned & Persisted"*.
3. **Right Sidebar (Active Roadmap & Notes)**: 
   - Render `response.plan` as an interactive checklist showing each task status (`pending`, `in_progress`, `completed`).
   - Render `response.memory_updates` as a live feed of decisions and constraints.
4. **Memory Vault Modal/Drawer**: Call `GET /users/{user_id}/preferences` to show the judge that preferences learned in Project 1 (e.g. `max_tasks_per_phase: 3`) carry over to a new Project 2 without re-prompting!
