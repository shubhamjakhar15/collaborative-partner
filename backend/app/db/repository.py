import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional
from dotenv import load_dotenv
from google.cloud import firestore

load_dotenv()
logger = logging.getLogger("project_partner.db")

# Whitelisted preference keys allowed to be stored in the database
WHITELISTED_PREFERENCE_KEYS = {
    # Communication & Interaction Style
    "response_length",               # e.g. "concise", "detailed", "bullet_points"
    "communication_tone",            # e.g. "direct", "collaborative", "formal"
    "include_code_examples",         # bool: True / False
    "notes_format",                  # e.g. "markdown_bullets", "structured_table"
    # Planning & Workflow Style
    "planning_style",                # e.g. "step_by_step", "upfront_detailed", "iterative"
    "include_tradeoffs",             # bool: True / False
    "max_tasks_per_phase",           # int: 3, 5, etc.
    # Technical Profile & Defaults
    "technical_depth",               # e.g. "expert", "intermediate", "beginner"
    "preferred_language_or_stack",   # e.g. "Python + FastAPI", "TypeScript + Next.js"
    "target_cloud_provider",         # e.g. "GCP", "AWS", "Firebase"
    # Legacy / alias keys
    "preferred_stack",
    "experience_level",
    "theme",
}

# Trivial phrases that should NOT be persisted as user preferences
TRIVIAL_STATEMENTS = {
    "ok", "okay", "yes", "yeah", "yep", "sure", "sounds good",
    "cool", "nice", "great", "thanks", "thank you", "k", "got it", "fine"
}


class LocalDocumentRef:
    def __init__(self, storage: dict, path: str):
        self.storage = storage
        self.path = path

    def set(self, data: dict, merge: bool = False):
        if merge and self.path in self.storage:
            self.storage[self.path].update(data)
        else:
            self.storage[self.path] = data.copy()

    def get(self):
        exists = self.path in self.storage
        data = self.storage.get(self.path, {})
        from unittest.mock import MagicMock
        mock_snapshot = MagicMock()
        mock_snapshot.exists = exists
        mock_snapshot.to_dict.return_value = data.copy() if exists else None
        return mock_snapshot

    def delete(self):
        if self.path in self.storage:
            del self.storage[self.path]

    def collection(self, col_name: str):
        return LocalCollectionRef(self.storage, f"{self.path}/{col_name}")


class LocalCollectionRef:
    def __init__(self, storage: dict, path: str):
        self.storage = storage
        self.path = path

    def document(self, doc_id: str):
        return LocalDocumentRef(self.storage, f"{self.path}/{doc_id}")

    def order_by(self, field: str, direction=None):
        return self

    def limit(self, count: int):
        return self

    def stream(self):
        from unittest.mock import MagicMock
        docs = []
        prefix = f"{self.path}/"
        for k, v in list(self.storage.items()):
            if k.startswith(prefix) and "/" not in k[len(prefix):]:
                mock_snap = MagicMock()
                mock_snap.to_dict.return_value = v.copy()
                docs.append(mock_snap)
        return docs


class LocalFirestoreClient:
    """Seamless in-memory Firestore client for zero-config local development and testing."""
    def __init__(self):
        self.storage: dict[str, dict] = {}

    def collection(self, col_name: str):
        return LocalCollectionRef(self.storage, col_name)


_db_client: Optional[Any] = None


def get_db_client() -> Any:
    """Returns a singleton Firestore client instance with seamless local fallback."""
    global _db_client
    if _db_client is None:
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "project-partner-dev")
            _db_client = firestore.Client(project=project_id)
        except Exception:
            logger.info("GCP Cloud Credentials not found. Using seamless local in-memory Firestore client.")
            _db_client = LocalFirestoreClient()
    return _db_client


def reset_db_client(client: Optional[Any] = None) -> None:
    """Reset or inject a custom client (useful for unit tests/fixtures)."""
    global _db_client
    _db_client = client


class FirestoreRepository:
    """
    Dedicated Firestore repository encapsulating all database interactions.
    Enforces hierarchical collection paths:
      - users/{user_id}
      - users/{user_id}/preferences/{preference_id}
      - users/{user_id}/projects/{project_id}
      - users/{user_id}/projects/{project_id}/messages/{message_id}
      - users/{user_id}/projects/{project_id}/feedback/{feedback_id}
    """

    def __init__(self, client: Optional[Any] = None):
        self._client = client

    @property
    def client(self) -> Any:
        return self._client or get_db_client()

    # -------------------------------------------------------------------------
    # 1. USER OPERATIONS
    # -------------------------------------------------------------------------
    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a user document by ID."""
        doc_ref = self.client.collection("users").document(user_id)
        snap = doc_ref.get()
        return snap.to_dict() if snap.exists else None

    def set_user(self, user_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """Creates or updates a user document."""
        data_to_save = data.copy()
        data_to_save["user_id"] = user_id
        data_to_save["updated_at"] = datetime.now(timezone.utc).isoformat()
        if "created_at" not in data_to_save:
            data_to_save["created_at"] = datetime.now(timezone.utc).isoformat()

        doc_ref = self.client.collection("users").document(user_id)
        doc_ref.set(data_to_save, merge=True)
        return data_to_save

    def delete_user(self, user_id: str) -> None:
        """Deletes a user document."""
        self.client.collection("users").document(user_id).delete()

    # -------------------------------------------------------------------------
    # 2. USER PREFERENCES OPERATIONS (Subcollection: users/{u}/preferences/{k})
    # -------------------------------------------------------------------------
    def get_preference(self, user_id: str, preference_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a specific user preference."""
        doc_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("preferences")
            .document(preference_id)
        )
        snap = doc_ref.get()
        return snap.to_dict() if snap.exists else None

    def get_all_preferences(self, user_id: str) -> list[dict[str, Any]]:
        """Retrieves all stored preferences for a user."""
        col_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("preferences")
        )
        docs = col_ref.stream()
        return [doc.to_dict() for doc in docs if doc.to_dict() is not None]

    def set_preference(
        self,
        user_id: str,
        preference_id: str,
        value: Any,
        category: str = "general",
        confidence: float = 1.0,
        source: str = "explicit_user_statement",
        evidence: Optional[str] = None,
        source_turn: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Stores a validated user preference.
        Enforces whitelisting and rejects trivial statements.
        """
        if preference_id not in WHITELISTED_PREFERENCE_KEYS:
            raise ValueError(
                f"Invalid preference key: '{preference_id}'. Allowed preference keys: "
                f"{sorted(WHITELISTED_PREFERENCE_KEYS)}"
            )

        if isinstance(value, str) and value.strip().lower() in TRIVIAL_STATEMENTS:
            raise ValueError(
                f"Refusing to save trivial confirmation '{value}' as user preference."
            )

        pref_data = {
            "key": preference_id,
            "value": value,
            "category": category,
            "confidence": float(confidence),
            "source": source,
            "evidence": evidence,
            "source_turn": source_turn,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        doc_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("preferences")
            .document(preference_id)
        )
        doc_ref.set(pref_data, merge=True)
        return pref_data

    def delete_preference(self, user_id: str, preference_id: str) -> None:
        """Deletes a user preference document."""
        (
            self.client.collection("users")
            .document(user_id)
            .collection("preferences")
            .document(preference_id)
            .delete()
        )

    # -------------------------------------------------------------------------
    # 3. PROJECT ROADMAP OPERATIONS (Subcollection: users/{u}/projects/{p})
    # -------------------------------------------------------------------------
    def get_project(self, user_id: str, project_id: str) -> Optional[dict[str, Any]]:
        """Retrieves a project document."""
        doc_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
        )
        snap = doc_ref.get()
        return snap.to_dict() if snap.exists else None

    def list_projects(self, user_id: str) -> list[dict[str, Any]]:
        """Lists all projects for a user."""
        col_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
        )
        docs = col_ref.stream()
        return [doc.to_dict() for doc in docs if doc.to_dict() is not None]

    def set_project(
        self,
        user_id: str,
        project_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """Creates or updates a project roadmap document."""
        data_to_save = data.copy()
        data_to_save["project_id"] = project_id
        data_to_save["updated_at"] = datetime.now(timezone.utc).isoformat()
        if "created_at" not in data_to_save:
            data_to_save["created_at"] = datetime.now(timezone.utc).isoformat()

        doc_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
        )
        doc_ref.set(data_to_save, merge=True)
        return data_to_save

    def delete_project(self, user_id: str, project_id: str) -> None:
        """Deletes a project document."""
        self.client.collection("users").document(user_id).collection("projects").document(project_id).delete()

    # -------------------------------------------------------------------------
    # 4. CONVERSATIONAL MESSAGE LOGS (users/{u}/projects/{p}/messages/{m})
    # -------------------------------------------------------------------------
    def save_message(
        self,
        user_id: str,
        project_id: str,
        message_id: str,
        role: str,
        content: str,
        stage: Optional[str] = None,
    ) -> dict[str, Any]:
        """Appends a message record to the project's messages subcollection."""
        msg_data = {
            "message_id": message_id,
            "role": role,
            "content": content,
            "stage": stage,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        doc_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("messages")
            .document(message_id)
        )
        doc_ref.set(msg_data)
        return msg_data

    def get_messages(
        self,
        user_id: str,
        project_id: str,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Retrieves recent conversation messages for a project."""
        col_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("messages")
        )
        docs = col_ref.order_by("created_at").limit(limit).stream()
        return [doc.to_dict() for doc in docs if doc.to_dict() is not None]

    def delete_message(self, user_id: str, project_id: str, message_id: str) -> None:
        """Deletes a message document."""
        (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("messages")
            .document(message_id)
            .delete()
        )

    # -------------------------------------------------------------------------
    # 5. FEEDBACK LOGS (users/{u}/projects/{p}/feedback/{f})
    # -------------------------------------------------------------------------
    def save_feedback(
        self,
        user_id: str,
        project_id: str,
        feedback_id: str,
        feedback_type: str,
        details: str,
        resolution: Optional[str] = None,
    ) -> dict[str, Any]:
        """Stores a feedback audit entry for a project."""
        fb_data = {
            "feedback_id": feedback_id,
            "feedback_type": feedback_type,
            "details": details,
            "resolution": resolution,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        doc_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("feedback")
            .document(feedback_id)
        )
        doc_ref.set(fb_data)
        return fb_data

    def get_feedback_records(
        self,
        user_id: str,
        project_id: str
    ) -> list[dict[str, Any]]:
        """Retrieves all feedback records for a project."""
        col_ref = (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("feedback")
        )
        docs = col_ref.stream()
        return [doc.to_dict() for doc in docs if doc.to_dict() is not None]

    def delete_feedback(self, user_id: str, project_id: str, feedback_id: str) -> None:
        """Deletes a feedback document."""
        (
            self.client.collection("users")
            .document(user_id)
            .collection("projects")
            .document(project_id)
            .collection("feedback")
            .document(feedback_id)
            .delete()
        )
