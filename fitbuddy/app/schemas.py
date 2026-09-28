"""
schemas.py
Pydantic models used to validate incoming request data.
"""

from pydantic import BaseModel


class UserInput(BaseModel):
    username: str
    user_id: int
    age: int
    weight: float
    goal: str
    intensity: str


class WorkoutRequest(BaseModel):
    goal: str
    intensity: str


class FeedbackRequest(BaseModel):
    feedback: str
