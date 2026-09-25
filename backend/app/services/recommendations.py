"""
SkillFlow recommendation and pathway service.

Transforms a completed user livelihood profile into explainable,
deterministic NSQF role recommendations, skill-gap analysis,
and accredited training roadmaps.
"""
import logging
from app.models.profile import UserProfile
from app.models.recommendation import (
    RecommendationsResponse,
    RoleRecommendation,
    TrainingPathway,
)
from app.services.knowledge_base import get_all_roles, get_role_by_id
from app.services.matching import _skill_match, match_profile

logger = logging.getLogger(__name__)


def _evaluate_preference_alignment(
    preference: str | None,
    role_title: str,
    role_employment_type: list[str],
) -> tuple[str, str | None]:
    """
    Evaluates semantic alignment between user's employment preference and role employment type.

    Returns:
    --------
    pref_align : str
        Human-readable alignment statement for the recommendation card.
    caveat : str | None
        Factual caveat to include in explanation if there is a mismatch.
    """
    if not preference or not preference.strip():
        return "Supports multi-modal livelihood pathways.", None

    p_clean = preference.strip().lower()
    role_types_clean = [e.lower() for e in role_employment_type]
    role_types_display = ", ".join(role_employment_type)

    # 1. Flexible / Either preference
    if "either" in p_clean or "both" in p_clean or "flexible" in p_clean or "any" in p_clean:
        return f"Supports {role_types_display} as flexible options.", None

    wants_wage = any(k in p_clean for k in ("wage", "job", "salaried", "service"))
    wants_self = any(k in p_clean for k in ("self", "business", "own"))

    role_supports_wage = "wage-employment" in role_types_clean and "self-employed" not in role_title.lower()
    role_supports_self = "self-employment" in role_types_clean

    if wants_wage:
        if role_supports_wage:
            return f"Directly supports {preference} as preferred.", None
        else:
            pref_align = f"Primarily structured for {role_types_display} rather than wage-employment."
            caveat = (
                f"Note: This role is primarily structured for {role_types_display} rather than "
                f"your preferred wage-employment, but is recommended due to strong skill and interest alignment."
            )
            return pref_align, caveat

    if wants_self:
        if role_supports_self:
            return f"Directly supports {preference} as preferred.", None
        else:
            pref_align = f"Primarily structured for {role_types_display} rather than self-employment."
            caveat = (
                f"Note: This role is primarily structured for {role_types_display} rather than "
                f"your preferred self-employment, but is recommended due to strong skill and interest alignment."
            )
            return pref_align, caveat

    # Fallback for any other custom preference string:
    if any(p_clean in e or e in p_clean for e in role_types_clean):
        return f"Directly supports {preference} as preferred.", None
    else:
        pref_align = f"Offers {role_types_display} pathways."
        caveat = (
            f"Note: This role offers {role_types_display} pathways differing from your stated "
            f"preference for {preference}, but aligns with your vocational skills."
        )
        return pref_align, caveat


def _build_grounded_explanation(
    role_title: str,
    sector: str,
    matched_skills: list[str],
    matched_interests: list[str],
    experience_years: float | None,
    current_occupation: str | None,
    skill_gaps: list[str],
    preference_caveat: str | None = None,
) -> str:
    """
    Construct a factual, grounded explanation strictly using verified profile
    fields and knowledge-base role data. Never invents qualifications,
    salaries, government guarantees, or external entities.
    """
    sentences = []

    # 1. Skills / Occupation alignment
    if matched_skills:
        skill_str = ", ".join(matched_skills[:2])
        if current_occupation and current_occupation.lower() not in {"none", "homemaker", "unemployed", "student"}:
            sentences.append(
                f"Your practical experience in {current_occupation} and skills in {skill_str} align directly with this pathway."
            )
        else:
            sentences.append(
                f"Your existing skills in {skill_str} provide a strong foundation for the {role_title} role."
            )
    elif current_occupation and current_occupation.lower() not in {"none", "homemaker", "unemployed", "student"}:
        sentences.append(
            f"Your work background in {current_occupation} connects with requirements in the {sector} sector."
        )

    # 2. Interests alignment
    if matched_interests:
        int_str = ", ".join(matched_interests[:2])
        sentences.append(
            f"Your stated interest in {int_str} aligns well with this {sector} livelihood track."
        )

    # 3. Experience alignment
    if experience_years and experience_years > 0:
        exp_val = int(experience_years) if experience_years.is_integer() else experience_years
        sentences.append(
            f"Your {exp_val} years of practical experience will help you accelerate through the curriculum."
        )

    # 4. Actionable skill gaps / training advice
    if skill_gaps:
        gaps_str = ", ".join(skill_gaps[:2])
        sentences.append(
            f"You may benefit from recommended training to develop {gaps_str}."
        )
    else:
        sentences.append(
            "You already demonstrate strong baseline competence across the core requirements."
        )

    # 5. Employment preference caveat (if recommended despite mismatch)
    if preference_caveat:
        sentences.append(preference_caveat)

    if not sentences:
        return f"This {sector} pathway provides accredited skilling aligned with entry-level NSQF standards."

    return " ".join(sentences)


def generate_recommendations(
    profile: UserProfile,
    max_recommendations: int = 3,
) -> RecommendationsResponse:
    """
    Generate at most `max_recommendations` (default 3) explainable NSQF
    livelihood recommendations for a completed profile.

    Parameters
    ----------
    profile : UserProfile
        The verified, completed user profile from the interview session.
    max_recommendations : int
        Maximum number of roles to return (capped at 3).

    Returns
    -------
    RecommendationsResponse
        Top recommendations containing role metadata, match percentage,
        grounded explanation, skill gaps, and verified training pathway.
    """
    all_roles = get_all_roles()
    scored_results = match_profile(profile, roles=all_roles)

    # Filter to roles that have meaningful relevance (score > 0.0)
    positive_matches = [r for r in scored_results if r.score > 0.0]

    # If the user profile is empty or has zero matching signals, handle safely:
    # Return empty recommendations list so caller knows no meaningful match was made.
    if not positive_matches:
        logger.info("No matching roles found with score > 0.0 for given profile.")
        return RecommendationsResponse(
            total_evaluated=len(all_roles),
            total_recommended=0,
            recommendations=[],
        )

    top_results = positive_matches[:max_recommendations]
    recommendations: list[RoleRecommendation] = []

    for r in top_results:
        role = get_role_by_id(r.role_id)
        if not role:
            continue

        # Distinguish skills user already has vs skills to develop
        skills_already_have = [
            u for u in profile.skills
            if any(_skill_match(u, req) for req in role.required_skills)
        ]
        # If user skills didn't match directly by user term, include role's matched term
        if not skills_already_have and r.matched_skills:
            skills_already_have = list(r.matched_skills)

        skills_to_develop = list(r.skill_gaps)

        # Experience alignment description
        if profile.experience_years and profile.experience_years > 0:
            exp_val = int(profile.experience_years) if profile.experience_years.is_integer() else profile.experience_years
            exp_align = f"{exp_val} years of practical experience provides a strong foundation for vocational progression."
        else:
            exp_align = "Entry-level accessible role; no prior formal work experience required."

        # Preference alignment description & caveat
        pref_align, pref_caveat = _evaluate_preference_alignment(
            preference=profile.employment_preference,
            role_title=role.title,
            role_employment_type=role.employment_type,
        )

        # Grounded factual explanation
        explanation = _build_grounded_explanation(
            role_title=role.title,
            sector=role.sector,
            matched_skills=r.matched_skills,
            matched_interests=r.matched_interests,
            experience_years=profile.experience_years,
            current_occupation=profile.current_occupation,
            skill_gaps=skills_to_develop,
            preference_caveat=pref_caveat,
        )

        # Training pathway grounded in knowledge base
        duration_clean = role.duration
        if not duration_clean or "not specified" in duration_clean.lower():
            duration_clean = "Information not available in current knowledge base (Standard NSQF short-term format)"

        eligibility_clean = role.eligibility or "Information not available in current knowledge base"
        qualification_clean = role.qualification or "Information not available in current knowledge base"

        pathway = TrainingPathway(
            qp_code=role.qp_code,
            nsqf_level=role.nsqf_level,
            qualification=qualification_clean,
            duration=duration_clean,
            eligibility=eligibility_clean,
            organization=role.source.organization,
            document=role.source.document,
            url=role.source.url,
        )

        match_pct = int(round(r.score * 100))

        rec = RoleRecommendation(
            role_id=role.id,
            role_title=role.title,
            sector=role.sector,
            nsqf_level=role.nsqf_level,
            match_score=r.score,
            match_percentage=match_pct,
            matched_skills=r.matched_skills,
            matched_interests=r.matched_interests,
            skills_already_have=skills_already_have,
            skills_to_develop=skills_to_develop,
            skill_gaps=skills_to_develop,
            experience_alignment=exp_align,
            preference_alignment=pref_align,
            explanation=explanation,
            pathway=pathway,
        )
        recommendations.append(rec)

    return RecommendationsResponse(
        total_evaluated=len(all_roles),
        total_recommended=len(recommendations),
        recommendations=recommendations,
    )
