"""
Backend API tests for SkillFlow.

Run from the backend/ directory:

    pytest tests/ -v

Requirements (install alongside main dependencies):
    pip install pytest httpx

Test coverage
-------------
1.  Health endpoint.
2.  Knowledge base loading.
3.  Get all roles — count and structure.
4.  Get role by ID — valid ID returns the correct role.
5.  Invalid role ID returns HTTP 404.
6.  Sector listing — correct keys and counts.
7.  Matching endpoint accepts a full profile.
8.  Matching results are sorted by score descending.
9.  Empty/minimal profile does not crash the backend.
10. Matching the tailoring profile places apparel roles in the top results.
11. Matching: employment preference bonus applied.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

# ---------------------------------------------------------------------------
# Shared test client
# ---------------------------------------------------------------------------
client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixture: tailoring profile (the canonical example from the problem statement)
# ---------------------------------------------------------------------------
TAILORING_PROFILE = {
    "education": "12th",
    "current_occupation": "Tailoring",
    "experience_years": 3,
    "skills": ["Sewing", "Tailoring", "Alteration"],
    "interests": ["Fashion"],
    "mobility_constraint": "Home-based preferred",
    "employment_preference": "Self-employment",
    "location": "Mumbai",
}

# ---------------------------------------------------------------------------
# 1. Health endpoint
# ---------------------------------------------------------------------------
def test_health_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "SkillFlow backend"


# ---------------------------------------------------------------------------
# 2. Knowledge base loading
# ---------------------------------------------------------------------------
def test_knowledge_base_loads():
    """The knowledge base must load without error on startup."""
    from app.services.knowledge_base import get_knowledge_base
    kb = get_knowledge_base()
    assert kb is not None
    assert len(kb.roles) > 0
    assert kb.version is not None


# ---------------------------------------------------------------------------
# 3. Get all roles — count and structure
# ---------------------------------------------------------------------------
def test_get_all_roles_returns_list():
    response = client.get("/api/knowledge/roles")
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    # We have exactly 20 roles in the current knowledge base
    assert len(roles) == 20


def test_each_role_has_required_fields():
    response = client.get("/api/knowledge/roles")
    roles = response.json()
    required_fields = {
        "id", "title", "qp_code", "nsqf_level", "sector",
        "required_skills", "gap_skills_covered", "eligibility",
        "qualification", "duration", "description",
        "employment_type", "source", "last_verified",
    }
    for role in roles:
        missing = required_fields - set(role.keys())
        assert not missing, f"Role {role.get('id')} missing fields: {missing}"


# ---------------------------------------------------------------------------
# 4. Get role by ID — valid ID
# ---------------------------------------------------------------------------
def test_get_role_by_id_valid():
    response = client.get("/api/knowledge/roles/T-001")
    assert response.status_code == 200
    role = response.json()
    assert role["id"] == "T-001"
    assert role["title"] == "Sewing Machine Operator"
    assert role["sector"] == "Apparel & Textiles"


def test_get_role_by_id_case_insensitive():
    """Role IDs should be looked up case-insensitively."""
    response = client.get("/api/knowledge/roles/t-001")
    assert response.status_code == 200
    assert response.json()["id"] == "T-001"


# ---------------------------------------------------------------------------
# 5. Invalid role ID returns 404
# ---------------------------------------------------------------------------
def test_get_role_invalid_id_returns_404():
    response = client.get("/api/knowledge/roles/NONEXISTENT-999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 6. Sector listing
# ---------------------------------------------------------------------------
def test_sectors_response_structure():
    response = client.get("/api/knowledge/sectors")
    assert response.status_code == 200
    body = response.json()
    assert "sectors" in body
    sectors = body["sectors"]
    assert isinstance(sectors, list)
    assert len(sectors) > 0
    for entry in sectors:
        assert "name" in entry
        assert "count" in entry
        assert isinstance(entry["count"], int)
        assert entry["count"] > 0


def test_sectors_total_matches_role_count():
    """Sum of sector counts must equal total number of roles."""
    sectors_resp = client.get("/api/knowledge/sectors").json()
    roles_resp = client.get("/api/knowledge/roles").json()
    total_from_sectors = sum(s["count"] for s in sectors_resp["sectors"])
    assert total_from_sectors == len(roles_resp)


def test_sectors_sorted_alphabetically():
    response = client.get("/api/knowledge/sectors")
    sectors = response.json()["sectors"]
    names = [s["name"] for s in sectors]
    assert names == sorted(names)


# ---------------------------------------------------------------------------
# 7. Matching endpoint — full profile
# ---------------------------------------------------------------------------
def test_match_endpoint_accepts_full_profile():
    response = client.post("/api/match", json=TAILORING_PROFILE)
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert "total_roles_evaluated" in body
    assert body["total_roles_evaluated"] == 20


def test_match_response_has_required_fields():
    response = client.post("/api/match", json=TAILORING_PROFILE)
    results = response.json()["results"]
    assert len(results) > 0
    for r in results:
        assert "role_id" in r
        assert "title" in r
        assert "score" in r
        assert "matched_skills" in r
        assert "skill_gaps" in r
        assert "employment_type" in r


# ---------------------------------------------------------------------------
# 8. Matching results are sorted by score descending
# ---------------------------------------------------------------------------
def test_match_results_sorted_by_score_descending():
    response = client.post("/api/match", json=TAILORING_PROFILE)
    results = response.json()["results"]
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), \
        "Match results should be sorted by score descending"


# ---------------------------------------------------------------------------
# 9. Empty / minimal profile does not crash
# ---------------------------------------------------------------------------
def test_match_empty_profile():
    """An empty profile should return a 200 with all roles scored (likely 0)."""
    response = client.post("/api/match", json={})
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert len(body["results"]) == 20  # all roles returned


def test_match_skills_only():
    """A profile with only skills should still match cleanly."""
    response = client.post("/api/match", json={"skills": ["Sewing"]})
    assert response.status_code == 200
    assert len(response.json()["results"]) == 20


def test_match_no_skills():
    """A profile with no skills should not crash."""
    response = client.post("/api/match", json={"current_occupation": "Farming"})
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 10. Tailoring profile → apparel roles in top results
# ---------------------------------------------------------------------------
def test_tailoring_profile_returns_apparel_roles_near_top():
    response = client.post("/api/match", json=TAILORING_PROFILE)
    results = response.json()["results"]
    # The top 5 results should contain at least one Apparel & Textiles role
    top_sectors = [r["sector"] for r in results[:5]]
    assert "Apparel & Textiles" in top_sectors, \
        f"Expected Apparel & Textiles in top 5, got: {top_sectors}"


def test_tailoring_profile_score_is_nonzero():
    response = client.post("/api/match", json=TAILORING_PROFILE)
    results = response.json()["results"]
    top = results[0]
    assert top["score"] > 0.0, "Top result should have a non-zero score"


def test_tailoring_self_employed_tailor_is_matched():
    """T-002 (Self-Employed Tailor) should appear in the results."""
    response = client.post("/api/match", json=TAILORING_PROFILE)
    results = response.json()["results"]
    ids = [r["role_id"] for r in results]
    assert "T-002" in ids, "Self-Employed Tailor (T-002) should be in results"


def test_tailoring_matched_skills_populated():
    """The top tailoring result should have at least one matched skill."""
    response = client.post("/api/match", json=TAILORING_PROFILE)
    results = response.json()["results"]
    top = results[0]
    assert len(top["matched_skills"]) > 0, \
        "Top result should have matched_skills populated"


# ---------------------------------------------------------------------------
# 11. Employment preference bonus
# ---------------------------------------------------------------------------
def test_self_employment_preference_scores_higher_for_matching_roles():
    """
    Compare scores of a role that supports self-employment against the same
    role when the user has no preference.  The self-employment role should
    score at least as high.
    """
    with_pref = client.post("/api/match", json=TAILORING_PROFILE).json()
    no_pref = client.post(
        "/api/match",
        json={**TAILORING_PROFILE, "employment_preference": None},
    ).json()

    def get_score(results, role_id):
        for r in results:
            if r["role_id"] == role_id:
                return r["score"]
        return None

    # T-002 Self-Employed Tailor supports self-employment
    score_with = get_score(with_pref["results"], "T-002")
    score_without = get_score(no_pref["results"], "T-002")

    assert score_with is not None
    assert score_without is not None
    assert score_with >= score_without, \
        "Self-employment preference bonus should not decrease the score"
