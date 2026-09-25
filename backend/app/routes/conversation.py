"""
Conversation API route.

Endpoints
---------
POST /api/conversation   — Process one turn of the AI livelihood interview
"""
import logging

from fastapi import APIRouter, HTTPException

from app.models.conversation import ConversationRequest, ConversationResponse
from app.services.conversation import process_conversation_turn

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/conversation",
    response_model=ConversationResponse,
    tags=["Conversation"],
    summary="Process one turn of the AI livelihood interview",
    responses={
        400: {"description": "Invalid request (empty message, unsupported language)"},
        502: {"description": "LLM API failure or malformed response"},
        503: {"description": "Gemini API key not configured"},
    },
)
def conversation(request: ConversationRequest) -> ConversationResponse:
    """
    Accepts a user message and returns the assistant's next question along with
    the extracted/updated livelihood profile.

    **Session management**: the server maintains conversation history and the
    accumulated profile in memory, keyed by ``session_id``.  Send the same
    ``session_id`` to continue an existing conversation.

    **Language**: set ``language`` to ``"en"`` (English) or ``"hi"`` (Hindi).
    The assistant's question will be generated in the selected language.
    Profile field names are always stored in English internally.

    **Interview flow**: the engine asks one question per turn, silently
    extracting profile fields from the user's answers.  When enough
    information has been collected, ``interview_complete`` becomes ``true``
    and the top 3 matched NSQF pathways can be fetched via ``POST /api/match``.

    **Error codes**:
    - 400: empty message or unsupported language
    - 503: GEMINI_API_KEY not set in the environment
    - 502: Gemini API call failed or returned a malformed response
    """
    try:
        return process_conversation_turn(request)

    except ValueError as exc:
        logger.warning(
            "Conversation 400 | Session: %s | Lang: %s | Error: %s",
            request.session_id,
            request.language,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except EnvironmentError as exc:
        logger.error(
            "Conversation 503 | Session: %s | Missing Configuration: %s",
            request.session_id,
            exc,
        )
        raise HTTPException(
            status_code=503,
            detail="The conversation service is not available: Gemini API key is not configured.",
        ) from exc

    except RuntimeError as exc:
        logger.error(
            "Conversation 502 | Session: %s | Lang: %s | Upstream Error: %s",
            request.session_id,
            request.language,
            exc,
        )
        raise HTTPException(
            status_code=502,
            detail="The conversation service encountered an error. Please try again.",
        ) from exc

    except Exception as exc:
        logger.exception(
            "Conversation 500 | Session: %s | Lang: %s | Unexpected (%s): %s",
            request.session_id,
            request.language,
            type(exc).__name__,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        ) from exc
