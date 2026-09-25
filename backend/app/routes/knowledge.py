"""
API routes for SkillFlow.

Endpoints
---------
GET  /api/health                  — Health check
GET  /api/knowledge/roles         — List all roles
GET  /api/knowledge/roles/{id}    — Get role by ID
GET  /api/knowledge/sectors       — Sector summary
POST /api/match                   — Match a user profile
"""
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.profile import UserProfile
from app.models.role import LivelihoodRole
from app.services import knowledge_base as kb_service
from app.services.matching import match_profile, MatchResult

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    service: str


class SectorEntry(BaseModel):
    name: str
    count: int


class SectorsResponse(BaseModel):
    sectors: list[SectorEntry]


class MatchResultResponse(BaseModel):
    """API-serialisable version of a MatchResult."""

    role_id: str
    title: str
    sector: str
    nsqf_level: float
    score: float
    matched_skills: list[str]
    skill_gaps: list[str]
    employment_type: list[str]


class MatchResponse(BaseModel):
    profile_received: dict[str, Any]
    total_roles_evaluated: int
    results: list[MatchResultResponse]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
)
def health() -> HealthResponse:
    """Returns a simple status response to confirm the service is running."""
    return HealthResponse(status="ok", service="SkillFlow backend")


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------
@router.get(
    "/knowledge/roles",
    response_model=list[LivelihoodRole],
    tags=["Knowledge Base"],
    summary="List all NSQF roles",
)
def list_roles() -> list[LivelihoodRole]:
    """
    Returns the complete list of NSQF-aligned vocational roles from the
    curated knowledge base.
    """
    return kb_service.get_all_roles()


@router.get(
    "/knowledge/roles/{role_id}",
    response_model=LivelihoodRole,
    tags=["Knowledge Base"],
    summary="Get a single role by ID",
    responses={404: {"description": "Role not found"}},
)
def get_role(role_id: str) -> LivelihoodRole:
    """
    Returns a single NSQF role by its ID (e.g. ``T-001``).

    The lookup is case-insensitive.

    Raises HTTP 404 if the ID is not found.
    """
    role = kb_service.get_role_by_id(role_id)
    if role is None:
        raise HTTPException(
            status_code=404,
            detail=f"Role '{role_id}' not found in the knowledge base.",
        )
    return role


@router.get(
    "/knowledge/sectors",
    response_model=SectorsResponse,
    tags=["Knowledge Base"],
    summary="List sectors and role counts",
)
def list_sectors() -> SectorsResponse:
    """
    Returns a list of sectors available in the knowledge base with the
    number of roles in each sector, sorted alphabetically.
    """
    entries = kb_service.get_sectors_summary()
    return SectorsResponse(
        sectors=[SectorEntry(name=e["name"], count=e["count"]) for e in entries]
    )


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
@router.post(
    "/match",
    response_model=MatchResponse,
    tags=["Matching"],
    summary="Match a user profile to NSQF pathways",
)
def match(profile: UserProfile) -> MatchResponse:
    """
    Accepts a structured user profile and returns all knowledge-base roles
    scored and ranked by relevance.

    The matching algorithm is deterministic keyword-based scoring:
    - 60% weight on skill overlap
    - 20% weight on interest alignment
    - 20% weight on occupation relevance
    - +5% bonus if the role's employment_type matches the user's preference

    Results are sorted by ``score`` descending.  The caller (e.g. the LLM
    conversation engine) should take the top 3 for presentation.

    An empty or minimal profile is accepted — the algorithm degrades
    gracefully and still returns scored results.
    """
    all_roles = kb_service.get_all_roles()
    results: list[MatchResult] = match_profile(profile, roles=all_roles)

    response_results = [
        MatchResultResponse(
            role_id=r.role_id,
            title=r.title,
            sector=r.sector,
            nsqf_level=r.nsqf_level,
            score=r.score,
            matched_skills=r.matched_skills,
            skill_gaps=r.skill_gaps,
            employment_type=r.employment_type,
        )
        for r in results
    ]

    return MatchResponse(
        profile_received=profile.model_dump(exclude_none=True),
        total_roles_evaluated=len(all_roles),
        results=response_results,
    )
