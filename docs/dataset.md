# SkillFlow Knowledge Base — Dataset Documentation

## Overview

`data/nsqf_roles.json` is the curated, government-aligned knowledge base that powers SkillFlow's skill-gap analysis and livelihood pathway recommendations.

> **Important:** This is a **curated knowledge base**, not a live government database. It does not claim to reflect real-time data from any government system. Entries are based on publicly available Qualification Pack (QP) documents and the National Qualification Register (NQR).

---

## Source Methodology

### Primary Sources

All entries are derived from **official Indian government and sector skill council sources only**. No data was invented or estimated without a verifiable source.

| Source | What it was used for |
|---|---|
| **National Qualification Register (NQR)** — `nqr.gov.in` | QP codes, NSQF levels, status verification |
| **Apparel, Made-Ups & Home Furnishing SSC (AMHSSC)** — `sscamh.com` | Apparel sector roles (T-001, T-002, T-003) |
| **Agriculture Skill Council of India (ASCI)** — `asci-india.com` | Agriculture roles (A-001, A-002, A-003) |
| **Furniture & Fittings Skill Council (FFSC)** — `ffsc.in` | Carpentry/furniture roles (C-001, C-002) |
| **Construction Skill Development Council of India (CSDCI)** — `csdcindia.org` | Construction roles (C-003) |
| **Water Management & Plumbing Skill Council (WMPSC)** — `wmpsc.in` | Plumbing role (C-004) |
| **Retailers Association's Skill Council of India (RASCI)** — `rasci.in` | Retail role (R-001) |
| **Handicrafts and Carpet Sector Skill Council (HCSSC)** — `hcssc.in` | Handicraft roles (R-002, R-003) |
| **Textile Sector Skill Council (TSC)** — `texskill.in` | Handloom weaving role (T-004) |
| **IT-ITeS Sector Skills Council NASSCOM** — `nqr.gov.in` | Data entry role (D-001) |
| **Media and Entertainment Skills Council (MESC)** — `mescindia.org` | Digital roles (D-002, D-003) |
| **Beauty & Wellness Sector Skill Council (B&WSSC)** — `bwssc.in` | Beauty roles (B-001, B-002) |
| **Food Industry Capacity & Skill Initiative (FICSI)** — `ficsi.in` | Food processing role (F-001) |

### Methodology

1. Official SSC websites and the NQR portal were queried for each sector.
2. Only roles with a **verifiable QP code and NSQF level** were included.
3. Duration and eligibility figures are drawn from official QP documents or PMKVY curriculum frameworks where publicly available.
4. Fields that could not be verified in official sources are set to `"Not specified in source"`.
5. The dataset was reviewed for internal consistency and validated programmatically before commit.

---

## Schema

Each role record in `data/nsqf_roles.json` follows this schema:

```json
{
  "id": "Unique identifier (prefix: T=Textiles, A=Agriculture, C=Carpentry/Construction, R=Retail/Handicrafts, D=Digital, B=Beauty, F=Food)",
  "title": "Official role title from the Qualification Pack",
  "qp_code": "Official QP Code from the SSC / NQR",
  "nsqf_level": "Numeric NSQF level (e.g. 3, 4, 4.5)",
  "sector": "Sector category used for matching",
  "required_skills": ["Normalised skill terms the role requires"],
  "gap_skills_covered": ["Skills this training will add — used for gap analysis"],
  "eligibility": "Minimum educational/experience requirements",
  "qualification": "Official certificate name and awarding body",
  "duration": "Training duration in notional hours (if available in source)",
  "description": "Plain-language description of the role and its suitability",
  "employment_type": ["wage-employment and/or self-employment"],
  "source": {
    "organization": "Sector Skill Council or awarding body",
    "document": "QP document title and code",
    "url": "Official website URL"
  },
  "last_verified": "Date last cross-checked against source (YYYY-MM-DD)"
}
```

---

## Sectors Covered

| Sector | Roles | IDs |
|---|---|---|
| Apparel & Textiles | 4 | T-001, T-002, T-003, T-004 |
| Agriculture & Allied Activities | 3 | A-001, A-002, A-003 |
| Carpentry, Construction & Skilled Trades | 4 | C-001, C-002, C-003, C-004 |
| Retail & Handicrafts | 3 | R-001, R-002, R-003 |
| Digital & Entrepreneurship | 3 | D-001, D-002, D-003 |
| Beauty & Wellness | 2 | B-001, B-002 |
| Food Processing | 1 | F-001 |
| **Total** | **20** | |

---

## NSQF Level Distribution

| NSQF Level | Roles |
|---|---|
| 2.5 | T-001 |
| 3 | T-004, A-001, A-003, C-001, C-003, R-001, R-002, D-001, B-001 |
| 4 | T-002, T-003, A-002, C-004, R-003, D-002, B-002, F-001 |
| 4.5 | C-002 |
| 5 | D-003 |

---

## Skill Terminology Normalisation

Skill terms in `required_skills` and `gap_skills_covered` are normalised to support consistent keyword matching. Examples of preferred terms used in this dataset:

| Preferred Term | Covers |
|---|---|
| `Sewing` | Stitching, sewing by hand, basic needlework |
| `Tailoring` | Garment construction, cutting and sewing |
| `Garment Making` | Apparel construction |
| `Alteration` | Garment alteration, repair |
| `Weaving` | Handloom operation, loom-based textile production |
| `Woodworking` | Carpentry, furniture making, joinery |
| `Crop Cultivation` | Farming, field crop production |
| `Digital Literacy` | Basic computer use, internet usage |
| `Digital Marketing` | Online marketing, social media promotion |
| `Online Selling` | E-commerce, selling via platforms |
| `Customer Service` | Client handling, customer interaction |
| `Sales` | Retail sales, direct selling |

This normalisation ensures the matching engine can correctly link user-stated skills (e.g., "I know stitching") to dataset entries (e.g., `"Sewing"` in `required_skills`).

---

## Limitations

1. **Not a live database.** This dataset is a point-in-time snapshot. NSQF levels, QP codes, eligibility requirements, and training durations are subject to periodic revision by SSCs and the Ministry of Skill Development & Entrepreneurship. Always refer to the NQR or the relevant SSC website for the most current information.

2. **Duration gaps.** Training durations are not publicly available for all roles in official QP documents. Affected records are marked `"Not specified in source"`.

3. **Eligibility variations.** Some QPs have different eligibility criteria for different programme pathways (e.g., PMKVY STT vs. RPL). Where this is the case, the most common/general criteria are recorded.

4. **Limited sector coverage.** The MVP dataset covers 7 sectors with 20 roles. Sectors such as healthcare, construction (advanced trades), logistics, and manufacturing are not yet represented.

5. **No geographic data.** Training availability varies by region and is not captured in this dataset.

6. **No live scheme data.** Specific PMKVY batch availability, stipend amounts, or training centre locations are not included and must be verified through the Skill India Digital Hub (`skillindiadigital.gov.in`).

---

## How the Matching Engine Uses This Dataset

The SkillFlow recommendation engine will:

1. Extract a user profile (skills, education, occupation, interests, employment preference) from the LLM conversation.
2. Compare the user's existing skills against `required_skills` in each record.
3. Identify `gap_skills_covered` — skills the user lacks but the training would provide.
4. Score and rank records by overlap with user skills and interests.
5. Return the top 3 recommendations with an LLM-generated explanation grounded in the matched records.

---

## Validation

A validation script is available at `tests/validate_nsqf.py`. Run from the project root:

```bash
python tests/validate_nsqf.py
```

The script checks:
- Valid JSON syntax
- All required fields present and non-empty in every record
- Unique IDs across all records
- Sector distribution and skill list sizes

**Last validation result (2026-09-25):** `VALIDATION PASSED` — 20 records, 0 issues.

---

## Future Improvements

- Add more sectors: Healthcare, Logistics, Construction (advanced), Tourism & Hospitality
- Add `location_relevance` or `cluster_regions` to support geographic recommendations
- Expand to 40–50 roles as the recommendation engine matures
- Integrate with live NQR API if one becomes available
- Add Hindi translations of role titles and descriptions
