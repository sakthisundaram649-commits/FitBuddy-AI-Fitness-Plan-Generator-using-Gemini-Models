"""
updated_plan.py
Revises an existing workout plan based on user feedback, using Gemini.
Raises an exception if the AI cannot be reached, so the app can keep the
existing plan instead of saving an error message.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

from app.gemini_generator import call_gemini_with_retry

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-flash-latest")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(GEMINI_PRO_MODEL)


def update_workout_plan(original_plan: str, user_feedback: str) -> str:
    """
    Use Gemini to update the workout plan based on user feedback.
    Raises an exception on failure (the caller keeps the current plan).
    """
    prompt = f"""
    You are a professional fitness trainer assistant.

    Here's the original 7-day workout plan:
    {original_plan}

    User Feedback:
    "{user_feedback}"

    Based on the feedback, revise the relevant parts of the workout plan. Keep the format and rest of the plan unchanged if not needed.
    """
    text = call_gemini_with_retry(model, prompt)
    if not text or not text.strip():
        raise ValueError("Empty response from AI")
    return text.strip()
