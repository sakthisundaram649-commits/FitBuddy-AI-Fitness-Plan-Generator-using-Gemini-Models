"""
nutrition.py
Handles nutrition-specific logic (as shown in the PDF's project structure).

This wraps the Gemini Flash nutrition-tip generator (gemini_flash_generator.py)
and adds a simple safety fallback: if the Gemini API call fails for any reason
(bad key, network issue, rate limit), the user still gets a useful static tip
instead of seeing an error message on the result page.
"""

from app.gemini_flash_generator import generate_nutrition_tip_with_flash

# Static fallback tips, used only if the Gemini API call fails
FALLBACK_TIPS = {
    "weight loss": "Stay in a moderate calorie deficit and prioritize protein and vegetables at every meal.",
    "muscle gain": "Eat in a slight calorie surplus with 1.6-2.2g of protein per kg of body weight daily.",
    "general fitness": "Stay hydrated, eat balanced meals, and get 7-9 hours of sleep for recovery.",
}


def get_nutrition_tip(goal: str) -> str:
    """
    Returns a nutrition/recovery tip for the given fitness goal.

    Tries Gemini Flash first (generate_nutrition_tip_with_flash). If that call
    errors out, falls back to a static tip so the app never breaks.

    Args:
        goal (str): the user's fitness goal, e.g. "weight loss", "muscle gain"

    Returns:
        str: a nutrition or recovery tip
    """
    tip = generate_nutrition_tip_with_flash(goal)

    if tip.startswith("Error"):
        goal_key = goal.strip().lower()
        return FALLBACK_TIPS.get(goal_key, FALLBACK_TIPS["general fitness"])

    return tip
