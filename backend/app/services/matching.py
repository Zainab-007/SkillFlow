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
    matched_specialization: list[str] = field(default_factory=list)
    occupation_matched: bool = False
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
    "cooking": {"cooking", "home cooking", "food preparation", "food handling", "food processing", "kitchen work", "food making", "खाना", "खाना बनाना", "खाना पकाना", "रसोई", "भोजन"},
    "home cooking": {"cooking", "home cooking", "food preparation", "food handling", "food processing", "kitchen work", "food making", "खाना बनाना", "खाना पकाना"},
    "food handling": {"food handling", "food storage", "safe food handling", "food preparation", "खाद्य हैंडलिंग"},
    "food preparation": {"cooking", "home cooking", "food handling", "food preparation", "kitchen work", "food making", "खाना बनाना"},
    "food processing": {"food processing", "food packaging", "preservation", "खाद्य प्रसंस्करण"},
    "hygiene practices": {"hygiene practices", "food safety", "sanitation", "cleanliness"},
    "खाना बनाना": {"cooking", "home cooking", "food preparation", "kitchen work", "food making", "खाना बनाना", "खाना पकाना"},
    "खाना पकाना": {"cooking", "home cooking", "food preparation", "kitchen work", "food making", "खाना बनाना", "खाना पकाना"},
    "खाना": {"cooking", "home cooking", "food preparation", "खाना बनाना", "खाना पकाना"},
    "रसोई": {"cooking", "home cooking", "food preparation", "kitchen work"},

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

    # Web Development
    "web development": {"web development", "web developer", "website development", "web design"},
    "web developer": {"web development", "web developer", "website development"},
    "website development": {"web development", "web developer", "website development", "web design"},
    "backend development": {"backend development", "back-end development", "backend architecture", "server-side development", "backend"},
    "back-end development": {"backend development", "back-end development", "backend architecture", "server-side development", "backend"},
    "frontend development": {"frontend development", "front-end development", "client-side development", "frontend"},
    "front-end development": {"frontend development", "front-end development", "client-side development", "frontend"},

    # Programming & Software
    "programming": {"programming", "coding", "software programming", "computer programming"},
    "coding": {"programming", "coding", "software programming"},
    "software development": {"software development", "software engineering", "application development"},
    "software developer": {"software developer", "software development", "software engineer"},
    "software engineering": {"software development", "software engineering", "software architecture"},

    # Technical Skills
    "python": {"python", "python3", "python programming"},
    "java": {"java", "core java", "java programming"},
    "mysql": {"mysql", "sql", "relational database", "database basics", "rdbms"},
    "sql": {"sql", "mysql", "database basics", "querying", "database"},
    "database": {"database", "database management", "sql", "mysql", "database basics"},
    "database management": {"database management", "database administration", "sql", "mysql", "rdbms", "database"},
    "database basics": {"database basics", "database", "sql", "mysql", "relational database"},
    "api": {"api", "api development", "api integration", "rest api"},
    "html": {"html", "html5", "html/css"},
    "css": {"css", "css3", "html/css"},
    "html/css": {"html", "css", "html/css", "html5", "css3"},
    "javascript": {"javascript", "js", "ecmascript"},

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
        if key == t or (len(key) > 3 and key in t):
            syns.update(cluster)
    return syns


def _skill_match(user_skill: str, role_skill: str) -> bool:
    """
    Return True if ``user_skill`` is considered equivalent to ``role_skill``.

    Checks:
      1. Direct string equality after normalisation
      2. Bidirectional substring containment with word-boundary guards
      3. Overlap in curated domain synonym clusters
    """
    u = _normalise(user_skill)
    r = _normalise(role_skill)
    if u == r:
        return True

    # Guard against accidental substring matches between distinct tech terms
    if (u == "java" and "javascript" in r) or (r == "java" and "javascript" in u):
        return False
    if (u == "sql" and "nosql" in r) or (r == "sql" and "nosql" in u):
        return False

    # Word-boundary phrase containment
    padded_u = f" {u} "
    padded_r = f" {r} "
    if padded_u in padded_r or padded_r in padded_u:
        return True

    # Token-level overlap and stem prefix match
    u_tokens = _tokens(u)
    r_tokens = _tokens(r)
    if any(ut in r_tokens for ut in u_tokens if len(ut) >= 3):
        return True

    if any(
        (ut.startswith(rt) or rt.startswith(ut))
        for ut in u_tokens
        for rt in r_tokens
        if min(len(ut), len(rt)) >= 4
    ):
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


def _compute_specialization_score(
    specialization: str | None,
    role: LivelihoodRole,
) -> tuple[float, list[str]]:
    """
    Compute alignment between user's preferred specialization and the role.

    Checks role title, sector, required_skills, gap_skills_covered, and description
    using normalized terms and domain synonyms.
    """
    if not specialization or not specialization.strip():
        return 0.0, []

    s_clean = specialization.strip()
    s_syns = _get_synonyms(s_clean)
    haystack = _normalise(
        f"{role.title} {role.sector} {' '.join(role.required_skills)} {' '.join(role.gap_skills_covered)} {role.description}"
    )

    if any(s in haystack for s in s_syns):
        return 1.0, [s_clean]

    return 0.0, []


def _compute_occupation_score(
    occupation: str | None,
    activity: str | None,
    role: LivelihoodRole,
    experience_years: float | None = None,
    has_matched_skills: bool = False,
) -> tuple[float, bool]:
    """
    Compute overlap between user occupation / activity / experience and the role.

    Returns
    -------
    tuple[float, bool]
        (score [0.0, 1.0], occupation_matched: bool)
    """
    occ_score = 0.0
    occ_matched = False
    text_to_check = []
    if occupation and occupation.strip():
        text_to_check.append(occupation.strip())
    if activity and activity.strip():
        text_to_check.append(activity.strip())

    if text_to_check:
        combined_text = " ".join(text_to_check)
        tokens = _tokens(combined_text)
        stopwords = {
            "i", "am", "a", "an", "the", "in", "and", "of", "for", "with",
            "work", "working", "worker", "etc", "doing", "making", "building",
            "build", "project", "projects", "help", "helping", "various", "general",
        }
        filtered_tokens = [t for t in tokens if t not in stopwords and len(t) > 2]
        if filtered_tokens:
            haystack = _normalise(
                role.title + " " + role.sector + " " + " ".join(role.required_skills)
            )
            matched = 0
            for tok in filtered_tokens:
                tok_syns = _get_synonyms(tok)
                if any(s in haystack for s in tok_syns):
                    matched += 1
            if matched > 0:
                occ_score = matched / len(filtered_tokens)
                occ_matched = True

    # Experience alignment:
    # 1. If occupation itself matched and user has years of experience, credit that experience
    if occ_matched and experience_years and experience_years > 0:
        occ_score = min(occ_score + (min(experience_years / 5.0, 1.0) * 0.3), 1.0)
    # 2. If occupation is neutral / informal (e.g. Homemaker, None, Student) and user has verified matching skills,
    # credit that practical domestic / informal experience.
    elif not occ_matched and experience_years and experience_years > 0 and has_matched_skills:
        occ_name = (occupation or "").lower().strip()
        is_informal_or_neutral = occ_name in {"", "none", "homemaker", "student", "unemployed", "fresher"}
        if is_informal_or_neutral:
            occ_score = min(experience_years / 5.0, 1.0) * 0.5

    return min(occ_score, 1.0), occ_matched


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
    Return EMPLOYMENT_BONUS if the role semantically supports the user's specific preference.

    - "wage-employment" favors roles supporting wage employment (and not strictly self-employed).
    - "self-employment" favors roles supporting self-employment / entrepreneurship.
    - "either" / flexible indicates no preference restriction and awards no artificial preference bonus.
    """
    if not preference:
        return 0.0
    pref = _normalise(preference)
    if "either" in pref or "both" in pref or "flexible" in pref or "any" in pref or pref == "":
        return 0.0

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

    Conceptual priority:
    1. Preferred specialization
    2. Explicit interests
    3. Relevant existing skills
    4. Relevant experience / occupation / activity
    5. Employment preference bonus

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
        spec_score, matched_spec = _compute_specialization_score(
            profile.preferred_specialization, role
        )
        occupation_score, occ_matched = _compute_occupation_score(
            profile.current_occupation,
            getattr(profile, "current_activity", None),
            role,
            experience_years=profile.experience_years,
            has_matched_skills=len(matched_skills) > 0,
        )
        bonus = _employment_bonus(profile.employment_preference, role)

        # CRITICAL HOLISTIC RULE:
        # A role MUST have genuine semantic connection to the user profile.
        # If there are zero matching skills, zero matching interests, zero matching specialization,
        # and no matching occupation or experience, the role has ZERO relevance.
        # An employment preference alone (e.g. "Either", "Wage-employment") must NEVER
        # award points to an otherwise unrelated role.
        has_core_evidence = (
            len(matched_skills) > 0
            or len(matched_interests) > 0
            or len(matched_spec) > 0
            or occ_matched
            or (len(matched_skills) > 0 and profile.experience_years and profile.experience_years > 0)
        )

        if profile.preferred_specialization:
            core_score = (
                0.25 * spec_score
                + 0.25 * interest_score
                + 0.30 * skill_score
                + 0.15 * occupation_score
            )
        else:
            core_score = (
                WEIGHT_SKILLS * skill_score
                + WEIGHT_INTERESTS * interest_score
                + WEIGHT_OCCUPATION * occupation_score
            )

        if not has_core_evidence or core_score <= 0.0:
            final_score = 0.0
        else:
            final_score = round(min(core_score + bonus, 1.0), 4)

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
                matched_specialization=matched_spec,
                occupation_matched=occ_matched,
                skill_gaps=skill_gaps,
                employment_type=role.employment_type,
            )
        )

    # Sort by score descending; use role_id as a stable tiebreaker
    results.sort(key=lambda r: (-r.score, r.role_id))
    return results

