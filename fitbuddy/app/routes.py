"""
routes.py
All route handlers for FitBuddy: home page, plan generation,
feedback-based updates, and the admin "view all users" dashboard.
"""

import os
from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.schemas import UserInput, FeedbackRequest, WorkoutRequest
from app.gemini_generator import generate_workout_gemini
from app.nutrition import get_nutrition_tip
from app.updated_plan import update_workout_plan
from app.database import (
    save_user,
    save_plan,
    update_plan,
    get_original_plan,
    get_user,
    get_all_users,
    get_all_plans,
)

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# 0. Home route: shows the input form
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


# 1. API: Generate workout using Gemini Pro (raw JSON endpoint)
@router.post("/generate-workout/gemini")
async def generate_gemini_workout(request: WorkoutRequest):
    try:
        result = generate_workout_gemini({
            "goal": request.goal,
            "intensity": request.intensity,
        })
        return {"model": "gemini-pro", "workout_plan": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 2. API: Generate nutrition tip using Gemini Flash (raw JSON endpoint)
@router.get("/nutrition-tip")
def get_flash_tip(goal: str):
    tip = get_nutrition_tip(goal)
    return {"goal": goal, "nutrition_tip": tip}


# 3. Web: Handle the form submission -> generate plan + tip, save, and render result.html
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

        save_user(
            user_id=user_data.user_id,
            name=user_data.username,
            age=user_data.age,
            weight=user_data.weight,
            goal=user_data.goal,
            intensity=user_data.intensity,
        )

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
            "workout_plan": plan,
            "nutrition_tip": nutrition_tip,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Something went wrong: {str(e)}")


# 4. Web: Submit feedback -> update plan via Gemini Pro, save, and re-render result.html
@router.post("/submit-feedback", response_class=HTMLResponse)
def submit_feedback_form(
    request: Request,
    user_id: int = Form(...),
    feedback: str = Form(...),
):
    original = get_original_plan(user_id)
    if not original:
        raise HTTPException(status_code=404, detail="Original plan not found for this user.")

    user = get_user(user_id)
    updated = update_workout_plan(original, feedback)
    update_plan(user_id, updated)

    nutrition_tip = get_nutrition_tip(user.goal if user else "general fitness")

    return templates.TemplateResponse(request, "result.html", {
        "username": user.name if user else "",
        "user_id": user_id,
        "age": user.age if user else "",
        "weight": user.weight if user else "",
        "goal": user.goal if user else "",
        "intensity": user.intensity if user else "",
        "workout_plan": updated,
        "nutrition_tip": nutrition_tip,
        "feedback_submitted": True,
    })


# 4b. API: JSON version of feedback update (matches doc's /update-plan/{user_id})
@router.post("/update-plan/{user_id}", response_model=dict)
def update_user_plan(user_id: int, data: FeedbackRequest):
    original = get_original_plan(user_id)
    if not original:
        return {"error": "Original plan not found for this user."}
    updated = update_workout_plan(original, data.feedback)
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
            "original_plan": plan.original_plan if plan else "N/A",
            "updated_plan": plan.updated_plan if plan and plan.updated_plan else "Not updated",
        })

    return templates.TemplateResponse(request, "all_users.html", {
        "users": user_data,
    })