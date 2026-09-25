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
    matched_interests : list[str]
        Interests of the user that align with this role or sector.
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
    matched_interests: list[str] = field(default_factory=list)
    skill_gaps: list[str] = field(default_factory=list)
    employment_type: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers & normalisation
# ---------------------------------------------------------------------------
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)

# Curated, deterministic skill and domain synonym clusters
# Normalises common variations across English, Hindi, and vernacular terms
# without arbitrary or invented synonyms.
SKILL_SYNONYMS: dict[str, set[str]] = {
    # Apparel & Textiles
    "sewing": {"sewing", "stitching", "silayi", "silai", "tailoring", "garment making", "sewing machine", "cutting", "सिलाई", "दर्जी", "कपड़े", "कटाई"},
    "stitching": {"sewing", "stitching", "silayi", "silai", "tailoring", "garment making", "sewing machine", "cutting", "सिलाई"},
    "silayi": {"sewing", "stitching", "silayi", "silai", "tailoring", "garment making", "सिलाई"},
    "silai": {"sewing", "stitching", "silayi", "silai", "tailoring", "garment making", "सिलाई"},
    "tailoring": {"sewing", "stitching", "silayi", "silai", "tailoring", "garment making", "alteration", "pattern making", "सिलाई", "दर्जी"},
    "garment making": {"sewing", "stitching", "tailoring", "garment making", "apparel", "सिलाई", "कपड़े"},
    "weaving": {"weaving", "handloom", "bunai", "weaver", "loom operation", "बुनाई", "हथकरघा"},
    "handloom": {"weaving", "handloom", "bunai", "weaver", "हथकरघा", "बुनाई"},
    "सिलाई": {"sewing", "stitching", "silayi", "silai", "tailoring", "garment making", "sewing machine", "cutting", "सिलाई", "दर्जी", "alteration", "pattern making", "fabric handling"},
    "दर्जी": {"sewing", "stitching", "tailoring", "garment making", "सिलाई", "दर्जी"},
    "बुनाई": {"weaving", "handloom", "bunai", "weaver", "बुनाई", "हथकरघा"},

    # Food Processing
    "cooking": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "food making", "food processing", "hygiene practices", "खाना", "खाना बनाना", "खाना पकाना", "रसोई", "भोजन"},
    "home cooking": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "food making", "food processing", "खाना बनाना", "खाना पकाना"},
    "food handling": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "hygiene practices", "खाना बनाना", "खाना पकाना", "खाद्य"},
    "food preparation": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "खाना बनाना"},
    "खाना बनाना": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "food making", "food processing", "hygiene practices", "खाना बनाना", "खाना पकाना"},
    "खाना पकाना": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "food making", "food processing", "hygiene practices", "खाना बनाना", "खाना पकाना"},
    "खाना": {"cooking", "home cooking", "food handling", "food preparation", "खाना बनाना", "खाना पकाना"},
    "रसोई": {"cooking", "home cooking", "food handling", "kitchen work"},

    # Agriculture & Allied
    "farming": {"farming", "kheti", "agriculture", "cultivation", "crop growing", "cultivator", "खेती", "कृषि", "फसल"},
    "kheti": {"farming", "kheti", "agriculture", "cultivation", "crop growing", "खेती", "कृषि"},
    "cultivation": {"farming", "kheti", "agriculture", "cultivation", "crop growing", "cultivator", "खेती", "कृषि"},
    "organic farming": {"organic farming", "organic grower", "farming", "cultivation", "जैविक खेती"},
    "खेती": {"farming", "kheti", "agriculture", "cultivation", "crop growing", "cultivator", "खेती", "कृषि"},
    "कृषि": {"farming", "kheti", "agriculture", "cultivation", "crop growing", "cultivator", "खेती", "कृषि"},

    # Carpentry, Construction & Trades
    "carpentry": {"carpentry", "woodwork", "furniture making", "carpenter", "wood cutting", "barhai", "बढ़ई", "लकड़ी"},
    "woodwork": {"carpentry", "woodwork", "furniture making", "carpenter", "बढ़ई"},
    "plumbing": {"plumbing", "pipe fitting", "plumber", "water fitting", "pipe repair", "प्लंबर", "नलसाजी"},
    "बढ़ई": {"carpentry", "woodwork", "furniture making", "carpenter"},
    "प्लंबर": {"plumbing", "pipe fitting", "plumber"},

    # Beauty & Wellness
    "beauty": {"beauty", "makeup", "parlour", "skin care", "beautician", "therapist", "beauty therapist", "ब्यूटी", "मेकअप"},
    "makeup": {"beauty", "makeup", "parlour", "skin care", "beautician", "मेकअप"},
    "hair styling": {"hair styling", "hair dresser", "hair cutting", "hair styling and cutting", "बाल काटना"},
    "ब्यूटी": {"beauty", "makeup", "parlour", "skin care", "beautician"},
    "मेकअप": {"beauty", "makeup", "parlour", "skin care", "beautician"},

    # Digital & Entrepreneurship
    "data entry": {"data entry", "computer", "typing", "computer operation", "data operator", "डेटा एंट्री", "कंप्यूटर"},
    "typing": {"data entry", "computer", "typing", "computer operation", "टाइपिंग"},
    "computer": {"data entry", "computer", "typing", "computer operation", "कंप्यूटर"},
    "social media": {"social media", "digital marketing", "online marketing", "content creation"},
    "डेटा एंट्री": {"data entry", "computer", "typing", "computer operation", "data operator"},
    "कंप्यूटर": {"data entry", "computer", "typing", "computer operation"},
    "टाइपिंग": {"data entry", "computer", "typing", "computer operation"},

    # Retail & Sales
    "retail": {"retail", "sales", "shop", "store assistant", "customer service", "selling", "दुकान", "बिक्री"},
    "sales": {"retail", "sales", "shop", "store assistant", "customer service", "selling", "बिक्री"},
    "दुकान": {"retail", "sales", "shop", "store assistant", "selling"},
}


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    return text.lower().translate(_PUNCT_TABLE).strip()


def _tokens(text: str) -> list[str]:
    """Return individual word tokens from a normalised string."""
    return _normalise(text).split()


def _get_synonyms(term: str) -> set[str]:
    """Return known synonyms and equivalences for a term."""
    t = _normalise(term)
    syns = {t}
    for key, cluster in SKILL_SYNONYMS.items():
        if key in t or t in key:
            syns.update(cluster)
    return syns


def _skill_match(user_skill: str, role_skill: str) -> bool:
    """
    Return True if ``user_skill`` is considered equivalent to ``role_skill``.

    Checks:
      1. Direct string equality after normalisation
      2. Bidirectional substring containment
      3. Overlap in curated domain synonym clusters
    """
    u = _normalise(user_skill)
    r = _normalise(role_skill)
    if u == r or u in r or r in u:
        return True

    u_syns = _get_synonyms(u)
    r_syns = _get_synonyms(r)
    return bool(u_syns.intersection(r_syns))


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
) -> tuple[float, list[str]]:
    """
    Compute how many user interests appear in the role's title, sector,
    or description (including domain synonyms).

    Returns
    -------
    tuple[float, list[str]]
        (Fraction of user interests matched [0.0, 1.0], list of matched interest terms)
    """
    if not interests:
        return 0.0, []

    haystack = _normalise(
        f"{role.title} {role.sector} {' '.join(role.required_skills)} {role.description}"
    )
    matched_interests = []
    for interest in interests:
        i_syns = _get_synonyms(interest)
        if any(s in haystack for s in i_syns):
            matched_interests.append(interest)

    return len(matched_interests) / len(interests), matched_interests


def _compute_occupation_score(
    occupation: str | None,
    role: LivelihoodRole,
    experience_years: float | None = None,
    has_matched_skills: bool = False,
) -> float:
    """
    Compute overlap between user occupation / experience and the role.

    Returns
    -------
    float
        Score [0.0, 1.0].
    """
    occ_score = 0.0
    if occupation:
        occ_tokens = _tokens(occupation)
        if occ_tokens:
            haystack = _normalise(
                role.title + " " + " ".join(role.required_skills)
            )
            matched = 0
            for tok in occ_tokens:
                tok_syns = _get_synonyms(tok)
                if any(s in haystack for s in tok_syns):
                    matched += 1
            occ_score = matched / len(occ_tokens)

    # Experience alignment: if occupation doesn't match by name (e.g. Homemaker, None),
    # but the user has practical years of experience in matching skills, credit that experience.
    if occ_score == 0.0 and experience_years and experience_years > 0 and has_matched_skills:
        occ_score = min(experience_years / 5.0, 1.0) * 0.5

    return occ_score


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
    """
    Return EMPLOYMENT_BONUS if the role semantically supports the user's preference.

    - "wage-employment" favors roles supporting wage employment (and not strictly self-employed).
    - "self-employment" favors roles supporting self-employment / entrepreneurship.
    - "either" / flexible receives the full bonus without mismatch penalty.
    """
    if not preference:
        return 0.0
    pref = _normalise(preference)
    if "either" in pref or "both" in pref or "flexible" in pref or "any" in pref or pref == "":
        return EMPLOYMENT_BONUS

    wants_wage = any(k in pref for k in ("wage", "job", "salaried", "service"))
    wants_self = any(k in pref for k in ("self", "business", "own"))

    role_types = [_normalise(e) for e in role.employment_type]
    role_supports_wage = any("wage" in e for e in role_types) and "self-employed" not in role.title.lower()
    role_supports_self = any("self" in e for e in role_types)

    if wants_wage and role_supports_wage:
        return EMPLOYMENT_BONUS
    if wants_self and role_supports_self:
        return EMPLOYMENT_BONUS

    # Fallback to direct substring match for any non-standard preference string
    for emp in role.employment_type:
        emp_n = _normalise(emp)
        if pref in emp_n or emp_n in pref:
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
        Roles to match against. Defaults to the full knowledge base.

    Returns
    -------
    list[MatchResult]
        All roles scored and sorted by ``score`` descending.
    """
    if roles is None:
        roles = get_all_roles()

    results: list[MatchResult] = []

    for role in roles:
        skill_score, matched_skills = _compute_skill_score(
            profile.skills, role.required_skills
        )
        interest_score, matched_interests = _compute_interest_score(
            profile.interests, role
        )
        occupation_score = _compute_occupation_score(
            profile.current_occupation,
            role,
            experience_years=profile.experience_years,
            has_matched_skills=len(matched_skills) > 0,
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
                matched_interests=matched_interests,
                skill_gaps=skill_gaps,
                employment_type=role.employment_type,
            )
        )

    # Sort by score descending; use role_id as a stable tiebreaker
    results.sort(key=lambda r: (-r.score, r.role_id))
    return results

