"""
gemini_generator.py
Uses Google's Gemini Pro model to generate a structured 7-day workout plan
based on the user's fitness goal and preferred intensity.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-1.5-pro")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(GEMINI_PRO_MODEL)


def generate_workout_gemini(user_input: dict) -> str:
    """
    Generate a personalized 7-day workout plan.

    Args:
        user_input (dict): expects keys "goal" and "intensity"

    Returns:
        str: the generated workout plan text
    """
    prompt = f"""
    You are a professional fitness trainer.

    Create a personalized, structured 7-day workout plan for someone with the goal of
    **{user_input['goal']}**, and prefers **{user_input['intensity']} intensity** workouts.

    Each day must include:
    - A warm-up (5-10 mins)
    - Main workout (targeted exercises, sets & reps)
    - Cooldown or recovery tip

    Format:
    Day 1:
    Warm-up: ...
    Main Workout: ...
    Cooldown: ...
    (Repeat for Day 2-7)
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"
