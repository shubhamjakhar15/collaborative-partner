import sys
from app.tools.project_memory import update_project
from app.schemas.contract import Plan, PlanStep, StepStatus

plan = Plan(
    title="Test Plan",
    summary="Summary",
    steps=[
        PlanStep(id="step_1", description="Do something", status=StepStatus.PENDING, assignee="agent")
    ]
)

res = update_project(
    user_id="demo-user",
    project_id="recipe-organizer-01",
    current_plan=plan
)

print(res)
