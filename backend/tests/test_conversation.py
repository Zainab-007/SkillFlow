"""
Tests for the conversation engine (POST /api/conversation).

All Gemini API calls are mocked — no real API key is required.

Test coverage
-------------
1.  New conversation session returns 200 and correct shape.
2.  Existing session continuation merges profile across turns.
3.  Profile is extracted from a tailoring message.
4.  Profile updates are accumulated across multiple turns.
5.  English conversation — assistant_question is returned.
6.  Hindi conversation — language parameter accepted.
7.  Empty message returns HTTP 400.
8.  Invalid language returns HTTP 400.
9.  Missing API key returns HTTP 503.
10. Malformed LLM response (bad JSON) returns HTTP 400.
11. Interview completion sets interview_complete=True.
12. Already-known profile fields are not re-asked (profile merge).
13. skills list is extended across turns without duplicates.
14. Gemini API failure returns HTTP 502.
15. Unknown session_id starts a fresh session.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.services import conversation as conv_service

# ---------------------------------------------------------------------------
# Shared test client
# ---------------------------------------------------------------------------
client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers to build mock Gemini responses
# ---------------------------------------------------------------------------

def _make_gemini_response(
    assistant_question: str,
    profile_update: dict = None,
    interview_complete: bool = False,
) -> MagicMock:
    """Build a mock object that looks like a Gemini GenerateContentResponse."""
    payload = {
        "assistant_question": assistant_question,
        "profile_update": profile_update or {},
        "interview_complete": interview_complete,
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    return mock_response


def _patch_gemini(
    assistant_question: str = "What kind of work do you do?",
    profile_update: dict = None,
    interview_complete: bool = False,
):
    """
    Context manager: patches _get_gemini_client so no real API key is needed.
    Returns a mock client whose generate_content returns the given payload.
    """
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_gemini_response(
        assistant_question, profile_update or {}, interview_complete
    )

    def fake_get_client():
        return mock_client

    return patch(
        "app.services.conversation._get_gemini_client",
        side_effect=fake_get_client,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_sessions():
    """Ensure each test starts with a clean session store."""
    conv_service.clear_all_sessions()
    yield
    conv_service.clear_all_sessions()


# ---------------------------------------------------------------------------
# 1. New conversation session — basic shape
# ---------------------------------------------------------------------------
def test_new_session_returns_200():
    with _patch_gemini("What kind of work do you do?"):
        response = client.post("/api/conversation", json={
            "session_id": "test-001",
            "language": "en",
            "message": "Hello, I want to know about jobs.",
            "conversation_history": [],
        })
    assert response.status_code == 200


def test_new_session_response_shape():
    with _patch_gemini("What kind of work do you do?"):
        body = client.post("/api/conversation", json={
            "session_id": "test-002",
            "language": "en",
            "message": "Hello.",
        }).json()

    assert "session_id" in body
    assert "assistant_question" in body
    assert "profile_update" in body
    assert "profile" in body
    assert "fields_completed" in body
    assert "fields_remaining" in body
    assert "interview_complete" in body
    assert body["session_id"] == "test-002"
    assert body["assistant_question"] == "What kind of work do you do?"


# ---------------------------------------------------------------------------
# 2. Existing session continuation
# ---------------------------------------------------------------------------
def test_existing_session_continues():
    # Turn 1
    with _patch_gemini(
        "How long have you been doing tailoring?",
        profile_update={"current_occupation": "Tailoring"},
    ):
        body1 = client.post("/api/conversation", json={
            "session_id": "session-A",
            "language": "en",
            "message": "I do tailoring.",
        }).json()

    assert body1["profile"].get("current_occupation") == "Tailoring"

    # Turn 2 — same session_id
    with _patch_gemini(
        "Where are you located?",
        profile_update={"experience_years": 5},
    ):
        body2 = client.post("/api/conversation", json={
            "session_id": "session-A",
            "language": "en",
            "message": "I have been doing this for 5 years.",
        }).json()

    # Profile should now have both fields
    assert body2["profile"].get("current_occupation") == "Tailoring"
    assert body2["profile"].get("experience_years") == 5


# ---------------------------------------------------------------------------
# 3. Profile is extracted from a tailoring message
# ---------------------------------------------------------------------------
def test_profile_extraction_tailoring():
    with _patch_gemini(
        "What kind of garments do you usually make?",
        profile_update={
            "current_occupation": "Tailoring",
            "experience_years": 3,
            "mobility_constraint": "Home-based preferred",
        },
    ):
        body = client.post("/api/conversation", json={
            "session_id": "tailoring-session",
            "language": "en",
            "message": "I have been doing tailoring from home for three years.",
        }).json()

    assert body["profile"]["current_occupation"] == "Tailoring"
    assert body["profile"]["experience_years"] == 3
    assert body["profile"]["mobility_constraint"] == "Home-based preferred"
    assert "current_occupation" in body["fields_completed"]
    assert "experience_years" in body["fields_completed"]


# ---------------------------------------------------------------------------
# 4. Profile updates accumulate across turns
# ---------------------------------------------------------------------------
def test_profile_accumulates_across_turns():
    turns = [
        ("I work in farming.", {"current_occupation": "Farming"}, "How long have you farmed?"),
        ("About 10 years.", {"experience_years": 10}, "Where are you located?"),
        ("Rajasthan.", {"location": "Rajasthan"}, "What skills do you have?"),
    ]

    for msg, p_update, q in turns:
        with _patch_gemini(q, profile_update=p_update):
            body = client.post("/api/conversation", json={
                "session_id": "farm-session",
                "language": "en",
                "message": msg,
            }).json()

    # After all turns, the profile should have all three fields
    assert body["profile"]["current_occupation"] == "Farming"
    assert body["profile"]["experience_years"] == 10
    assert body["profile"]["location"] == "Rajasthan"


# ---------------------------------------------------------------------------
# 5. English conversation
# ---------------------------------------------------------------------------
def test_english_conversation():
    with _patch_gemini("What is your highest education level?"):
        body = client.post("/api/conversation", json={
            "session_id": "en-session",
            "language": "en",
            "message": "I want to learn a new skill.",
        }).json()
    assert body["assistant_question"] == "What is your highest education level?"
    assert body["interview_complete"] is False


# ---------------------------------------------------------------------------
# 6. Hindi conversation — language parameter accepted
# ---------------------------------------------------------------------------
def test_hindi_language_accepted():
    with _patch_gemini("आप कहाँ रहते हैं?"):
        response = client.post("/api/conversation", json={
            "session_id": "hi-session",
            "language": "hi",
            "message": "मैं सिलाई करती हूँ।",
        })
    assert response.status_code == 200
    assert response.json()["assistant_question"] == "आप कहाँ रहते हैं?"


# ---------------------------------------------------------------------------
# 7. Empty message → 400
# ---------------------------------------------------------------------------
def test_empty_message_returns_400():
    response = client.post("/api/conversation", json={
        "session_id": "empty-msg",
        "language": "en",
        "message": "",
    })
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_whitespace_only_message_returns_400():
    response = client.post("/api/conversation", json={
        "session_id": "ws-msg",
        "language": "en",
        "message": "   ",
    })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 8. Invalid language → 400
# ---------------------------------------------------------------------------
def test_invalid_language_returns_400():
    response = client.post("/api/conversation", json={
        "session_id": "lang-test",
        "language": "fr",
        "message": "Bonjour.",
    })
    assert response.status_code == 400
    assert "unsupported language" in response.json()["detail"].lower()


def test_invalid_language_marathi_returns_400():
    response = client.post("/api/conversation", json={
        "session_id": "mr-test",
        "language": "mr",
        "message": "नमस्ते.",
    })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 9. Missing API key → 503
# ---------------------------------------------------------------------------
def test_missing_api_key_returns_503():
    def raise_env_error():
        raise EnvironmentError("GEMINI_API_KEY not set")

    with patch(
        "app.services.conversation._get_gemini_client",
        side_effect=raise_env_error,
    ):
        response = client.post("/api/conversation", json={
            "session_id": "no-key-session",
            "language": "en",
            "message": "Hello.",
        })
    assert response.status_code == 503
    assert "not available" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 10. Malformed LLM response → 400
# ---------------------------------------------------------------------------
def test_malformed_llm_response_returns_400():
    """If Gemini returns JSON that doesn't match LLMTurnOutput schema, return 400."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = '{"garbage": true}'

    with patch(
        "app.services.conversation._get_gemini_client",
        return_value=mock_client,
    ):
        response = client.post("/api/conversation", json={
            "session_id": "bad-json-session",
            "language": "en",
            "message": "Hello.",
        })
    assert response.status_code == 400


def test_empty_llm_response_returns_400():
    """If Gemini returns empty text, return 400."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = ""

    with patch(
        "app.services.conversation._get_gemini_client",
        return_value=mock_client,
    ):
        response = client.post("/api/conversation", json={
            "session_id": "empty-llm-session",
            "language": "en",
            "message": "Hello.",
        })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# 11. Interview completion
# ---------------------------------------------------------------------------
def test_interview_complete_flag():
    full_profile = {
        "education": "10th pass",
        "current_occupation": "Tailoring",
        "experience_years": 3.0,
        "skills": ["Sewing", "Cutting"],
        "interests": ["Boutique management"],
        "mobility_constraint": "Home-based preferred",
        "employment_preference": "Self-employment",
        "location": "Jaipur",
    }
    with _patch_gemini(
        "Thank you! Based on your profile, here are some training suggestions.",
        profile_update=full_profile,
        interview_complete=True,
    ):
        body = client.post("/api/conversation", json={
            "session_id": "complete-session",
            "language": "en",
            "message": "I prefer working from home.",
        }).json()

    assert body["interview_complete"] is True


def test_interview_complete_with_rich_profile():
    """Simulate a complete profile and confirm interview_complete=True."""
    # First build up a rich profile
    session_id = "rich-session"
    turns = [
        ({"current_occupation": "Tailoring", "experience_years": 5.0}, False, "What skills?"),
        ({"skills": ["Sewing", "Embroidery"]}, False, "What level?"),
        ({"education": "10th", "interests": ["Garments"]}, False, "Where are you?"),
        ({
            "location": "Pune",
            "employment_preference": "Self-employment",
            "mobility_constraint": "Home-based preferred",
        }, True, "Great, all set!"),
    ]
    for p_update, complete, q in turns:
        with _patch_gemini(q, profile_update=p_update, interview_complete=complete):
            body = client.post("/api/conversation", json={
                "session_id": session_id,
                "language": "en",
                "message": "...",
            }).json()

    assert body["interview_complete"] is True
    assert "current_occupation" in body["fields_completed"]
    assert "skills" in body["fields_completed"]
    assert "experience_years" in body["fields_completed"]
    assert "interests" in body["fields_completed"]


# ---------------------------------------------------------------------------
# 11b. Regression: Incomplete profile must NOT complete interview early
# ---------------------------------------------------------------------------
def test_incomplete_profile_missing_experience_and_interests_does_not_complete():
    """
    Regression test for SIH user test bug:
    A profile with occupation, skills, education, location, employment preference,
    and work setting, but WITHOUT experience and interests, must NOT be marked complete,
    even if the LLM erroneously returns interview_complete=True while asking a question.
    """
    session_id = "test-incomplete-user-bug-session"
    partial_profile = {
        "current_occupation": "Tailoring",
        "education": "8th pass",
        "location": "Malad, Mumbai",
        "employment_preference": "Self-employment",
        "mobility_constraint": "Home-based preferred",
        "skills": ["Silayi", "Tailoring"],
        # Notice: experience_years and interests are intentionally missing
    }

    with _patch_gemini(
        assistant_question="बहुत बढ़िया! आपके पास सिलाई का कितने साल का अनुभव है?",
        profile_update=partial_profile,
        interview_complete=True,  # LLM erroneously suggests completion while asking a question
    ):
        body = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "hi",
            "message": "apna khud ka",
        }).json()

    # Must stay active so user can answer the follow-up question
    assert body["interview_complete"] is False
    assert "experience_years" in body["fields_remaining"]
    assert "interests" in body["fields_remaining"]
    assert body["assistant_question"] == "बहुत बढ़िया! आपके पास सिलाई का कितने साल का अनुभव है?"


def test_complete_profile_with_all_required_fields_does_complete():
    """
    Test that when all 8 required profile fields are present and LLM signals completion,
    the backend confirms completion (interview_complete=True).
    """
    session_id = "test-fully-complete-session"
    full_profile = {
        "current_occupation": "Tailoring",
        "education": "8th pass",
        "location": "Malad, Mumbai",
        "employment_preference": "Self-employment",
        "mobility_constraint": "Home-based preferred",
        "skills": ["Silayi", "Tailoring"],
        "experience_years": 4.0,
        "interests": ["Boutique business", "Garment design"],
    }

    with _patch_gemini(
        assistant_question="बहुत धन्यवाद! आपकी प्रोफाइल पूरी हो गई है। अब हम आपके लिए अवसर ढूंढ रहे हैं।",
        profile_update=full_profile,
        interview_complete=True,
    ):
        body = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "hi",
            "message": "मुझे 4 साल का तजुर्बा है और मैं बुटीक का काम सीखना चाहती हूँ।",
        }).json()

    assert body["interview_complete"] is True
    assert len(body["fields_remaining"]) == 0
    assert len(body["fields_completed"]) == 8



# ---------------------------------------------------------------------------
# 12. No re-asking known fields (profile merge correctness)
# ---------------------------------------------------------------------------
def test_known_field_not_overwritten_with_empty():
    """An empty profile_update should not clear existing fields."""
    session_id = "no-overwrite-session"

    # Turn 1: set current_occupation
    with _patch_gemini("How many years?", profile_update={"current_occupation": "Carpentry"}):
        client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "en",
            "message": "I am a carpenter.",
        })

    # Turn 2: LLM returns empty profile_update
    with _patch_gemini("Where are you based?", profile_update={}):
        body = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "en",
            "message": "About 8 years.",
        }).json()

    # current_occupation should still be present
    assert body["profile"]["current_occupation"] == "Carpentry"


# ---------------------------------------------------------------------------
# 13. skills list extended without duplicates
# ---------------------------------------------------------------------------
def test_skills_list_extended_without_duplicates():
    session_id = "skills-dedup-session"

    with _patch_gemini("Any other skills?", profile_update={"skills": ["Sewing", "Tailoring"]}):
        client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "en",
            "message": "I know sewing and tailoring.",
        })

    # Second turn adds Alteration + a duplicate of Sewing
    with _patch_gemini("Good.", profile_update={"skills": ["Sewing", "Alteration"]}):
        body = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "en",
            "message": "Also alteration.",
        }).json()

    skills = body["profile"].get("skills", [])
    assert "Sewing" in skills
    assert "Tailoring" in skills
    assert "Alteration" in skills
    # Sewing should appear only once
    assert skills.count("Sewing") == 1


# ---------------------------------------------------------------------------
# 14. Gemini API failure → 502
# ---------------------------------------------------------------------------
def test_gemini_api_failure_returns_502():
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Network timeout")

    with patch(
        "app.services.conversation._get_gemini_client",
        return_value=mock_client,
    ):
        response = client.post("/api/conversation", json={
            "session_id": "fail-session",
            "language": "en",
            "message": "Tell me about jobs.",
        })
    assert response.status_code == 502


# ---------------------------------------------------------------------------
# 15. Unknown session_id starts a fresh session
# ---------------------------------------------------------------------------
def test_unknown_session_starts_fresh():
    with _patch_gemini("What work do you do?", profile_update={"location": "Delhi"}):
        body = client.post("/api/conversation", json={
            "session_id": "brand-new-xyz-9999",
            "language": "en",
            "message": "I am from Delhi.",
        }).json()

    assert body["profile"]["location"] == "Delhi"


# ---------------------------------------------------------------------------
# Ensure all previously passing tests still pass
# (smoke-check: re-test the health endpoint)
# ---------------------------------------------------------------------------
def test_health_still_passes():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_match_still_passes():
    response = client.post("/api/match", json={
        "skills": ["Sewing"],
        "current_occupation": "Tailoring",
    })
    assert response.status_code == 200
    assert len(response.json()["results"]) == 20


# ---------------------------------------------------------------------------
# 16. Regression: Short context-dependent reply in multi-turn ("apna khud ka")
# ---------------------------------------------------------------------------
def test_short_context_dependent_reply_multi_turn():
    """
    Regression test: Verifies that short context-dependent replies (e.g. 'apna khud ka')
    in multi-turn sessions correctly update the profile and return 200 without upstream schema errors.
    """
    session_id = "regression-short-context-session"

    # Turn 1: Initial greeting and location
    with _patch_gemini(
        assistant_question="नमस्ते! आप क्या काम करते हैं?",
        profile_update={"location": "Jaipur"},
    ):
        r1 = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "hi",
            "message": "नमस्ते, मैं जयपुर से हूँ।",
        })
        assert r1.status_code == 200
        assert r1.json()["profile"]["location"] == "Jaipur"
        assert "location" in r1.json()["fields_completed"]

    # Turn 2: Mention occupation
    with _patch_gemini(
        assistant_question="क्या आप खुद का काम शुरू करना चाहते हैं या नौकरी करना चाहते हैं?",
        profile_update={"current_occupation": "Tailoring", "skills": ["Sewing"]},
    ):
        r2 = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "hi",
            "message": "मैं घर पर सिलाई का काम करती हूँ।",
        })
        assert r2.status_code == 200
        assert r2.json()["profile"]["current_occupation"] == "Tailoring"
        assert "current_occupation" in r2.json()["fields_completed"]

    # Turn 3: Short context-dependent reply: "apna khud ka"
    with _patch_gemini(
        assistant_question="बहुत बढ़िया! आपके पास सिलाई का कितने साल का अनुभव है?",
        profile_update={"employment_preference": "Self-employment"},
    ):
        r3 = client.post("/api/conversation", json={
            "session_id": session_id,
            "language": "hi",
            "message": "apna khud ka",
        })
        assert r3.status_code == 200
        body = r3.json()
        assert body["profile"]["employment_preference"] == "Self-employment"
        assert body["profile"]["current_occupation"] == "Tailoring"
        assert body["profile"]["location"] == "Jaipur"
        assert "employment_preference" in body["fields_completed"]


