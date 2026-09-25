"""
Pydantic models for the conversation engine API.

These models define the request and response shapes for POST /api/conversation.
All fields use plain Python types so they serialise cleanly to JSON for the
future React frontend.
"""
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Supported languages
# ---------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {"en", "hi"}


# ---------------------------------------------------------------------------
# A single turn in the conversation history
# ---------------------------------------------------------------------------
class ConversationTurn(BaseModel):
    """One exchange: a user message and the assistant's reply."""

    role: str = Field(description="'user' or 'assistant'")
    content: str = Field(description="The message text")


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------
class ConversationRequest(BaseModel):
    """
    Request body for POST /api/conversation.

    The client sends:
      - session_id : persistent identifier for this user session
      - language   : 'en' or 'hi'
      - message    : the user's latest input
      - conversation_history : all previous turns (optional on first turn)
    """

    session_id: str = Field(
        description="Unique identifier for this conversation session",
    )
    language: str = Field(
        default="en",
        description="Conversation language: 'en' (English) or 'hi' (Hindi)",
    )
    message: str = Field(
        description="The user's latest message",
    )
    conversation_history: list[ConversationTurn] = Field(
        default_factory=list,
        description="All previous turns in this session",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "demo-session-001",
                "language": "en",
                "message": "I have been doing tailoring from home for three years.",
                "conversation_history": [],
            }
        }
    }


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Profile update extracted by LLM
# ---------------------------------------------------------------------------
class ProfileUpdate(BaseModel):
    """
    Partial profile fields extracted from the user's message.
    Explicit typed fields avoid additionalProperties: true in Gemini response_schema.
    """
    education: Optional[str] = None
    current_occupation: Optional[str] = None
    current_activity: Optional[str] = None
    experience_years: Optional[float] = None
    skills: Optional[list[str]] = None
    interests: Optional[list[str]] = None
    preferred_specialization: Optional[str] = None
    mobility_constraint: Optional[str] = None
    employment_preference: Optional[str] = None
    location: Optional[str] = None


# ---------------------------------------------------------------------------
# LLM structured output — what Gemini must return
# ---------------------------------------------------------------------------
class LLMTurnOutput(BaseModel):
    """
    The structured output schema we request from Gemini.

    Gemini is instructed to return JSON matching this schema exactly.
    Validated with Pydantic before any further processing.
    """

    assistant_question: str
    profile_update: ProfileUpdate = Field(default_factory=ProfileUpdate)
    interview_complete: bool = False


# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------
class ConversationResponse(BaseModel):
    """
    Response body for POST /api/conversation.

    Returns the assistant's next question, the updated profile,
    and metadata about interview progress.
    """

    session_id: str
    assistant_question: str = Field(
        description="The assistant's next question or closing statement",
    )
    profile_update: dict[str, Any] = Field(
        default_factory=dict,
        description="Fields extracted or updated from this turn",
    )
    profile: dict[str, Any] = Field(
        description="The full accumulated profile for this session so far",
    )
    fields_completed: list[str] = Field(
        description="Profile fields that now have a value",
    )
    fields_remaining: list[str] = Field(
        description="Profile fields still missing",
    )
    interview_complete: bool = Field(
        default=False,
        description="True when the profile is sufficiently complete",
    )
