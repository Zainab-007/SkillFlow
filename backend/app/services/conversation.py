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
    "current_activity",
    "experience_years",
    "skills",
    "interests",
    "preferred_specialization",
    "mobility_constraint",
    "employment_preference",
    "location",
]

_CORE_PROFILE_FIELDS = [
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


def _merge_profile(existing: dict, update: Any) -> dict:
    """
    Merge a profile update into the existing session profile.

    Rules:
    - String fields: overwrite only if the new value is non-empty.
    - List fields (skills, interests): extend, deduplicating case-insensitively.
      Remove placeholder values like "open to any" if concrete values arrive.
    - Numeric fields (experience_years): overwrite if >= 0.
    - Preferred specialization: preserve and also reflect in interests if not already present.
    - Preserves earlier useful information across multiple turns.
    """
    if hasattr(update, "model_dump"):
        update_data = update.model_dump(exclude_none=True)
    elif isinstance(update, dict):
        update_data = update
    else:
        update_data = {}

    valid_string_fields = {
        "education",
        "current_occupation",
        "current_activity",
        "preferred_specialization",
        "mobility_constraint",
        "employment_preference",
        "location",
    }
    valid_list_fields = {"skills", "interests"}
    valid_numeric_fields = {"experience_years"}

    merged = dict(existing)

    for key, value in update_data.items():
        if key in valid_string_fields:
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()

        elif key in valid_list_fields:
            if isinstance(value, list):
                current = merged.get(key, [])
                # If current only has generic placeholders and new concrete values arrived, clear placeholders
                placeholder_terms = {
                    "open to any", "open to anything", "none",
                    "not specified", "any", "no preference", "project building",
                }
                if any(isinstance(v, str) and v.lower().strip() not in placeholder_terms for v in value):
                    current = [v for v in current if isinstance(v, str) and v.lower().strip() not in placeholder_terms]

                # Deduplicate case-insensitively, preserving order
                existing_lower = {v.lower() for v in current if isinstance(v, str)}
                for item in value:
                    if isinstance(item, str) and item.strip():
                        if item.strip().lower() not in existing_lower:
                            current.append(item.strip())
                            existing_lower.add(item.strip().lower())
                merged[key] = current

        elif key in valid_numeric_fields:
            if isinstance(value, (int, float)) and value >= 0:
                merged[key] = value

    # If preferred_specialization is set, ensure it is also represented in interests
    spec = merged.get("preferred_specialization")
    if spec and isinstance(spec, str) and spec.strip():
        cur_interests = merged.get("interests", [])
        if not any(spec.strip().lower() == i.lower() for i in cur_interests):
            cur_interests.append(spec.strip())
            merged["interests"] = cur_interests

    return merged


def _profile_completeness(profile: dict) -> tuple[list[str], list[str]]:
    """
    Return (fields_completed, fields_remaining) based on the current profile.

    A list field counts as complete when it has at least one entry.
    A scalar field counts as complete when it has a non-None, non-empty value.
    Note: current_activity can satisfy the current_occupation requirement.
    """
    completed = []
    remaining = []

    for field in _CORE_PROFILE_FIELDS:
        value = profile.get(field)
        # If current_occupation is not set, but current_activity or skills exist, count occupation as completed
        if field == "current_occupation" and (value is None or (isinstance(value, str) and not value.strip())):
            act = profile.get("current_activity")
            skills = profile.get("skills")
            if (isinstance(act, str) and act.strip()) or (isinstance(skills, list) and len(skills) > 0):
                completed.append(field)
                continue

        if value is None:
            remaining.append(field)
        elif isinstance(value, list) and len(value) == 0:
            remaining.append(field)
        elif isinstance(value, str) and not value.strip():
            remaining.append(field)
        else:
            completed.append(field)

    return completed, remaining


def is_profile_sufficient_for_completion(
    profile: dict,
    turn_number: int = 1,
) -> bool:
    """
    Deterministically validate whether the profile contains sufficient information
    to support meaningful livelihood and skilling recommendations.

    Required fields:
      - education: non-empty string (e.g. '8th pass', '10th pass', 'No formal schooling')
      - current_occupation OR current_activity OR skills non-empty
      - experience_years: numeric (>= 0, 0.0 is valid for beginners/no prior experience)
      - skills: non-empty list
      - interests: non-empty list OR preferred_specialization
      - mobility_constraint: non-empty string (e.g. 'Home-based preferred', 'None')
      - employment_preference: non-empty string ('Self-employment', 'Wage-employment', 'Either')
      - location: non-empty string (city, district, town, or state)

    Safety fallback:
      If turn_number >= 10 (user has engaged extensively), allow completion if at least
      core livelihood fields are satisfied (education, occupation/skills, employment_preference, location).
    """
    edu = profile.get("education")
    has_edu = isinstance(edu, str) and bool(edu.strip())

    occ = profile.get("current_occupation")
    act = profile.get("current_activity")
    skills = profile.get("skills") or []
    has_skills = isinstance(skills, list) and len(skills) > 0
    has_occ = (isinstance(occ, str) and bool(occ.strip())) or (isinstance(act, str) and bool(act.strip())) or has_skills

    exp = profile.get("experience_years")
    has_exp = exp is not None and isinstance(exp, (int, float))

    interests = profile.get("interests") or []
    spec = profile.get("preferred_specialization")
    has_interests = (isinstance(interests, list) and len(interests) > 0) or (isinstance(spec, str) and bool(spec.strip()))

    mob = profile.get("mobility_constraint")
    has_mob = isinstance(mob, str) and bool(mob.strip())

    pref = profile.get("employment_preference")
    has_pref = isinstance(pref, str) and bool(pref.strip())

    loc = profile.get("location")
    has_loc = isinstance(loc, str) and bool(loc.strip())

    # Full completeness check
    if (
        has_edu
        and has_occ
        and has_skills
        and has_exp
        and has_interests
        and has_mob
        and has_pref
        and has_loc
    ):
        return True

    # Extended turn safety cap (prevents trapping users who decline/skip optional details)
    if turn_number >= 10 and has_edu and has_occ and has_pref and has_loc:
        return True

    return False


def _build_system_prompt(
    language: str,
    current_profile: dict | None = None,
    fields_remaining: list[str] | None = None,
) -> str:
    """
    Build the system prompt that instructs Gemini how to behave.

    The prompt incorporates the currently collected profile and remaining fields
    so Gemini asks targeted questions and never declares completion prematurely.
    """
    lang_name = "English" if language == "en" else "Hindi"

    profile_summary = ""
    if current_profile:
        lines = []
        for k in _ALL_PROFILE_FIELDS:
            v = current_profile.get(k)
            lines.append(f"  - {k}: {v if v is not None and v != '' and v != [] else 'Not yet gathered'}")
        profile_summary = "\nCURRENT PROFILE STATUS:\n" + "\n".join(lines)

    remaining_summary = ""
    if fields_remaining:
        remaining_summary = (
            f"\nFIELDS STILL MISSING: {', '.join(fields_remaining)}\n"
            "INSTRUCTION FOR NEXT TURN: Ask ONE natural, encouraging question specifically targeting one of these missing fields."
        )
    elif fields_remaining is not None and len(fields_remaining) == 0:
        remaining_summary = (
            "\nALL REQUIRED FIELDS HAVE BEEN GATHERED!\n"
            "Your assistant_question must be a warm closing statement thanking the user and informing "
            "them that their profile is ready for livelihood recommendations. DO NOT ask any further questions. "
            "Set interview_complete=true."
        )

    return f"""You are a warm, patient livelihood counsellor helping individuals in India \
explore skill-development and training opportunities under PM-AJAY.

Your goal is to build a structured livelihood profile through natural conversation.
You collect information across these profile fields:
- education (e.g. "5th pass", "8th pass", "10th pass", "12th pass", "Graduate", or "No formal schooling")
- current_occupation (formal job/trade e.g. "Tailoring", "Farming", "Homemaker", "Student", "None")
- current_activity (what the user is currently doing practically, e.g. "Tailoring clothes at home", "Cultivating crops on family land", "Building projects", "Food preparation", "Assisting at local shop")
- experience_years (numeric, years of work experience; use 0.0 if beginner or no prior formal work)
- skills (list of practical, artisanal, operational, or technical skills the person already has, e.g. ["Sewing", "Cutting fabric"] or ["Crop cultivation", "Irrigation"] or ["Food prep", "Cooking"] or ["Python", "MySQL"])
- interests (list of trades, skills, or domains they want to learn or work in, e.g. ["Apparel & Fashion Design"], ["Organic Farming"], ["Food Processing"], ["Beauty & Wellness"], ["Web Development"])
- preferred_specialization (specific niche or direction within a trade, e.g. "Fashion Design", "Dairy Farming", "Bakery", "Backend Development", "Bridal Makeup")
- mobility_constraint (e.g. "Home-based preferred", "Can travel locally", "None")
- employment_preference ("Self-employment", "Wage-employment", or "Either")
- location (city, district, town, or state)
{profile_summary}{remaining_summary}

SEMANTIC EXTRACTION RULES (GENERIC ACROSS ALL LIVELIHOOD DOMAINS):
1. Distinguish CURRENT ACTIVITY vs CURRENT OCCUPATION vs INTEREST vs PREFERRED SPECIALIZATION vs EXISTING SKILLS:
   - current_activity: Practical day-to-day engagement or self-directed project work (e.g. "stitching clothes", "farming paddy", "building software projects", "cooking meals"). Do NOT record ongoing work activities as a generic interest.
   - current_occupation: Formal occupational title or status (e.g. "Tailor", "Farmer", "Homemaker", "Student", "Unemployed").
   - interests: Broader trades or vocational areas they want to explore or enter (e.g. "Fashion Design", "Dairy farming", "Web Development", "Beauty services", "Food processing").
   - preferred_specialization: Specific sub-area, niche, or direction they prefer within a trade (e.g. "Fashion Design", "Dairy Farming", "Backend Development", "Hair Styling", "Bakery").
   - skills: Concrete practical or technical skills the person already knows (e.g. ["Sewing", "Stitching"], ["Python", "Java", "MySQL"], ["Animal care"], ["Cooking"]). Extract verified skills even when stated naturally in a sentence. Never list role requirements or aspirational goals as existing skills unless confirmed by the user.
2. Consider the ENTIRE conversation history when updating the profile:
   - Explicit later clarification must NOT erase earlier useful information.
   - Skills and interests accumulate across turns.
3. Ask ONLY ONE short, voice-friendly question per turn.
4. NEVER ask for information already known in the profile status above.
5. Extract information silently into profile_update — do NOT narrate what you extracted.
6. Do NOT fabricate information. Only record what the user clearly states or implies.
7. If the user's answer is ambiguous, ask a natural clarification.
8. Target missing fields: keep each turn focused on asking for one missing field.
9. Handle declines gracefully: If the user says they don't know, have no preference, or want to skip \
(e.g., "no experience", "no preference", "open to anything"), record that (e.g., experience_years: 0.0, \
interests: ["Open to any"], mobility_constraint: "None") and move on to the next missing field without repeating.
10. INTERVIEW COMPLETION RULES:
    - NEVER set interview_complete=true while still asking a question.
    - Set interview_complete=false on every intermediate turn while asking questions.
    - Set interview_complete=true ONLY when all required fields have been addressed AND your assistant_question \
is a final closing statement thanking the user.
11. Ask questions in {lang_name}. Keep internal profile field names in English.
12. Your tone should be encouraging, respectful, and conversational, NOT like an interrogation or form.

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
        # Explicitly search for backend/.env relative to this file
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parent.parent.parent
        load_dotenv(backend_dir / ".env")
        load_dotenv()
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

    # Models to attempt in order of preference.
    # Flash-lite models have distinct, higher free-tier request quotas on Google AI Studio.
    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.5-flash",
        "gemini-3.8-flash",
        "gemini-flash-latest",
    ]
    response = None
    last_exc = None

    for model_name in candidate_models:
        try:
            config_params = {
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
                "response_schema": LLMTurnOutput,
                "temperature": 0.4,        # low temperature for consistent extraction
                "max_output_tokens": 1024,
            }
            # thinking_budget is only supported on standard flash/pro models, not flash-lite
            if "lite" not in model_name:
                config_params["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(**config_params),
            )
            logger.info("Gemini generation succeeded with model: %s", model_name)
            break
        except Exception as exc:
            last_exc = exc
            status_code = getattr(exc, "code", getattr(exc, "status_code", None))
            logger.warning(
                "Gemini attempt failed | Model: %s | Status: %s | Type: %s | Error: %s",
                model_name,
                status_code,
                type(exc).__name__,
                exc,
            )

    if response is None:
        status_code = getattr(last_exc, "code", getattr(last_exc, "status_code", None))
        raise RuntimeError(
            f"Gemini API call failed (status={status_code}, type={type(last_exc).__name__}): {last_exc}"
        ) from last_exc

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

    turn_number = (len(session["history"]) // 2) + 1
    logger.info(
        "Conversation Turn | Session: %s | Turn: %d | Language: %s | User Input: %s",
        request.session_id,
        turn_number,
        request.language,
        message[:100],
    )

    # --- Determine current profile completeness before LLM call ---
    _, fields_remaining_prior = _profile_completeness(session["profile"])

    # --- Build Gemini inputs with live profile context ---
    system_prompt = _build_system_prompt(
        language=request.language,
        current_profile=session["profile"],
        fields_remaining=fields_remaining_prior,
    )
    contents = _build_contents(session["history"], message)

    # --- Call Gemini ---
    client = _get_gemini_client()
    turn_output = _call_gemini(client, system_prompt, contents)

    profile_update_dict = (
        turn_output.profile_update.model_dump(exclude_none=True)
        if hasattr(turn_output.profile_update, "model_dump")
        else turn_output.profile_update
    )

    logger.info(
        "Conversation Response | Session: %s | Turn: %d | LLM complete=%s | Extracted: %s",
        request.session_id,
        turn_number,
        turn_output.interview_complete,
        profile_update_dict,
    )

    # --- Merge profile ---
    session["profile"] = _merge_profile(
        session["profile"], profile_update_dict
    )

    # --- Update history ---
    session["history"].append({"role": "user", "content": message})
    session["history"].append(
        {"role": "assistant", "content": turn_output.assistant_question}
    )

    # --- Compute completeness after profile update ---
    fields_completed, fields_remaining = _profile_completeness(session["profile"])

    # --- Deterministic completion check ---
    # The interview is complete ONLY if the profile data is actually sufficient to recommend pathways.
    # LLM cannot mark complete early while required fields are missing.
    is_sufficient = is_profile_sufficient_for_completion(session["profile"], turn_number)
    final_interview_complete = is_sufficient and (
        turn_output.interview_complete or len(fields_remaining) == 0
    )

    logger.info(
        "Conversation Completion Decision | Session: %s | Turn: %d | "
        "LLM_suggested=%s | is_sufficient=%s | final_complete=%s | Remaining: %s",
        request.session_id,
        turn_number,
        turn_output.interview_complete,
        is_sufficient,
        final_interview_complete,
        fields_remaining,
    )

    return ConversationResponse(
        session_id=request.session_id,
        assistant_question=turn_output.assistant_question,
        profile_update=profile_update_dict,
        profile=dict(session["profile"]),
        fields_completed=fields_completed,
        fields_remaining=fields_remaining,
        interview_complete=final_interview_complete,
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
