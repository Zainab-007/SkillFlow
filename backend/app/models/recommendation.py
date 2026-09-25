"""
Pydantic models for the SkillFlow recommendation and pathway system.

Defines the request and response shapes for POST /api/recommendations.
"""
from pydantic import BaseModel, Field
from app.models.profile import UserProfile


class TrainingPathway(BaseModel):
    """
    Accredited NSQF vocational training and certification pathway details.
    Directly grounded in the verified Qualification Pack (QP) data.
    """

    qp_code: str = Field(description="Qualification Pack Code (e.g. AMH/Q0301)")
    nsqf_level: float = Field(description="NSQF Level of the qualification (e.g. 2.5, 4.0)")
    qualification: str = Field(description="Official NSQF qualification title")
    duration: str = Field(description="Course duration or training format")
    eligibility: str = Field(description="Entry requirements and minimum educational qualification")
    organization: str = Field(description="Awarding Sector Skill Council / Body")
    document: str = Field(description="Curriculum / QP reference document")
    url: str = Field(description="Official source URL")


class RoleRecommendation(BaseModel):
    """
    A single tailored NSQF livelihood role recommendation with explainability,
    skill-gap analysis, and training pathway.
    """

    role_id: str = Field(description="Unique role identifier (e.g. T-001)")
    role_title: str = Field(description="Official job role title")
    sector: str = Field(description="Vocational industry sector")
    nsqf_level: float = Field(description="NSQF Level")
    match_score: float = Field(description="Deterministic match score [0.0, 1.0]")
    match_percentage: int = Field(description="Deterministic match score as an integer percentage 0-100")
    matched_skills: list[str] = Field(default_factory=list, description="Skills the user already has that match this role")
    matched_interests: list[str] = Field(default_factory=list, description="User interests that align with this role or sector")
    skills_already_have: list[str] = Field(default_factory=list, description="Specific relevant skills the user possesses")
    skills_to_develop: list[str] = Field(default_factory=list, description="Actionable skill gaps to develop via NSQF training")
    skill_gaps: list[str] = Field(default_factory=list, description="Alias for skills_to_develop")
    experience_alignment: str = Field(description="How the user's experience maps to this role")
    preference_alignment: str = Field(description="How the role supports user's employment preference")
    explanation: str = Field(description="Factual, grounded rationale based on verified user facts and role data")
    pathway: TrainingPathway = Field(description="Accredited training and certification roadmap")


class RecommendationsRequest(BaseModel):
    """
    Request body for POST /api/recommendations.
    Accepts the completed user profile.
    """

    profile: UserProfile


class RecommendationsResponse(BaseModel):
    """
    Response body for POST /api/recommendations.
    Returns top recommendations with explainable pathways.
    """

    total_evaluated: int = Field(description="Total knowledge base roles evaluated")
    total_recommended: int = Field(description="Number of recommendations returned (at most 3)")
    recommendations: list[RoleRecommendation] = Field(
        default_factory=list,
        description="Top livelihood recommendations ordered by relevance",
    )
