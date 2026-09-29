"""
gemini_flash_generator.py
Uses Google's Gemini Flash model (lighter/faster) to generate a quick
nutrition or recovery tip tailored to the user's fitness goal.
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

from app.gemini_generator import call_gemini_with_retry

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_FLASH_MODEL = os.getenv("GEMINI_FLASH_MODEL", "gemini-flash-latest")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

flash_model = genai.GenerativeModel(GEMINI_FLASH_MODEL)


def generate_nutrition_tip_with_flash(goal: str) -> str:
    """
    Generate a nutrition or recovery tip using Gemini Flash based on the user's fitness goal.
    On failure it returns text starting with "Error", which nutrition.py replaces
    with a built-in tip.
    """
    prompt = (
        f"Give one clear, helpful nutrition or recovery tip for someone focused on '{goal}'. "
        "The tip should be practical, friendly, and easy to understand."
    )

    try:
        # One attempt only: if the limit is hit, nutrition.py uses its built-in tip
        return call_gemini_with_retry(flash_model, prompt, max_attempts=1).strip()
    except Exception as e:
        return f"Error generating tip: {str(e)}"
