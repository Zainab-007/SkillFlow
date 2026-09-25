"""
Tests for the SkillFlow livelihood recommendation and pathway system.

Verifies:
1. Profile with cooking skills ranks Food Processing / cooking roles appropriately.
2. Profile with tailoring/stitching/silayi skills ranks apparel roles appropriately.
3. Skills + interests influence ranking.
4. Employment preference influences alignment and scoring.
5. Actionable skill gaps are returned.
6. Maximum 3 recommendations are returned.
7. Empty / minimal profile is handled safely.
8. Explanations use only grounded profile/role facts (no invented claims).
9. Realistic test profile (Homemaker with Cooking & Tailoring) produces meaningful top 3 matches.
10. POST /api/recommendations accepts both wrapped {"profile": ...} and bare profile shapes.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.profile import UserProfile
from app.services.recommendations import generate_recommendations

client = TestClient(app)

# Canonical realistic test profile from Milestone specification
REALISTIC_HOMEMAKER_PROFILE = {
    "current_occupation": "Homemaker",
    "experience_years": 5.0,
    "education": "12th pass",
    "location": "Palghar West",
    "employment_preference": "Wage-employment",
    "mobility_constraint": "Home-based preferred / can travel locally",
    "skills": ["Cooking", "Tailoring"],
    "interests": ["Cooking", "Tailoring"],
}


# ---------------------------------------------------------------------------
# 1. Cooking skills → Food Products Packaging Technician ranks near top
# ---------------------------------------------------------------------------
def test_cooking_profile_ranks_food_processing():
    profile_data = {
        "skills": ["Cooking", "Food Handling"],
        "interests": ["Cooking", "Food Processing"],
        "employment_preference": "Wage-employment",
    }
    response = client.post("/api/recommendations", json={"profile": profile_data})
    assert response.status_code == 200
    data = response.json()
    assert data["total_recommended"] >= 1
    top_role = data["recommendations"][0]
    assert top_role["role_id"] == "F-001"
    assert "Food" in top_role["sector"]
    assert len(top_role["matched_skills"]) > 0


# ---------------------------------------------------------------------------
# 2. Tailoring / Silayi skills → Apparel roles rank near top
# ---------------------------------------------------------------------------
def test_tailoring_stitching_ranks_apparel():
    # Test vernacular / Hinglish term "silayi"
    profile_data = {
        "skills": ["silayi", "stitching"],
        "interests": ["garments", "tailoring"],
        "employment_preference": "Self-employment",
    }
    response = client.post("/api/recommendations", json={"profile": profile_data})
    assert response.status_code == 200
    data = response.json()
    assert data["total_recommended"] >= 1
    top_role = data["recommendations"][0]
    assert top_role["sector"] == "Apparel & Textiles"
    assert top_role["role_id"] in {"T-001", "T-002", "T-003"}


# ---------------------------------------------------------------------------
# 3. Skills + interests influence ranking
# ---------------------------------------------------------------------------
def test_skills_and_interests_influence_ranking():
    # Without digital interest
    base_data = {
        "skills": ["Data Entry", "Typing"],
        "interests": [],
    }
    r_base = client.post("/api/recommendations", json={"profile": base_data}).json()
    top_base = r_base["recommendations"][0]

    # With digital interest
    boosted_data = {
        "skills": ["Data Entry", "Typing"],
        "interests": ["Digital & Entrepreneurship"],
    }
    r_boosted = client.post("/api/recommendations", json={"profile": boosted_data}).json()
    top_boosted = r_boosted["recommendations"][0]

    assert top_boosted["role_id"] == "D-001"
    assert top_boosted["match_score"] > top_base["match_score"]
    assert "Digital & Entrepreneurship" in top_boosted["matched_interests"]


# ---------------------------------------------------------------------------
# 4. Employment preference influences alignment
# ---------------------------------------------------------------------------
def test_employment_preference_influence():
    # T-003 only supports wage-employment
    # When user prefers Wage-employment, T-003 gets the preference bonus (+0.05)
    # When user prefers Self-employment, T-003 does NOT get the bonus
    profile_wage = {
        "skills": ["Sewing"],
        "employment_preference": "Wage-employment",
    }
    r_wage = client.post("/api/recommendations", json={"profile": profile_wage}).json()
    t003_wage = next(r for r in r_wage["recommendations"] if r["role_id"] == "T-003")

    profile_self = {
        "skills": ["Sewing"],
        "employment_preference": "Self-employment",
    }
    r_self = client.post("/api/recommendations", json={"profile": profile_self}).json()
    t003_self = next(r for r in r_self["recommendations"] if r["role_id"] == "T-003")

    assert t003_wage["match_score"] > t003_self["match_score"]
    assert "Wage-employment" in t003_wage["preference_alignment"]



# ---------------------------------------------------------------------------
# 5. Skill gaps are returned
# ---------------------------------------------------------------------------
def test_skill_gaps_returned():
    profile_data = {
        "skills": ["Sewing"],
        "current_occupation": "Tailoring",
    }
    response = client.post("/api/recommendations", json={"profile": profile_data})
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    assert len(recs) > 0
    for r in recs:
        assert isinstance(r["skills_to_develop"], list)
        assert len(r["skills_to_develop"]) > 0
        assert isinstance(r["skill_gaps"], list)
        # Skills user already has must not be in skills_to_develop
        for s in r["skills_already_have"]:
            assert s not in r["skills_to_develop"]


# ---------------------------------------------------------------------------
# 6. Maximum 3 recommendations are returned
# ---------------------------------------------------------------------------
def test_maximum_3_recommendations():
    # Profile with broad skills that could match many sectors
    broad_profile = {
        "skills": ["Sewing", "Cooking", "Carpentry", "Data Entry", "Farming"],
        "interests": ["Apparel", "Food", "Digital"],
    }
    response = client.post("/api/recommendations", json={"profile": broad_profile})
    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) <= 3
    assert data["total_recommended"] <= 3


# ---------------------------------------------------------------------------
# 7. Empty / insufficient profile is handled safely
# ---------------------------------------------------------------------------
def test_empty_profile_handled_safely():
    response = client.post("/api/recommendations", json={"profile": {}})
    assert response.status_code == 200
    data = response.json()
    assert data["total_recommended"] == 0
    assert data["recommendations"] == []
    assert data["total_evaluated"] == 20


# ---------------------------------------------------------------------------
# 8. Recommendation explanations use only grounded facts
# ---------------------------------------------------------------------------
def test_explanations_only_grounded_facts():
    profile_data = {
        "skills": ["Sewing", "Cutting"],
        "current_occupation": "Tailor",
        "interests": ["Garments"],
        "experience_years": 3.0,
    }
    response = client.post("/api/recommendations", json={"profile": profile_data})
    assert response.status_code == 200
    for r in response.json()["recommendations"]:
        explanation = r["explanation"]
        assert isinstance(explanation, str)
        assert len(explanation) > 10
        # No hallucinated buzzwords
        assert "rupees" not in explanation.lower()
        assert "salary" not in explanation.lower()
        assert "100%" not in explanation
        assert "guarantee" not in explanation.lower()
        # Must mention actual matched skill, sector, or training
        assert any(
            token.lower() in explanation.lower()
            for token in ["sewing", "cutting", "tailor", "apparel", "skills", "training", "garment"]
        )


# ---------------------------------------------------------------------------
# 9. Realistic Homemaker profile test (Palghar West)
# ---------------------------------------------------------------------------
def test_realistic_homemaker_integration_profile():
    """
    Realistic test case specified by SIH prompt:
    - Homemaker, 5 years experience, 12th pass, Palghar West
    - Wage-employment, Home-based preferred / can travel locally
    - Skills: Cooking, Tailoring
    - Interests: Cooking, Tailoring
    """
    response = client.post(
        "/api/recommendations", json={"profile": REALISTIC_HOMEMAKER_PROFILE}
    )
    assert response.status_code == 200
    data = response.json()
    recs = data["recommendations"]

    assert len(recs) == 3
    rec_ids = [r["role_id"] for r in recs]

    # Must contain Apparel & Textiles and Food Processing roles
    sectors = {r["sector"] for r in recs}
    assert "Apparel & Textiles" in sectors
    assert "Food Processing" in sectors

    # T-001 (Sewing Machine Operator) and F-001 (Food Products Packaging Technician)
    # both support wage-employment, which matches user's preference!
    assert "T-001" in rec_ids or "T-002" in rec_ids
    assert "F-001" in rec_ids

    for r in recs:
        assert r["match_score"] > 0.0
        assert r["match_percentage"] > 0
        assert len(r["pathway"]["qualification"]) > 0
        assert r["pathway"]["nsqf_level"] > 0
        assert len(r["explanation"]) > 0
        assert len(r["skills_to_develop"]) > 0


# ---------------------------------------------------------------------------
# 10. Direct UserProfile payload acceptance (bare dictionary)
# ---------------------------------------------------------------------------
def test_bare_profile_payload_accepted():
    response = client.post("/api/recommendations", json=REALISTIC_HOMEMAKER_PROFILE)
    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) == 3


# ---------------------------------------------------------------------------
# 11. Regression: Wage-employment profile + wage role
# ---------------------------------------------------------------------------
def test_wage_preference_with_wage_role():
    """Wage-employment preference on wage role must report direct alignment."""
    profile = {
        "skills": ["Sewing", "Stitching"],
        "employment_preference": "Wage-employment",
    }
    response = client.post("/api/recommendations", json={"profile": profile})
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    t001 = next((r for r in recs if r["role_id"] == "T-001"), None)
    assert t001 is not None, "T-001 should be recommended for sewing skills"
    assert "Directly supports" in t001["preference_alignment"]
    assert "Wage-employment" in t001["preference_alignment"]
    assert "Note: This role is primarily structured" not in t001["explanation"]


# ---------------------------------------------------------------------------
# 12. Regression: Self-employment profile + self-employment role
# ---------------------------------------------------------------------------
def test_self_employment_preference_with_self_role():
    """Self-employment preference on self role must report direct alignment."""
    profile = {
        "skills": ["Tailoring", "Garment Making"],
        "employment_preference": "Self-employment",
    }
    response = client.post("/api/recommendations", json={"profile": profile})
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    t002 = next((r for r in recs if r["role_id"] == "T-002"), None)
    assert t002 is not None, "T-002 should be recommended for tailoring skills"
    assert "Directly supports" in t002["preference_alignment"]
    assert "Self-employment" in t002["preference_alignment"]
    assert "Note: This role is primarily structured" not in t002["explanation"]


# ---------------------------------------------------------------------------
# 13. Regression: Wage preference + self-employment role NOT directly aligned
# ---------------------------------------------------------------------------
def test_wage_preference_with_self_employment_role_caveat():
    """
    When a self-employment role is recommended to a wage-seeking user due to strong skills,
    it must NOT report direct preference alignment and must include a clarifying caveat.
    """
    profile = {
        "skills": ["Tailoring", "Measurement Taking", "Garment Making"],
        "employment_preference": "Wage-employment",
    }
    response = client.post("/api/recommendations", json={"profile": profile})
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    t002 = next((r for r in recs if r["role_id"] == "T-002"), None)
    assert t002 is not None
    # Must NOT claim direct alignment with wage-employment
    assert "Directly supports Wage-employment" not in t002["preference_alignment"]
    assert "self-employment rather than wage-employment" in t002["preference_alignment"].lower()
    # Explanation must explicitly state that the role is structured for self-employment
    assert "primarily structured for self-employment rather than your preferred wage-employment" in t002["explanation"].lower()


# ---------------------------------------------------------------------------
# 14. Regression: Either preference receives flexible options without penalty
# ---------------------------------------------------------------------------
def test_either_preference_handled_flexibly():
    """Either preference should report flexible options and receive no penalty or mismatch caveat."""
    profile = {
        "skills": ["Tailoring"],
        "employment_preference": "Either",
    }
    response = client.post("/api/recommendations", json={"profile": profile})
    assert response.status_code == 200
    recs = response.json()["recommendations"]
    for r in recs:
        assert "flexible" in r["preference_alignment"].lower()
        assert "Note: This role is primarily structured" not in r["explanation"]

