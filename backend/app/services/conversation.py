"""
Conversation service — LLM-powered interview engine.

Responsibilities
----------------
1. Manage in-memory session state (history + accumulated profile).
2. Build the Gemini prompt with the current conversation context.
3. Call Gemini using the current SDK (google-genai ≥ 1.0.0) with
   structured JSON output (response_schema = LLMTurnOutput).
4. Validate the structured response with Pydantic.
5. Merge the extracted profile_update into the session profile.
6. Return a clean ConversationResponse for the FastAPI route.

Gemini SDK note
---------------
The current recommended SDK is `google-genai` (pip install google-genai),
NOT the deprecated `google-generativeai`.

API key
-------
Read from the GEMINI_API_KEY environment variable.
python-dotenv is used so a backend/.env file is automatically loaded
when running locally.  Never hardcode the key.

Session state
-------------
In-memory dict: session_id -> {"history": [...], "profile": {...}}.
Suitable for prototype/demo.  Replace with Redis/DB for production.

Error handling
--------------
- Missing API key → raises EnvironmentError (caught by route → 503)
- Gemini API failure → raises RuntimeError (caught by route → 502)
- Malformed LLM JSON → raises ValueError (caught by route → 502)
- Invalid language → raises ValueError (caught by route → 400)
"""
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

from app.models.conversation import (
    ConversationRequest,
    ConversationResponse,
    ConversationTurn,
    LLMTurnOutput,
    SUPPORTED_LANGUAGES,
)
from app.models.profile import UserProfile

# Load .env from the backend/ directory if it exists (local dev only)
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Profile field metadata — used to track completeness
# ---------------------------------------------------------------------------
_ALL_PROFILE_FIELDS = [
    "education",
    "current_occupation",
    "experience_years",
    "skills",
    "interests",
    "mobility_constraint",
    "employment_preference",
    "location",
]

# ---------------------------------------------------------------------------
# In-memory session store
# session_id -> {"history": list[dict], "profile": dict}
# ---------------------------------------------------------------------------
_sessions: dict[str, dict] = {}


def _get_or_create_session(session_id: str) -> dict:
    """Return the session dict, creating it if this is a new session."""
    if session_id not in _sessions:
        _sessions[session_id] = {"history": [], "profile": {}}
    return _sessions[session_id]


def _merge_profile(existing: dict, update: dict) -> dict:
    """
    Merge a profile update into the existing session profile.

    Rules:
    - String fields: overwrite only if the new value is non-empty.
    - List fields (skills, interests): extend, deduplicating case-insensitively.
    - Numeric fields (experience_years): overwrite if positive.
    - Unknown keys from the LLM are silently dropped.
    """
    valid_string_fields = {
        "education",
        "current_occupation",
        "mobility_constraint",
        "employment_preference",
        "location",
    }
    valid_list_fields = {"skills", "interests"}
    valid_numeric_fields = {"experience_years"}

    merged = dict(existing)

    for key, value in update.items():
        if key in valid_string_fields:
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()

        elif key in valid_list_fields:
            if isinstance(value, list):
                current = merged.get(key, [])
                # Deduplicate case-insensitively, preserving order
                existing_lower = {v.lower() for v in current}
                for item in value:
                    if isinstance(item, str) and item.strip():
                        if item.strip().lower() not in existing_lower:
                            current.append(item.strip())
                            existing_lower.add(item.strip().lower())
                merged[key] = current

        elif key in valid_numeric_fields:
            if isinstance(value, (int, float)) and value >= 0:
                merged[key] = value

        # Silently drop unknown keys from LLM

    return merged


def _profile_completeness(profile: dict) -> tuple[list[str], list[str]]:
    """
    Return (fields_completed, fields_remaining) based on the current profile.

    A list field counts as complete when it has at least one entry.
    A scalar field counts as complete when it has a non-None, non-empty value.
    """
    completed = []
    remaining = []

    for field in _ALL_PROFILE_FIELDS:
        value = profile.get(field)
        if value is None:
            remaining.append(field)
        elif isinstance(value, list) and len(value) == 0:
            remaining.append(field)
        elif isinstance(value, str) and not value.strip():
            remaining.append(field)
        else:
            completed.append(field)

    return completed, remaining


def _build_system_prompt(language: str) -> str:
    """
    Build the system prompt that instructs Gemini how to behave.

    The prompt is the same regardless of language — the language instruction
    is embedded inside it.  Internal reasoning remains in English.
    """
    lang_name = "English" if language == "en" else "Hindi"

    return f"""You are a warm, patient livelihood counsellor helping individuals in India \
explore skill-development and training opportunities.

Your goal is to build a structured livelihood profile through natural conversation.
You collect information across these fields:
- education (e.g. "5th pass", "8th pass", "10th pass", "12th pass", "Graduate")
- current_occupation (e.g. "Tailoring", "Farming", "None")
- experience_years (numeric, years of relevant work experience)
- skills (list of skills the person already has)
- interests (list of domains or activities they enjoy or want to work in)
- mobility_constraint (e.g. "Home-based preferred", "Can travel locally", "None")
- employment_preference ("Self-employment", "Wage-employment", or "Either")
- location (city, district, or state)

RULES:
1. Ask ONLY ONE short, voice-friendly question per turn.
2. NEVER ask for information already mentioned by the user.
3. Extract information silently — do NOT narrate what you extracted.
4. Do NOT fabricate information. Only record what the user clearly states.
5. If the user's answer is ambiguous, ask a natural clarification.
6. Aim for 5–8 total turns. Stop when the profile is sufficiently complete.
7. Set interview_complete=true when you have enough information for useful recommendations.
   You do NOT need every single field — use good judgment.
8. Ask questions in {lang_name}. Keep internal profile field names in English.
9. Your tone should be conversational and encouraging, NOT like a form.
10. Questions should build naturally on what the user just said.

OUTPUT FORMAT:
You must respond ONLY with valid JSON matching this exact schema:
{{
  "assistant_question": "<your next question or closing statement in {lang_name}>",
  "profile_update": {{<partial profile dict with only newly known fields>}},
  "interview_complete": <true or false>
}}

Do not add any text outside the JSON.
Do not add markdown code fences.
"""


def _build_contents(
    history: list[dict],
    current_message: str,
) -> list[dict]:
    """
    Build the Gemini `contents` list from the session history + new message.

    Format expected by google-genai SDK:
        [{"role": "user"|"model", "parts": [{"text": "..."}]}, ...]
    """
    contents = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": turn["content"]}]})
    contents.append({"role": "user", "parts": [{"text": current_message}]})
    return contents


def _get_gemini_client():
    """
    Create and return a configured Gemini client.

    Raises
    ------
    EnvironmentError
        If GEMINI_API_KEY is not set.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Create backend/.env with GEMINI_API_KEY=your_key_here."
        )
    # Import here so the module can be imported without the SDK installed
    # (useful for tests that mock this function).
    from google import genai  # type: ignore[import]
    return genai.Client(api_key=api_key)


def _call_gemini(
    client: Any,
    system_prompt: str,
    contents: list[dict],
) -> LLMTurnOutput:
    """
    Call the Gemini API and return a validated LLMTurnOutput.

    Uses response_schema with LLMTurnOutput to request structured JSON output.
    Validates the response with Pydantic.

    Raises
    ------
    RuntimeError
        If the Gemini API call fails.
    ValueError
        If the response cannot be parsed as LLMTurnOutput.
    """
    from google.genai import types  # type: ignore[import]

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=LLMTurnOutput,
                temperature=0.4,        # low temperature for consistent extraction
                max_output_tokens=512,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API call failed: {exc}") from exc

    raw_text = response.text
    if not raw_text:
        raise ValueError("Gemini returned an empty response.")

    try:
        turn_output = LLMTurnOutput.model_validate_json(raw_text)
    except Exception as exc:
        raise ValueError(
            f"Could not parse Gemini response as LLMTurnOutput: {exc}\n"
            f"Raw response: {raw_text[:500]}"
        ) from exc

    return turn_output


# ---------------------------------------------------------------------------
# Public function — called by the route
# ---------------------------------------------------------------------------
def process_conversation_turn(request: ConversationRequest) -> ConversationResponse:
    """
    Process one turn of the conversation.

    1. Validate language.
    2. Validate message is non-empty.
    3. Get/create session state.
    4. Build Gemini prompt and call the API.
    5. Merge extracted profile_update into session profile.
    6. Update session history.
    7. Return ConversationResponse.

    Parameters
    ----------
    request : ConversationRequest

    Returns
    -------
    ConversationResponse

    Raises
    ------
    ValueError
        Invalid language or empty message (→ HTTP 400).
    EnvironmentError
        Missing API key (→ HTTP 503).
    RuntimeError
        Gemini API failure (→ HTTP 502).
    """
    # --- Input validation ---
    if request.language not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Unsupported language '{request.language}'. "
            f"Supported: {sorted(SUPPORTED_LANGUAGES)}"
        )

    message = request.message.strip()
    if not message:
        raise ValueError("Message cannot be empty.")

    # --- Session state ---
    session = _get_or_create_session(request.session_id)

    # Honour history from the request if the client is tracking it,
    # but the server-side session is authoritative for the profile.
    if request.conversation_history:
        # Sync server history from client on first turn
        if not session["history"]:
            session["history"] = [
                {"role": t.role, "content": t.content}
                for t in request.conversation_history
            ]

    # --- Build Gemini inputs ---
    system_prompt = _build_system_prompt(request.language)
    contents = _build_contents(session["history"], message)

    # --- Call Gemini ---
    client = _get_gemini_client()
    turn_output = _call_gemini(client, system_prompt, contents)

    logger.info(
        "Session %s | interview_complete=%s | profile_update=%s",
        request.session_id,
        turn_output.interview_complete,
        turn_output.profile_update,
    )

    # --- Merge profile ---
    session["profile"] = _merge_profile(
        session["profile"], turn_output.profile_update
    )

    # --- Update history ---
    session["history"].append({"role": "user", "content": message})
    session["history"].append(
        {"role": "assistant", "content": turn_output.assistant_question}
    )

    # --- Compute completeness ---
    fields_completed, fields_remaining = _profile_completeness(session["profile"])

    return ConversationResponse(
        session_id=request.session_id,
        assistant_question=turn_output.assistant_question,
        profile_update=turn_output.profile_update,
        profile=dict(session["profile"]),
        fields_completed=fields_completed,
        fields_remaining=fields_remaining,
        interview_complete=turn_output.interview_complete,
    )


# ---------------------------------------------------------------------------
# Session utilities — exposed for testing and future admin endpoints
# ---------------------------------------------------------------------------
def get_session_profile(session_id: str) -> dict | None:
    """Return the current profile for a session, or None if not found."""
    session = _sessions.get(session_id)
    return dict(session["profile"]) if session else None


def clear_session(session_id: str) -> bool:
    """Delete a session. Returns True if it existed."""
    return _sessions.pop(session_id, None) is not None


def clear_all_sessions() -> int:
    """Clear all sessions (useful for testing). Returns number cleared."""
    count = len(_sessions)
    _sessions.clear()
    return count
