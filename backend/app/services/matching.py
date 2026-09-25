"""
Deterministic skill-matching service.

Algorithm
---------
This is a simple, transparent, keyword-based matching function.
It is designed to be explainable to SIH judges in one minute.

For every role in the knowledge base, three sub-scores are computed:

1. skill_score (weight 0.60)
   Fraction of the role's ``required_skills`` that the user already possesses.
   Comparison is case-insensitive and strips punctuation.

2. interest_score (weight 0.20)
   Fraction of the user's ``interests`` that appear in the role's title
   or sector (case-insensitive substring match).

3. occupation_score (weight 0.20)
   Fraction of words in ``current_occupation`` that appear in the role's
   title or any required_skill (case-insensitive substring match).

   ``final_score = 0.60 * skill_score
                 + 0.20 * interest_score
                 + 0.20 * occupation_score``

Additionally, ``employment_preference`` is used as a hard filter boost:
if the user's preference matches any of the role's ``employment_type``
values, a small bonus of +0.05 is added (capped at 1.0).

``skill_gaps`` are computed as the role's ``gap_skills_covered`` entries
that the user does NOT already possess.

The function is entirely deterministic — same input always produces the
same ranked output.  No randomness, no LLM, no embeddings.

This service can be called independently of the conversation engine so that
the LLM layer added in the next phase can simply pass a ``UserProfile`` to
``match_profile()``.
"""
import re
import string
from dataclasses import dataclass, field

from app.models.profile import UserProfile
from app.models.role import LivelihoodRole
from app.services.knowledge_base import get_all_roles


# ---------------------------------------------------------------------------
# Score weights — declared as module-level constants for easy tuning.
# ---------------------------------------------------------------------------
WEIGHT_SKILLS = 0.60
WEIGHT_INTERESTS = 0.20
WEIGHT_OCCUPATION = 0.20
EMPLOYMENT_BONUS = 0.05  # added when employment_preference matches the role


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class MatchResult:
    """
    The matching result for a single role.

    Attributes
    ----------
    role_id : str
    title : str
    sector : str
    nsqf_level : float
    score : float
        Final weighted score in the range [0.0, 1.0].
    matched_skills : list[str]
        Required skills the user already has.
    skill_gaps : list[str]
        Skills covered by the training that the user does not yet have.
    employment_type : list[str]
        Employment modes supported by this role.
    """

    role_id: str
    title: str
    sector: str
    nsqf_level: float
    score: float
    matched_skills: list[str] = field(default_factory=list)
    skill_gaps: list[str] = field(default_factory=list)
    employment_type: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    return text.lower().translate(_PUNCT_TABLE).strip()


def _tokens(text: str) -> list[str]:
    """Return individual word tokens from a normalised string."""
    return _normalise(text).split()


def _skill_match(user_skill: str, role_skill: str) -> bool:
    """
    Return True if ``user_skill`` is considered equivalent to ``role_skill``.

    Currently uses a bidirectional substring check after normalisation.
    This catches common variations:
      - "Stitching" matches "Sewing" → False (no substring match)
      - "Tailoring" matches "Tailoring" → True
      - "Sewing machine" matches "Sewing" → True (substring)
    """
    u = _normalise(user_skill)
    r = _normalise(role_skill)
    return u == r or u in r or r in u


def _compute_skill_score(
    user_skills: list[str],
    required_skills: list[str],
) -> tuple[float, list[str]]:
    """
    Compute how many of the role's required skills the user already has.

    Returns
    -------
    score : float
        Fraction [0.0, 1.0].
    matched : list[str]
        Required skills that matched (using the role's canonical term).
    """
    if not required_skills:
        return 0.0, []

    matched = []
    for req in required_skills:
        for user in user_skills:
            if _skill_match(user, req):
                matched.append(req)
                break  # only count each required skill once

    return len(matched) / len(required_skills), matched


def _compute_interest_score(
    interests: list[str],
    role: LivelihoodRole,
) -> float:
    """
    Compute how many user interests appear in the role's title or sector.

    Returns
    -------
    float
        Fraction of user interests matched [0.0, 1.0].
        Returns 0.0 if user has no interests.
    """
    if not interests:
        return 0.0

    haystack = _normalise(f"{role.title} {role.sector}")
    matched = sum(
        1 for interest in interests if _normalise(interest) in haystack
    )
    return matched / len(interests)


def _compute_occupation_score(
    occupation: str | None,
    role: LivelihoodRole,
) -> float:
    """
    Compute overlap between the user's occupation words and the role's title
    or required skills.

    Returns
    -------
    float
        Fraction of occupation tokens matched [0.0, 1.0].
        Returns 0.0 if no occupation is provided.
    """
    if not occupation:
        return 0.0

    occ_tokens = _tokens(occupation)
    if not occ_tokens:
        return 0.0

    # Build a single haystack from the role title + required skills
    haystack = _normalise(
        role.title + " " + " ".join(role.required_skills)
    )

    matched = sum(1 for tok in occ_tokens if tok in haystack)
    return matched / len(occ_tokens)


def _compute_skill_gaps(
    user_skills: list[str],
    gap_skills_covered: list[str],
) -> list[str]:
    """
    Return skills covered by the training that the user does NOT yet have.
    These represent the actionable gaps the training would fill.
    """
    gaps = []
    for gap_skill in gap_skills_covered:
        already_has = any(_skill_match(u, gap_skill) for u in user_skills)
        if not already_has:
            gaps.append(gap_skill)
    return gaps


def _employment_bonus(preference: str | None, role: LivelihoodRole) -> float:
    """Return EMPLOYMENT_BONUS if the role supports the user's preference."""
    if not preference:
        return 0.0
    pref = _normalise(preference)
    for emp in role.employment_type:
        if pref in _normalise(emp) or _normalise(emp) in pref:
            return EMPLOYMENT_BONUS
    return 0.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def match_profile(
    profile: UserProfile,
    roles: list[LivelihoodRole] | None = None,
) -> list[MatchResult]:
    """
    Match a user profile against the knowledge base and return scored results.

    Parameters
    ----------
    profile : UserProfile
        The structured livelihood profile from the conversation engine.
    roles : list[LivelihoodRole] | None
        Roles to match against.  Defaults to the full knowledge base.
        Pass a custom list in tests.

    Returns
    -------
    list[MatchResult]
        All roles scored and sorted by ``score`` descending.
        Roles with score 0.0 are included so the caller can decide
        on a minimum threshold.
    """
    if roles is None:
        roles = get_all_roles()

    results: list[MatchResult] = []

    for role in roles:
        skill_score, matched_skills = _compute_skill_score(
            profile.skills, role.required_skills
        )
        interest_score = _compute_interest_score(profile.interests, role)
        occupation_score = _compute_occupation_score(
            profile.current_occupation, role
        )
        bonus = _employment_bonus(profile.employment_preference, role)

        raw_score = (
            WEIGHT_SKILLS * skill_score
            + WEIGHT_INTERESTS * interest_score
            + WEIGHT_OCCUPATION * occupation_score
            + bonus
        )
        final_score = round(min(raw_score, 1.0), 4)

        skill_gaps = _compute_skill_gaps(profile.skills, role.gap_skills_covered)

        results.append(
            MatchResult(
                role_id=role.id,
                title=role.title,
                sector=role.sector,
                nsqf_level=role.nsqf_level,
                score=final_score,
                matched_skills=matched_skills,
                skill_gaps=skill_gaps,
                employment_type=role.employment_type,
            )
        )

    # Sort by score descending; use role_id as a stable tiebreaker
    results.sort(key=lambda r: (-r.score, r.role_id))
    return results
