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
    skills_already_have: list[str],
    matched_interests: list[str],
    matched_specialization: list[str] | None = None,
    experience_years: float | None = None,
    current_occupation: str | None = None,
    current_activity: str | None = None,
    skill_gaps: list[str] | None = None,
    preference_caveat: str | None = None,
) -> str:
    """
    Construct a factual, grounded explanation strictly using verified profile
    fields and knowledge-base role data. Never invents qualifications,
    salaries, government guarantees, or external entities.
    """
    sentences = []

    # 1. Preferred specialization alignment (Highest priority)
    if matched_specialization:
        spec_str = ", ".join(matched_specialization[:2])
        sentences.append(
            f"Your focus on {spec_str} aligns directly with the core objectives of the {role_title} pathway."
        )

    # 2. Skills alignment (uses confirmed user skills that matched this role)
def _build_grounded_explanation(
    role_title: str,
    sector: str,
    skills_already_have: list[str],
    matched_interests: list[str],
    matched_specialization: list[str] | None,
    experience_years: float | None,
    current_occupation: str | None,
    current_activity: str | None,
    occupation_matched: bool = False,
    skill_gaps: list[str] | None = None,
    preference_caveat: str | None = None,
    match_type: str = "primary",
) -> str:
    """
    Construct a factual, grounded explanation strictly using reported profile
    fields and knowledge-base role data. Never invents qualifications,
    salaries, government guarantees, or external entities.
    Never claims an occupation connects with a role unless occupation_matched is True.
    """
    sentences = []

    if match_type == "alternative":
        if skills_already_have:
            skill_str = ", ".join(skills_already_have[:2])
            sentences.append(
                f"Alternative pathway: Your recorded skills in {skill_str} align with this vocational pathway in the {sector} sector and may provide a potential alternative pathway."
            )
        else:
            sentences.append(
                f"Alternative pathway: This vocational pathway in the {sector} sector may provide a potential alternative option based on your reported background."
            )
    else:
        # 1. Preferred specialization alignment (Highest priority)
        if matched_specialization:
            spec_str = ", ".join(matched_specialization[:2])
            sentences.append(
                f"Your focus on {spec_str} aligns directly with the core objectives of the {role_title} pathway."
            )

        # 2. Occupation & Skills alignment
        # ONLY cite current occupation if it actually matched this role!
        if occupation_matched and current_occupation and current_occupation.lower() not in {"none", "homemaker", "unemployed", "student", "fresher"}:
            if skills_already_have:
                skill_str = ", ".join(skills_already_have[:2])
                sentences.append(
                    f"Your practical experience in {current_occupation} and recorded skills in {skill_str} provide a strong foundation for this role."
                )
            else:
                sentences.append(
                    f"Your practical experience in {current_occupation} provides a strong foundation for this role."
                )
        elif skills_already_have:
            skill_str = ", ".join(skills_already_have[:2])
            sentences.append(
                f"Your recorded skills in {skill_str} provide a strong foundation for the {role_title} role."
            )

        # 3. Interests alignment
        if matched_interests:
            int_str = ", ".join(matched_interests[:2])
            sentences.append(
                f"Matches your stated interest in {int_str} within the {sector} sector."
            )

    # 4. Relevant experience alignment (ONLY if occupation matched, or informal/domestic background with matched skills!)
    occ_name = (current_occupation or "").lower().strip()
    is_informal = occ_name in {"", "none", "homemaker", "student", "unemployed", "fresher"}
    has_relevant_exp = (
        experience_years
        and experience_years > 0
        and (occupation_matched or (is_informal and skills_already_have))
    )
    if has_relevant_exp:
        exp_val = int(experience_years) if experience_years.is_integer() else experience_years
        sentences.append(
            f"Your {exp_val} years of practical experience in this field will help you accelerate through the curriculum."
        )

    # 5. Actionable skill gaps / training advice
    if skill_gaps:
        gaps_str = ", ".join(skill_gaps[:2])
        sentences.append(
            f"You may benefit from recommended training to develop {gaps_str}."
        )
    else:
        sentences.append(
            "You already demonstrate strong baseline competence across the core requirements."
        )

    # 6. Employment preference caveat (if recommended despite mismatch)
    if preference_caveat:
        sentences.append(preference_caveat)

    if not sentences:
        return f"This {sector} pathway provides accredited skilling aligned with entry-level NSQF standards."

    return " ".join(sentences)


MIN_RECOMMENDATION_SCORE = 0.10


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

    has_stated_intent = bool(
        (profile.interests and any(i.strip() for i in profile.interests))
        or (profile.preferred_specialization and profile.preferred_specialization.strip())
    )

    # Require genuine profile-role relevance.
    # A role is ONLY recommended if there is genuine semantic evidence connecting
    # the user's profile to the role, with a score of at least MIN_RECOMMENDATION_SCORE.
    def _is_meaningful_match(r) -> bool:
        if r.score < MIN_RECOMMENDATION_SCORE:
            return False

        has_skills = bool(r.matched_skills and len(r.matched_skills) > 0)
        has_interests = bool(r.matched_interests and len(r.matched_interests) > 0)
        has_spec = bool(getattr(r, "matched_specialization", None) and len(r.matched_specialization) > 0)
        has_occ = getattr(r, "occupation_matched", False)

        if not (has_skills or has_interests or has_spec or has_occ):
            return False

        # Holistic intent alignment: If the user expressed concrete interests or specialization,
        # roles matching them are primary pathways.
        # Roles from other domains are only eligible as alternative pathways if the user possesses
        # at least 2 distinct recorded skills that genuinely match the role requirements.
        if has_stated_intent:
            aligned_with_intent = has_interests or has_spec or has_occ
            if not aligned_with_intent:
                # Strong evidence required for alternative pathway:
                # An incidental single skill is NEVER enough to recommend an alternative pathway.
                role = get_role_by_id(r.role_id)
                if not role:
                    return False
                user_matching_skills = [
                    u for u in profile.skills
                    if any(_skill_match(u, req) for req in role.required_skills)
                ]
                if len(user_matching_skills) < 2 or len(r.matched_skills) < 2:
                    return False

        return True

    relevant_matches = [r for r in scored_results if _is_meaningful_match(r)]

    # If the user profile has zero meaningful matches, return empty list
    if not relevant_matches:
        logger.info("No meaningful matching roles found for given profile.")
        return RecommendationsResponse(
            total_evaluated=len(all_roles),
            total_recommended=0,
            recommendations=[],
        )

    # Do not force 3 recommendations: return UP TO 3 genuinely relevant roles.
    # If only 1 is relevant, return 1. If 2 are relevant, return 2.
    top_results = relevant_matches[:max_recommendations]
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

        skills_to_develop = list(r.skill_gaps)

        # Experience alignment description:
        # A user's years of experience in a formal occupation must NOT transfer to an unrelated occupation!
        occ_name = (profile.current_occupation or "").lower().strip()
        is_informal = occ_name in {"", "none", "homemaker", "student", "unemployed", "fresher"}
        has_relevant_exp = (
            profile.experience_years
            and profile.experience_years > 0
            and (getattr(r, "occupation_matched", False) or (is_informal and skills_already_have))
        )

        if has_relevant_exp:
            exp_val = int(profile.experience_years) if profile.experience_years.is_integer() else profile.experience_years
            exp_align = f"{exp_val} years of practical experience provides a strong foundation for vocational progression."
        else:
            exp_align = "Entry-level accessible role; no prior formal work experience in this sector required."

        # Preference alignment description & caveat
        pref_align, pref_caveat = _evaluate_preference_alignment(
            preference=profile.employment_preference,
            role_title=role.title,
            role_employment_type=role.employment_type,
        )

        # Determine pathway type:
        aligned_with_intent = bool(
            r.matched_interests
            or getattr(r, "matched_specialization", None)
            or getattr(r, "occupation_matched", False)
        )
        match_type = "primary" if (aligned_with_intent or not has_stated_intent) else "alternative"

        # Grounded factual explanation
        explanation = _build_grounded_explanation(
            role_title=role.title,
            sector=role.sector,
            skills_already_have=skills_already_have,
            matched_interests=r.matched_interests,
            matched_specialization=getattr(r, "matched_specialization", None),
            experience_years=profile.experience_years,
            current_occupation=profile.current_occupation,
            current_activity=getattr(profile, "current_activity", None),
            occupation_matched=getattr(r, "occupation_matched", False),
            skill_gaps=skills_to_develop,
            preference_caveat=pref_caveat,
            match_type=match_type,
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
            matched_specialization=getattr(r, "matched_specialization", []),
            skills_already_have=skills_already_have,
            skills_to_develop=skills_to_develop,
            skill_gaps=skills_to_develop,
            match_type=match_type,
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
