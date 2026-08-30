import os
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()

# Model for fast agent reasoning
MODEL_NAME = os.getenv("GEMINI_MODEL") or os.getenv("MODEL_NAME") or "gemini-2.5-flash"

root_agent = Agent(
    name="hello_agent",
    model=MODEL_NAME,
    instruction="You are a friendly collaborative partner assistant. Introduce yourself succinctly and confirm that you are ready to pair-program."
)
