"""
Basic validation script for data/nsqf_roles.json.
Run from the project root: python tests/validate_nsqf.py
"""
import json
import sys

DATA_PATH = "data/nsqf_roles.json"

REQUIRED_FIELDS = [
    "id", "title", "qp_code", "nsqf_level", "sector",
    "required_skills", "gap_skills_covered", "eligibility",
    "qualification", "duration", "description",
    "employment_type", "source", "last_verified",
]

SOURCE_FIELDS = ["organization", "document", "url"]


def main():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"FAIL: JSON parse error — {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"FAIL: File not found — {DATA_PATH}")
        sys.exit(1)

    print(f"Version        : {data.get('version', 'MISSING')}")
    print(f"Last updated   : {data.get('last_updated', 'MISSING')}")
    roles = data.get("roles", [])
    print(f"Total roles    : {len(roles)}")
    print()

    # Sector distribution
    sectors = {}
    for r in roles:
        s = r.get("sector", "Unknown")
        sectors[s] = sectors.get(s, 0) + 1

    print("--- Sector Distribution ---")
    for s, n in sorted(sectors.items()):
        print(f"  {s}: {n}")
    print()

    # All roles summary
    print("--- All Roles ---")
    for r in roles:
        print(
            f"  [{r.get('id','?')}] {r.get('title','?')} "
            f"| NSQF {r.get('nsqf_level','?')} "
            f"| {r.get('sector','?')}"
        )
    print()

    # Field completeness check
    issues = []
    for r in roles:
        rid = r.get("id", "UNKNOWN_ID")
        for field in REQUIRED_FIELDS:
            if field not in r:
                issues.append(f"{rid}: missing field '{field}'")
            elif r[field] == "" or r[field] == [] or r[field] is None:
                issues.append(f"{rid}: empty field '{field}'")
        # Validate source sub-fields
        src = r.get("source", {})
        for sf in SOURCE_FIELDS:
            if sf not in src or not src[sf]:
                issues.append(f"{rid}: source.{sf} missing or empty")

    print("--- Field Completeness ---")
    if issues:
        print(f"ISSUES ({len(issues)}):")
        for i in issues:
            print(f"  {i}")
    else:
        print("OK: All required fields present and non-empty in all records.")
    print()

    # Unique ID check
    ids = [r.get("id") for r in roles]
    print("--- Unique ID Check ---")
    if len(ids) == len(set(ids)):
        print("OK: All IDs are unique.")
    else:
        dupes = [x for x in ids if ids.count(x) > 1]
        print(f"FAIL: Duplicate IDs found: {set(dupes)}")

    # Skill list non-empty check
    print()
    print("--- Skill List Sizes ---")
    for r in roles:
        req = len(r.get("required_skills", []))
        gap = len(r.get("gap_skills_covered", []))
        emp = len(r.get("employment_type", []))
        print(
            f"  [{r.get('id','?')}] required_skills={req}"
            f"  gap_skills={gap}  employment_types={emp}"
        )

    print()
    if not issues and len(ids) == len(set(ids)):
        print("=== VALIDATION PASSED ===")
        sys.exit(0)
    else:
        print("=== VALIDATION FAILED — see issues above ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
