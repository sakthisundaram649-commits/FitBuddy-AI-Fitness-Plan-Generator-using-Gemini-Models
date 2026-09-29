"""
routes.py
All route handlers for FitBuddy: home page, plan generation,
feedback-based updates, and the admin "view all users" dashboard.

Reliability: a saved plan is reused when the same user submits the same goal and
intensity, and an error message is never saved as a workout plan.
"""

import os
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.schemas import UserInput, FeedbackRequest, WorkoutRequest
from app.gemini_generator import generate_workout_gemini, TEMPLATE_MARKER
from app.nutrition import get_nutrition_tip
from app.updated_plan import update_workout_plan
from app.formatting import markdown_to_html
from app.database import (
    save_user,
    save_plan,
    update_plan,
    get_original_plan,
    get_plan_record,
    get_user,
    get_all_users,
    get_all_plans,
)

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


def is_good_plan(text) -> bool:
    """A saved plan is reusable only if it is real AI text (not an error or a template)."""
    return bool(text) and not text.startswith("Error") and not text.startswith(TEMPLATE_MARKER)


# 0. Home route: shows the input form
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


# 1. API: Generate workout using Gemini (raw JSON endpoint)
@router.post("/generate-workout/gemini")
async def generate_gemini_workout(request: WorkoutRequest):
    try:
        result = generate_workout_gemini({
            "goal": request.goal,
            "intensity": request.intensity,
        })
        return {"model": "gemini", "workout_plan": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2. API: Generate nutrition tip using Gemini Flash (raw JSON endpoint)
@router.get("/nutrition-tip")
def get_flash_tip(goal: str):
    tip = get_nutrition_tip(goal)
    return {"goal": goal, "nutrition_tip": tip}


# 3. Web: Handle the form submission -> generate (or reuse) plan, save, render result.html
@router.post("/generate-workout", response_class=HTMLResponse)
def generate_workout_form(
    request: Request,
    username: str = Form(...),
    user_id: int = Form(...),
    age: int = Form(...),
    weight: float = Form(...),
    goal: str = Form(...),
    intensity: str = Form(...),
):
    try:
        user_data = UserInput(
            username=username,
            user_id=user_id,
            age=age,
            weight=weight,
            goal=goal,
            intensity=intensity,
        )

        # Look for an already-saved good plan BEFORE updating the user row
        existing_user = get_user(user_id)
        record = get_plan_record(user_id)
        can_reuse = bool(
            existing_user
            and record
            and is_good_plan(record["original_plan"])
            and existing_user.goal.strip().lower() == goal.strip().lower()
            and existing_user.intensity.strip().lower() == intensity.strip().lower()
        )

        save_user(
            user_id=user_data.user_id,
            name=user_data.username,
            age=user_data.age,
            weight=user_data.weight,
            goal=user_data.goal,
            intensity=user_data.intensity,
        )

        if can_reuse:
            # Same user, same goal and intensity: show the saved plan, no AI call needed
            plan = record["updated_plan"] or record["original_plan"]
            nutrition_tip = record["nutrition_tip"] or get_nutrition_tip(goal)
        else:
            plan = generate_workout_gemini({"goal": goal, "intensity": intensity})
            nutrition_tip = get_nutrition_tip(goal)
            save_plan(user_data.user_id, plan, nutrition_tip)

        return templates.TemplateResponse(request, "result.html", {
            "username": username,
            "user_id": user_id,
            "age": age,
            "weight": weight,
            "goal": goal,
            "intensity": intensity,
            "workout_plan_html": markdown_to_html(plan),
            "nutrition_tip_html": markdown_to_html(nutrition_tip),
            "reused": can_reuse,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Something went wrong: {str(e)}")


# 4. Web: Submit feedback -> update plan, save, and re-render result.html
@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback_form(
    request: Request,
    user_id: int = Form(...),
    feedback: str = Form(...),
):
    record = get_plan_record(user_id)
    if not record or not record["original_plan"] or record["original_plan"].startswith("Error"):
        raise HTTPException(
            status_code=404,
            detail="No saved plan found for this User ID. Please generate a plan first.",
        )

    user = get_user(user_id)
    current_plan = record["updated_plan"] or record["original_plan"]
    nutrition_tip = record["nutrition_tip"] or get_nutrition_tip(user.goal if user else "general fitness")

    context = {
        "username": user.name if user else "",
        "user_id": user_id,
        "age": user.age if user else "",
        "weight": user.weight if user else "",
        "goal": user.goal if user else "",
        "intensity": user.intensity if user else "",
        "nutrition_tip_html": markdown_to_html(nutrition_tip),
    }

    try:
        updated = update_workout_plan(current_plan, feedback)
    except Exception:
        # AI unavailable: keep the current plan and tell the user, never save an error
        context["workout_plan_html"] = markdown_to_html(current_plan)
        context["error_message"] = (
            "The AI is busy right now (free usage limit). Your saved plan is unchanged. "
            "Please wait one minute and submit your feedback again."
        )
        return templates.TemplateResponse(request, "result.html", context)

    update_plan(user_id, updated)
    context["workout_plan_html"] = markdown_to_html(updated)
    context["feedback_submitted"] = True
    return templates.TemplateResponse(request, "result.html", context)


# 4b. API: JSON version of feedback update (matches doc's /update-plan/{user_id})
@router.post("/update-plan/{user_id}", response_model=dict)
def update_user_plan(user_id: int, data: FeedbackRequest):
    original = get_original_plan(user_id)
    if not original:
        return {"error": "Original plan not found for this user."}
    try:
        updated = update_workout_plan(original, data.feedback)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI unavailable, plan unchanged: {str(e)}")
    update_plan(user_id, updated)
    return {"updated_plan": updated}


# 5. Web: Admin dashboard - view all users & their plans
@router.get("/view-all-users", response_class=HTMLResponse)
def view_all_users(request: Request):
    users = get_all_users()
    plans = {p.user_id: p for p in get_all_plans()}

    user_data = []
    for user in users:
        plan = plans.get(user.id)
        user_data.append({
            "id": user.id,
            "name": user.name,
            "age": user.age,
            "weight": user.weight,
            "goal": user.goal,
            "intensity": user.intensity,
            "original_plan_html": markdown_to_html(plan.original_plan) if plan else "N/A",
            "updated_plan_html": markdown_to_html(plan.updated_plan) if plan and plan.updated_plan else "Not updated",
        })

    return templates.TemplateResponse(request, "all_users.html", {
        "users": user_data,
    })
