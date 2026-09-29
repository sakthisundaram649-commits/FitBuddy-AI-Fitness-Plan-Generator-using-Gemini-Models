"""
gemini_generator.py
Uses Google's Gemini model to generate a structured 7-day workout plan
based on the user's fitness goal and preferred intensity.

Reliability features:
- call_gemini_with_retry(): waits and retries when the free-tier rate limit (429) is hit
- fallback_workout_plan(): a built-in 7-day plan used if the AI still fails,
  so the user never sees an error message as their plan
"""

import os
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_PRO_MODEL = os.getenv("GEMINI_PRO_MODEL", "gemini-flash-latest")

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(GEMINI_PRO_MODEL)

# Plans that start with this text are built-in templates (not AI-written).
# The app tries the AI again next time instead of reusing them.
TEMPLATE_MARKER = "[Template plan]"


def call_gemini_with_retry(gemini_model, prompt, max_attempts=3):
    """
    Call Gemini. If Google says we hit the rate limit (429), wait the time
    Google asks for and try again. Raises the last error if it still fails.
    """
    last_error = None
    for attempt in range(max_attempts):
        try:
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            last_error = e
            message = str(e)
            is_rate_limit = "429" in message or "quota" in message.lower()
            if not is_rate_limit or attempt == max_attempts - 1:
                break
            match = re.search(r"retry in ([\d.]+)s", message)
            wait_seconds = float(match.group(1)) + 2 if match else 30
            time.sleep(min(wait_seconds, 45))
    raise last_error


# ---------- Built-in fallback plans ----------

def _detect_focus(goal: str) -> str:
    g = (goal or "").lower()
    if any(w in g for w in ("muscle", "gain", "strength", "bulk")):
        return "muscle gain"
    if any(w in g for w in ("lose", "loss", "fat", "weight", "slim")):
        return "weight loss"
    return "general fitness"


_PLANS = {
    "muscle gain": [
        ("Upper Body Push (Chest, Shoulders, Triceps)", [
            "Push-ups: {s} sets of 8-12 reps",
            "Dumbbell shoulder press: {s} sets of 8-12 reps",
            "Incline dumbbell press: {s} sets of 8-12 reps",
            "Bench or chair dips: {s} sets of 8-12 reps"]),
        ("Lower Body (Quads, Hamstrings, Calves)", [
            "Bodyweight or goblet squats: {s} sets of 10-12 reps",
            "Romanian deadlifts (dumbbells): {s} sets of 10-12 reps",
            "Walking lunges: {s} sets of 10 reps per leg",
            "Standing calf raises: {s} sets of 15 reps"]),
        ("Active Recovery", [
            "Brisk walk or easy cycling: 30 minutes",
            "Full-body stretching: 10 minutes"]),
        ("Upper Body Pull (Back, Biceps)", [
            "Dumbbell rows: {s} sets of 10-12 reps",
            "Band or machine lat pulldown: {s} sets of 10-12 reps",
            "Dumbbell bicep curls: {s} sets of 10-12 reps",
            "Face pulls (band): {s} sets of 15 reps"]),
        ("Lower Body and Core", [
            "Goblet squats: {s} sets of 10-12 reps",
            "Glute bridges: {s} sets of 12-15 reps",
            "Plank: {s} sets of 30-45 seconds",
            "Lying leg raises: {s} sets of 10-12 reps"]),
        ("Full Body", [
            "Push-ups: {s} sets of 8-12 reps",
            "Squats: {s} sets of 10-12 reps",
            "Dumbbell rows: {s} sets of 10-12 reps",
            "Side plank: {s} sets of 20-30 seconds per side"]),
        ("Rest Day", ["Rest, light walking and 7-9 hours of sleep"]),
    ],
    "weight loss": [
        ("Full Body Strength Circuit", [
            "Squats: {s} sets of 12-15 reps",
            "Push-ups: {s} sets of 8-12 reps",
            "Dumbbell rows: {s} sets of 12 reps",
            "Plank: {s} sets of 30-45 seconds"]),
        ("Cardio Intervals", [
            "Brisk walk or jog: 1 minute fast, 2 minutes easy, repeat for 25-30 minutes",
            "Jumping jacks: {s} sets of 30 seconds"]),
        ("Lower Body and Core", [
            "Lunges: {s} sets of 10 reps per leg",
            "Glute bridges: {s} sets of 15 reps",
            "Mountain climbers: {s} sets of 30 seconds",
            "Bicycle crunches: {s} sets of 15 reps per side"]),
        ("Active Recovery", [
            "Easy walk: 30-40 minutes",
            "Full-body stretching: 10 minutes"]),
        ("Upper Body and Cardio Finisher", [
            "Push-ups: {s} sets of 8-12 reps",
            "Dumbbell shoulder press: {s} sets of 12 reps",
            "Bench or chair dips: {s} sets of 10 reps",
            "High knees: {s} sets of 30 seconds"]),
        ("Steady Cardio", [
            "Jog, cycle or brisk walk: 35-40 minutes at a comfortable pace",
            "Core: plank {s} sets of 30-45 seconds"]),
        ("Rest Day", ["Rest, light walking and 7-9 hours of sleep"]),
    ],
    "general fitness": [
        ("Full Body Strength", [
            "Squats: {s} sets of 10-12 reps",
            "Push-ups: {s} sets of 8-12 reps",
            "Dumbbell rows: {s} sets of 10-12 reps",
            "Plank: {s} sets of 30-45 seconds"]),
        ("Cardio", [
            "Brisk walk, jog or cycle: 30 minutes",
            "Jumping jacks: {s} sets of 30 seconds"]),
        ("Mobility and Flexibility", [
            "Yoga flow or full-body stretching: 25-30 minutes",
            "Cat-cow and child's pose: 2 minutes each"]),
        ("Lower Body and Core", [
            "Lunges: {s} sets of 10 reps per leg",
            "Glute bridges: {s} sets of 12-15 reps",
            "Bird-dog: {s} sets of 8-10 reps per side",
            "Dead bug: {s} sets of 8 reps per side"]),
        ("Upper Body", [
            "Incline or regular push-ups: {s} sets of 8-12 reps",
            "Dumbbell shoulder press: {s} sets of 10-12 reps",
            "Dumbbell bicep curls: {s} sets of 12 reps",
            "Triceps dips: {s} sets of 10 reps"]),
        ("Cardio and Core", [
            "Easy jog or cycling: 25-30 minutes",
            "Bicycle crunches: {s} sets of 15 reps per side"]),
        ("Rest Day", ["Rest, light walking and 7-9 hours of sleep"]),
    ],
}


def fallback_workout_plan(goal: str, intensity: str) -> str:
    """Built-in 7-day plan used when the AI service is unavailable."""
    focus = _detect_focus(goal)
    level = (intensity or "medium").strip().lower()
    sets = {"low": 2, "medium": 3, "high": 4}.get(level, 3)
    rest = {"low": "60-90 seconds", "medium": "45-60 seconds", "high": "30-45 seconds"}.get(level, "45-60 seconds")

    lines = [
        f"{TEMPLATE_MARKER} The AI service was busy, so this is a standard 7-day plan for your goal. "
        "Generate again in a minute to get an AI-written plan.",
        "",
        f"## 7-Day {focus.title()} Workout Plan ({level.capitalize()} Intensity)",
        "",
    ]
    for number, (title, exercises) in enumerate(_PLANS[focus], start=1):
        lines.append(f"**Day {number}: {title}**")
        lines.append("")
        if title == "Rest Day":
            lines.append(f"* {exercises[0]}")
        else:
            lines.append("* **Warm-up (5-10 mins):** Light cardio and dynamic stretches.")
            lines.append("* **Main Workout:**")
            for exercise in exercises:
                lines.append("    * " + exercise.replace("{s}", str(sets)))
            lines.append(f"    * Rest {rest} between sets.")
            lines.append("* **Cooldown:** 5 minutes of gentle static stretching.")
        lines.append("")
    lines.append("**Important Notes:** Listen to your body, keep good form, drink plenty of water, "
                 "and consult a doctor before starting a new routine.")
    return "\n".join(lines)


def generate_workout_gemini(user_input: dict) -> str:
    """
    Generate a personalized 7-day workout plan.
    Never returns an error message: if the AI fails, a built-in plan is returned.

    Args:
        user_input (dict): expects keys "goal" and "intensity"
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
        text = call_gemini_with_retry(model, prompt)
        if text and text.strip():
            return text
    except Exception:
        pass
    return fallback_workout_plan(user_input["goal"], user_input["intensity"])
