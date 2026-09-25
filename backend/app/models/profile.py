"""
Pydantic models for the user livelihood profile.

The profile is built incrementally through the AI conversation — most fields
are therefore Optional.  The matching service handles missing fields gracefully
so an incomplete profile still produces useful results.
"""
from typing import Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """
    Structured livelihood profile extracted from the AI conversation.

    All fields except `skills` are optional because the interview is adaptive —
    the user may not yet have provided every piece of information.
    """

    education: Optional[str] = Field(
        default=None,
        description="Highest educational qualification (e.g. '8th', '10th', '12th', 'Graduate')",
    )
    current_occupation: Optional[str] = Field(
        default=None,
        description="Current or most recent occupation (e.g. 'Tailoring', 'Farming', 'Student')",
    )
    current_activity: Optional[str] = Field(
        default=None,
        description="Current ongoing work or practical activity (e.g. 'Software / Project Development')",
    )
    experience_years: Optional[float] = Field(
        default=None,
        ge=0,
        description="Years of relevant work experience",
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Skills the user already has (normalised terms preferred)",
    )
    interests: list[str] = Field(
        default_factory=list,
        description="Interests or domains the user wants to work in",
    )
    preferred_specialization: Optional[str] = Field(
        default=None,
        description="Preferred specialized domain or career focus (e.g. 'Backend Development')",
    )
    mobility_constraint: Optional[str] = Field(
        default=None,
        description="Any mobility or physical constraints (e.g. 'Home-based preferred', 'None')",
    )
    employment_preference: Optional[str] = Field(
        default=None,
        description="Employment preference: 'Self-employment', 'Wage-employment', or 'Either'",
    )
    location: Optional[str] = Field(
        default=None,
        description="City, district, or state where the user is based",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "education": "12th",
                "current_occupation": "Tailoring",
                "experience_years": 3,
                "skills": ["Sewing", "Tailoring", "Alteration"],
                "interests": ["Fashion"],
                "mobility_constraint": "Home-based preferred",
                "employment_preference": "Self-employment",
                "location": "Mumbai",
            }
        }
    }
