"""
Route definitions for the SkillFlow recommendation and pathway system.

Exposes:
  POST /api/recommendations — Generates top 3 explainable NSQF recommendations
"""
import logging
from typing import Any
from fastapi import APIRouter, HTTPException

from app.models.profile import UserProfile
from app.models.recommendation import RecommendationsResponse
from app.services.recommendations import generate_recommendations

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Recommendations"])


@router.post(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Generate top 3 explainable NSQF recommendations for a completed profile",
)
def get_recommendations(payload: dict[str, Any]) -> RecommendationsResponse:
    """
    Accepts a completed user livelihood profile and generates at most 3
    grounded NSQF role recommendations with:
    - Match score and percentage
    - Grounded explainability rationale
    - Clear distinction of skills already had vs skills to develop
    - Accredited NSQF training and certification roadmap

    Accepts either `{"profile": {...}}` or a bare `UserProfile` object.
    """
    try:
        if "profile" in payload and isinstance(payload["profile"], dict):
            profile = UserProfile.model_validate(payload["profile"])
        else:
            profile = UserProfile.model_validate(payload)
    except Exception as exc:
        logger.warning("Invalid profile payload for recommendations: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid profile payload: {exc}",
        ) from exc

    return generate_recommendations(profile, max_recommendations=3)
