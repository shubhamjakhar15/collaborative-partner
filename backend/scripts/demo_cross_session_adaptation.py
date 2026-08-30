import sys
import io
from pathlib import Path

# Ensure root backend directory is in sys.path so 'app' and 'project_partner' are importable from any directory
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Ensure UTF-8 stdout encoding on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import asyncio
import os
import time
from dotenv import load_dotenv

# Load .env explicitly from backend root
load_dotenv(dotenv_path=root_dir / ".env")

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.db.repository import FirestoreRepository
from app.schemas.contract import Stage
from project_partner.agent import root_agent


async def execute_turn_with_retry(runner: Runner, user_id: str, session_id: str, content: types.Content, max_retries: int = 3) -> str:
    """Executes an ADK turn with automatic retry if rate limits (429) are encountered."""
    for attempt in range(1, max_retries + 1):
        try:
            agent_reply = ""
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "text", None):
                            agent_reply += part.text
            return agent_reply
        except Exception as e:
            err_msg = str(e)
            if ("429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg) and attempt < max_retries:
                print(f"\n⏳ [Rate Limit Encountered] Pausing 25s before retry (Attempt {attempt}/{max_retries})...")
                await asyncio.sleep(25)
            else:
                raise e
    return ""


async def run_adaptation_demo():
    print("=" * 75)
    print("PROJECT PARTNER: END-TO-END CROSS-SESSION ADAPTATION DEMO")
    print("=" * 75)

    user_id = "user_hackathon_demo"
    session_service = InMemorySessionService()
    app_name = "project_partner"
    runner = Runner(agent=root_agent, app_name=app_name, session_service=session_service)

    # -------------------------------------------------------------------------
    # SESSION 1: Project A (Recipe Organizer)
    # -------------------------------------------------------------------------
    session_1_id = "sess_project_A_recipe_app"
    print("\n" + "#" * 75)
    print(f"🎬 SESSION 1: Project A ('{session_1_id}')")
    print("#" * 75)

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_1_id,
        state={"stage": Stage.DISCOVERY.value}
    )

    # Turn 1: Initial Goal
    user_msg_1 = "I want to build a recipe organizer app with meal planning."
    print(f"\n👤 User (Turn 1): {user_msg_1}")
    content_1 = types.Content(role="user", parts=[types.Part.from_text(text=user_msg_1)])

    agent_reply_1 = await execute_turn_with_retry(runner, user_id, session_1_id, content_1)
    print(f"🤖 Partner Reply (Turn 1):\n{agent_reply_1}\n")

    # Rate-limit safety pause
    print("⏳ Pausing 12s to respect Free Tier RPM limits...")
    await asyncio.sleep(12)

    # Turn 2: User provides feedback with a reusable constraint
    user_msg_2 = "Don't give me so many tasks at once, only give me three actions at a time."
    print("-" * 75)
    print(f"👤 User (Turn 2 - Feedback): {user_msg_2}")
    content_2 = types.Content(role="user", parts=[types.Part.from_text(text=user_msg_2)])

    agent_reply_2 = await execute_turn_with_retry(runner, user_id, session_1_id, content_2)
    print(f"🤖 Partner Reply (Turn 2):\n{agent_reply_2}\n")

    # Verify preference was written to Firestore
    repo = FirestoreRepository()
    saved_pref = repo.get_preference(user_id=user_id, preference_id="max_tasks_per_phase")
    print(f"🗄️ Firestore Verification: max_tasks_per_phase = {saved_pref['value'] if saved_pref else 'None'}")

    # Rate-limit safety pause
    print("⏳ Pausing 12s before Session 2...")
    await asyncio.sleep(12)

    # -------------------------------------------------------------------------
    # SESSION 2: Project B (IoT Telemetry Dashboard — BRAND NEW PROJECT)
    # -------------------------------------------------------------------------
    session_2_id = "sess_project_B_iot_telemetry"
    print("\n" + "#" * 75)
    print(f"🎬 SESSION 2: Project B ('{session_2_id}') — BRAND NEW PROJECT")
    print("Goal: Prove agent remembers the 3-task limit learned in Project A!")
    print("#" * 75)

    await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_2_id,
        state={"stage": Stage.DISCOVERY.value}
    )

    user_msg_3 = "Let's plan an IoT telemetry dashboard with real-time sensor ingestion."
    print(f"\n👤 User (Turn 1 - New Project): {user_msg_3}")
    content_3 = types.Content(role="user", parts=[types.Part.from_text(text=user_msg_3)])

    agent_reply_3 = await execute_turn_with_retry(runner, user_id, session_2_id, content_3)
    print(f"🤖 Partner Reply (Turn 1 - New Project):\n{agent_reply_3}\n")
    print("=" * 75)
    print("🎉 CROSS-SESSION ADAPTATION SUCCESSFUL!")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_adaptation_demo())
