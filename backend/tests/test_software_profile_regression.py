"""
Regression test suite for Software / Web Developer profile extraction and recommendations.

Tests:
1. Exact 5-turn conversation accumulation and merge preservation.
2. Current activity vs current occupation vs interests vs specialization vs skills.
3. Matching and ranking of IT/Software roles (Web Developer D-004, Software Developer D-005, Database Administrator D-006).
4. Strict filtering out of irrelevant Agriculture (A-001, A-003) and Beauty (B-001) roles.
5. Employment preference alone not manufacturing irrelevant recommendations.
6. Existing agriculture and tailoring livelihood profiles continue to match correctly.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.conversation import ProfileUpdate
from app.models.profile import UserProfile
from app.services.conversation import _merge_profile
from app.services.matching import match_profile
from app.services.recommendations import generate_recommendations

client = TestClient(app)


# ---------------------------------------------------------------------------
# 1. Profile merging across 5 turns
# ---------------------------------------------------------------------------
def test_five_turn_profile_merge_preservation():
    """
    TURN 1: "I am building software projects."
    TURN 2: "I am interested in web development."
    TURN 3: "I prefer backend development."
    TURN 4: "I know Python, Java and MySQL."
    TURN 5: "I want wage employment."

    The resulting profile MUST preserve all 5 turns of information.
    """
    profile = {}

    # Turn 1
    t1 = ProfileUpdate(current_activity="Software / Project Development")
    profile = _merge_profile(profile, t1)
    assert profile["current_activity"] == "Software / Project Development"

    # Turn 2
    t2 = ProfileUpdate(interests=["Web Development"])
    profile = _merge_profile(profile, t2)
    assert profile["current_activity"] == "Software / Project Development"
    assert "Web Development" in profile["interests"]

    # Turn 3
    t3 = ProfileUpdate(preferred_specialization="Backend Development")
    profile = _merge_profile(profile, t3)
    assert profile["current_activity"] == "Software / Project Development"
    assert "Web Development" in profile["interests"]
    assert profile["preferred_specialization"] == "Backend Development"

    # Turn 4
    t4 = ProfileUpdate(skills=["Python", "Java", "MySQL"])
    profile = _merge_profile(profile, t4)
    assert profile["current_activity"] == "Software / Project Development"
    assert "Web Development" in profile["interests"]
    assert profile["preferred_specialization"] == "Backend Development"
    assert profile["skills"] == ["Python", "Java", "MySQL"]

    # Turn 5
    t5 = ProfileUpdate(employment_preference="Wage-employment")
    profile = _merge_profile(profile, t5)
    assert profile["current_activity"] == "Software / Project Development"
    assert "Web Development" in profile["interests"]
    assert profile["preferred_specialization"] == "Backend Development"
    assert profile["skills"] == ["Python", "Java", "MySQL"]
    assert profile["employment_preference"] == "Wage-employment"


# ---------------------------------------------------------------------------
# 2. Multi-turn skill and interest accumulation (no overwrite)
# ---------------------------------------------------------------------------
def test_skills_accumulate_across_turns():
    """Mentioning a new skill must NOT wipe earlier skills."""
    profile = {}
    profile = _merge_profile(profile, ProfileUpdate(skills=["Python"]))
    profile = _merge_profile(profile, ProfileUpdate(skills=["Java"]))
    profile = _merge_profile(profile, ProfileUpdate(skills=["MySQL"]))
    assert set(profile["skills"]) == {"Python", "Java", "MySQL"}


def test_explicit_clarification_replaces_generic_placeholder():
    """If user earlier had generic 'Open to any' or 'Project Building', explicit interest cleans it up."""
    profile = {"interests": ["Open to any"]}
    profile = _merge_profile(profile, ProfileUpdate(interests=["Web Development"]))
    assert "Web Development" in profile["interests"]
    assert "Open to any" not in profile["interests"]


# ---------------------------------------------------------------------------
# 3. Software/Web recommendation relevance
# ---------------------------------------------------------------------------
def test_software_profile_recommends_software_roles_and_excludes_agriculture():
    """
    Given the regression profile:
      current_activity: "Software / Project Development"
      interests: ["Web Development"]
      preferred_specialization: "Backend Development"
      skills: ["Python", "Java", "MySQL"]
      employment_preference: "Wage-employment"

    Recommendations MUST:
    - Include Web Developer, Software Developer, or Database Administrator at the top.
    - Strictly exclude Paddy Cultivator, Pulses Cultivator, and Assistant Beauty Therapist.
    - Ground explanation in Python, Java, MySQL, Web/Backend without fabricating agriculture links.
    """
    user_prof = UserProfile(
        current_activity="Software / Project Development",
        interests=["Web Development"],
        preferred_specialization="Backend Development",
        skills=["Python", "Java", "MySQL"],
        employment_preference="Wage-employment",
    )

    recs_resp = generate_recommendations(user_prof)
    recs = recs_resp.recommendations

    assert len(recs) > 0
    rec_ids = [r.role_id for r in recs]

    # Software / Web / Database roles must be present
    assert any(rid in {"D-004", "D-005", "D-006"} for rid in rec_ids), \
        f"Expected IT roles in {rec_ids}"

    # Top recommendation must be an IT-ITeS role
    assert recs[0].role_id in {"D-004", "D-005", "D-006"}
    assert recs[0].sector == "Digital & Entrepreneurship"

    # Agriculture and Beauty must NOT appear
    assert "A-001" not in rec_ids, "Paddy Cultivator must NOT be recommended"
    assert "A-003" not in rec_ids, "Pulses Cultivator must NOT be recommended"
    assert "B-001" not in rec_ids, "Assistant Beauty Therapist must NOT be recommended"

    # Verify grounded explanations
    for r in recs:
        assert "Agriculture" not in r.explanation
        assert "Project building connects with requirements in the Agriculture" not in r.explanation

    # Specific check for Web Developer (D-004)
    web_dev = next((r for r in recs if r.role_id == "D-004"), None)
    if web_dev:
        # User only knows Python, Java, MySQL. Role requires Database Basics, HTML/CSS, JavaScript, Web Dev, Frontend Dev.
        # Only MySQL matches Database Basics. User does NOT know HTML/CSS or JavaScript.
        assert "HTML/CSS" not in web_dev.skills_already_have
        assert "JavaScript" not in web_dev.skills_already_have
        assert "Web Development" not in web_dev.skills_already_have
        assert web_dev.skills_already_have == ["MySQL"]
        # Explanation must not claim the user has HTML/CSS or JavaScript
        assert "skills in HTML/CSS" not in web_dev.explanation
        assert "skills in JavaScript" not in web_dev.explanation
        assert "skills in Web Development" not in web_dev.explanation
        assert "skills in MySQL" in web_dev.explanation


# ---------------------------------------------------------------------------
# 4. Employment preference alone does not manufacture recommendations
# ---------------------------------------------------------------------------
def test_employment_preference_alone_does_not_create_recommendations():
    """A profile with ONLY employment_preference and no skills/interests must return 0 recommendations."""
    user_prof = UserProfile(employment_preference="Wage-employment")
    recs_resp = generate_recommendations(user_prof)
    assert recs_resp.total_recommended == 0
    assert len(recs_resp.recommendations) == 0


# ---------------------------------------------------------------------------
# 5. Matching priority: Preferred specialization takes precedence
# ---------------------------------------------------------------------------
def test_preferred_specialization_ranks_appropriate_role_highest():
    """
    A user with Backend Development specialization should rank Software/Web Developer
    above generic Data Entry or unrelated roles.
    """
    user_prof = UserProfile(
        skills=["Python", "MySQL"],
        interests=["Software"],
        preferred_specialization="Backend Development",
    )
    results = match_profile(user_prof)
    top_role_ids = [r.role_id for r in results[:3]]
    assert "D-005" in top_role_ids or "D-004" in top_role_ids
    assert results[0].score >= 0.50


# ---------------------------------------------------------------------------
# 6. Existing livelihood profiles remain intact (Apparel / Agriculture)
# ---------------------------------------------------------------------------
def test_existing_tailoring_profile_still_ranks_tailoring():
    user_prof = UserProfile(
        skills=["Sewing", "Stitching", "Cutting"],
        current_occupation="Tailoring",
        interests=["Apparel & Textiles"],
        employment_preference="Self-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) > 0
    assert recs[0].role_id in {"T-001", "T-002", "T-003"}


def test_existing_farming_profile_still_ranks_agriculture():
    user_prof = UserProfile(
        skills=["Crop Growing", "Harvesting"],
        current_occupation="Farming",
        interests=["Agriculture & Allied Activities"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) > 0
    assert recs[0].role_id in {"A-001", "A-002", "A-003"}


# ---------------------------------------------------------------------------
# 7. Non-software domain regressions: Food Processing & Beauty / Wellness
# ---------------------------------------------------------------------------
def test_food_processing_profile_with_specialization_ranks_food():
    """Verify that a Food Processing profile correctly ranks Food Packaging Technician."""
    user_prof = UserProfile(
        current_activity="Cooking and kitchen work",
        interests=["Food Processing"],
        preferred_specialization="Packaging",
        skills=["Food Handling", "Hygiene Practices"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) > 0
    assert recs[0].role_id == "F-001"
    assert recs[0].sector == "Food Processing"
    assert "Food Handling" in recs[0].skills_already_have
    assert "Packaging" in recs[0].explanation


def test_beauty_wellness_profile_with_specialization_ranks_beauty():
    """Verify that a Beauty & Wellness profile correctly ranks Hair Dresser or Beauty Therapist."""
    user_prof = UserProfile(
        current_activity="Assisting in parlour",
        interests=["Beauty and Wellness"],
        preferred_specialization="Hair styling",
        skills=["Hair Styling", "Skin Care"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) > 0
    assert recs[0].role_id in {"B-001", "B-002"}
    assert recs[0].sector == "Beauty & Wellness"
    assert "Hair Styling" in recs[0].skills_already_have
    assert "Hair styling" in recs[0].explanation


# ---------------------------------------------------------------------------
# 8. Holistic matching & non-padding: Tutor profile regression
# ---------------------------------------------------------------------------
def test_tutor_teaching_profile_with_no_pathway_returns_zero_recommendations():
    """
    Profile with Tutor occupation, Teaching interest, and domestic Cooking skill.
    Since the current NSQF catalog has no teaching/tutoring pathway, and domestic cooking
    does not qualify for industrial packaging or agriculture, the system MUST return 0 recommendations.
    Must NEVER pad with Paddy Cultivator (5%) or Organic Grower (5%).
    """
    user_prof = UserProfile(
        current_occupation="Tutor",
        interests=["Teaching"],
        experience_years=2.5,
        education="12th pass",
        location="Mumbai, Malad",
        employment_preference="Either",
        mobility_constraint="Can travel locally",
        skills=["Cooking"],
    )

    recs_resp = generate_recommendations(user_prof)
    assert recs_resp.total_recommended == 0
    assert len(recs_resp.recommendations) == 0

    # Verify that match_profile does not give 5% bonus to unrelated roles
    from app.services.matching import match_profile
    matches = match_profile(user_prof)
    for m in matches:
        assert m.score < 0.20, f"Role {m.title} unexpectedly scored {m.score} for unrelated Tutor profile"
        if m.role_id in {"A-001", "A-002", "A-003"}:
            assert m.score == 0.0, f"Agriculture role {m.title} must have 0.0 score for Tutor profile"


def test_single_role_match_returns_exactly_one_recommendation():
    """
    When only 1 role in the knowledge base genuinely matches the profile,
    return exactly 1 recommendation without padding.
    """
    user_prof = UserProfile(
        current_occupation="Plumber",
        skills=["Pipe Fitting", "Plumbing"],
        interests=["Plumbing Repair"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) == 1
    assert recs[0].role_id == "C-004"
    assert recs[0].role_title == "Plumber (General)"


def test_two_roles_match_returns_exactly_two_recommendations():
    """
    When exactly 2 roles genuinely match, return exactly 2 recommendations without padding.
    """
    user_prof = UserProfile(
        current_occupation="Beautician",
        skills=["Hair Styling", "Skin Care"],
        interests=["Beauty and Wellness"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) == 2
    rec_ids = {r.role_id for r in recs}
    assert rec_ids == {"B-001", "B-002"}


def test_unmatched_interest_with_strong_skills_returns_alternative_pathway():
    """
    Test A: If the user's stated career interest has no corresponding role in the catalog (e.g. 'Robotics'),
    but they have strong, recorded practical skills (e.g. Sewing, Machine Operation, Stitching),
    SkillFlow should present the genuine skill match labeled as an 'alternative' pathway,
    without claiming their interest matched the role.
    """
    user_prof = UserProfile(
        interests=["Robotics"],
        skills=["Sewing", "Machine Operation", "Stitching"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) > 0
    # Must be marked as alternative pathway
    assert recs[0].match_type == "alternative"
    assert recs[0].role_id == "T-001"  # Sewing Machine Operator
    assert "Alternative pathway:" in recs[0].explanation
    assert "recorded skills" in recs[0].explanation
    assert "verified skills" not in recs[0].explanation
    assert "may provide a potential alternative pathway" in recs[0].explanation
    assert "Robotics" not in recs[0].explanation
    # Skills already have must reflect their recorded tailoring skills
    assert any(s in recs[0].skills_already_have for s in ["Sewing", "Machine Operation", "Stitching"])


def test_unmatched_interest_with_single_incidental_skill_returns_zero_unrelated_roles():
    """
    Test B: An out-of-catalog interest with only ONE incidental skill must NOT produce
    unrelated alternative recommendations.
    For instance, someone interested in Astronomy with only 'Typing' as an incidental skill
    should not receive Domestic Data Entry Operator as an alternative pathway.
    """
    user_prof = UserProfile(
        interests=["Astronomy"],
        skills=["Typing"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) == 0


def test_either_preference_with_zero_core_evidence_returns_zero_recommendations():
    """
    Test C: A profile with 'Either' employment preference but zero core evidence
    must return zero recommendations, and matching scores must all be 0.0.
    'Either' indicates flexibility, never a positive relevance generator.
    """
    user_prof = UserProfile(
        education="12th pass",
        location="Malad, Mumbai",
        employment_preference="Either",
        mobility_constraint="Can travel locally",
    )
    recs_resp = generate_recommendations(user_prof)
    assert recs_resp.total_recommended == 0
    assert len(recs_resp.recommendations) == 0

    from app.services.matching import match_profile
    matches = match_profile(user_prof)
    for m in matches:
        assert m.score == 0.0, f"Expected 0.0 score for role {m.title}, got {m.score}"


def test_formal_occupation_experience_does_not_transfer_to_unrelated_role():
    """
    Test D: Years of experience in a formal occupation (e.g. 5 years as an Accountant)
    must NOT transfer to an unrelated role that only shares skill overlap (e.g. Domestic Data Entry Operator).
    The role's experience alignment and explanation must not treat accounting experience as data entry experience.
    """
    user_prof = UserProfile(
        current_occupation="Accountant",
        experience_years=5.0,
        skills=["Data Entry", "Computer Operation"],
        interests=["Data Processing"],
        employment_preference="Wage-employment",
    )
    recs = generate_recommendations(user_prof).recommendations
    assert len(recs) > 0
    rec = recs[0]
    # Occupation 'Accountant' does not match D-001 Domestic Data Entry Operator
    # Experience from Accountant must not be treated as practical experience in Data Entry Operator
    assert "Your 5 years of practical experience in this field" not in rec.explanation
    assert "5 years of practical experience provides a strong foundation" not in rec.experience_alignment
    assert "no prior formal work experience in this sector required" in rec.experience_alignment


