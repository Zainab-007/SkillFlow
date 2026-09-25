"""
Pydantic models representing a single NSQF vocational role/pathway.

These models mirror the schema defined in data/nsqf_roles.json exactly.
Do not add fields here that do not exist in the JSON — the JSON is the
single source of truth.
"""
from pydantic import BaseModel, HttpUrl


class RoleSource(BaseModel):
    """Source attribution for a knowledge-base record."""

    organization: str
    document: str
    url: str  # kept as plain str so non-canonical URLs don't fail validation


class LivelihoodRole(BaseModel):
    """
    A single NSQF-aligned vocational role / training pathway.

    Field names match the JSON keys in data/nsqf_roles.json.
    """

    id: str
    title: str
    qp_code: str
    nsqf_level: float          # float to accommodate levels like 2.5 and 4.5
    sector: str
    required_skills: list[str]
    gap_skills_covered: list[str]
    eligibility: str
    qualification: str
    duration: str
    description: str
    employment_type: list[str]
    source: RoleSource
    last_verified: str         # stored as ISO-date string (YYYY-MM-DD)


class KnowledgeBase(BaseModel):
    """Top-level wrapper around the nsqf_roles.json file."""

    version: str
    last_updated: str
    description: str
    roles: list[LivelihoodRole]
