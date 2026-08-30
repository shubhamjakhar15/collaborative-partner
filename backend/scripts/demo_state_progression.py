import sys
import io
from pathlib import Path

# Ensure root backend directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import asyncio
from dotenv import load_dotenv

load_dotenv(dotenv_path=root_dir / ".env")

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from app.schemas.contract import Stage
from project_partner.agent import root_agent


async def run_state_progression_demo():
    print("=" * 70)
    print("PROJECT PARTNER: ADK SESSION STATE & LIFECYCLE PROGRESSION DEMO")
    print("=" * 70)

    session_service = InMemorySessionService()
    app_name = "project_partner"
    user_id = "user_hackathon_demo"
    session_id = "sess_recipe_app_01"

    session = await session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id,
        state={
            "stage": Stage.DISCOVERY.value,
            "user:preferred_stack": "FastAPI + React",
            "app:version": "1.0.0-hackathon"
        }
    )

    runner = Runner(agent=root_agent, app_name=app_name, session_service=session_service)

    # TURN 1: DISCOVERY
    print("\n--- TURN 1: DISCOVERY ---")
    user_msg_1 = "I want to build a smart recipe organizer app."
    print(f"👤 User: {user_msg_1}")
    content_1 = types.Content(role="user", parts=[types.Part.from_text(text=user_msg_1)])

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content_1):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)

    session_t1 = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print(f"\n\n📊 State after Turn 1: Stage = '{session_t1.state.get('stage')}', Turn = {session_t1.state.get('turn_count')}")

    # TURN 2: CLARIFICATION
    print("\n--- TURN 2: CLARIFICATION ---")
    user_msg_2 = "The target audience is busy families who need fast 20-minute dinner recipes."
    print(f"👤 User: {user_msg_2}")
    content_2 = types.Content(role="user", parts=[types.Part.from_text(text=user_msg_2)])

    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content_2):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(part.text, end="", flush=True)

    session_t2 = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print(f"\n\n📊 State after Turn 2: Stage = '{session_t2.state.get('stage')}', Turn = {session_t2.state.get('turn_count')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_state_progression_demo())
