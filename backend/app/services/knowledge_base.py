"""
Knowledge base service.

Responsible for locating, loading, and validating data/nsqf_roles.json.
The JSON file is the single source of truth — no data is duplicated here.

The file is loaded once at import time and cached in memory.  This keeps
request latency low without requiring a database.

Path resolution strategy
------------------------
The data file lives at:
    <project_root>/data/nsqf_roles.json

This module resolves the path relative to its own location:
    <project_root>/backend/app/services/knowledge_base.py
                           ↑ 3 levels up = project root

This makes the path work regardless of the working directory from which
uvicorn is launched.
"""
import json
import logging
from pathlib import Path
from functools import lru_cache

from app.models.role import KnowledgeBase, LivelihoodRole

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution: this file is at  backend/app/services/knowledge_base.py
# Three .parent calls reach the project root.
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent.parent  # backend/app/services -> backend/app -> backend -> project_root
_DATA_FILE = _PROJECT_ROOT / "data" / "nsqf_roles.json"


def _load_knowledge_base() -> KnowledgeBase:
    """
    Load and validate the knowledge base from disk.

    Raises
    ------
    FileNotFoundError
        If data/nsqf_roles.json is not found at the expected path.
    ValueError
        If the JSON file exists but fails Pydantic validation.
    json.JSONDecodeError
        If the file is not valid JSON.
    """
    if not _DATA_FILE.exists():
        raise FileNotFoundError(
            f"Knowledge base not found at '{_DATA_FILE}'. "
            "Ensure data/nsqf_roles.json exists in the project root."
        )

    logger.info("Loading knowledge base from %s", _DATA_FILE)

    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    try:
        kb = KnowledgeBase.model_validate(raw)
    except Exception as exc:
        raise ValueError(
            f"Knowledge base failed Pydantic validation: {exc}"
        ) from exc

    logger.info(
        "Knowledge base loaded: %d roles across %d sectors",
        len(kb.roles),
        len({r.sector for r in kb.roles}),
    )
    return kb


# ---------------------------------------------------------------------------
# Cached access — the KB is loaded once per process lifetime.
# Use lru_cache(maxsize=1) so the heavy I/O only happens once.
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    """Return the loaded, validated knowledge base (cached after first call)."""
    return _load_knowledge_base()


def get_all_roles() -> list[LivelihoodRole]:
    """Return all roles from the knowledge base."""
    return get_knowledge_base().roles


def get_role_by_id(role_id: str) -> LivelihoodRole | None:
    """
    Return a single role by its ID (case-insensitive), or None if not found.

    Parameters
    ----------
    role_id : str
        Role ID such as ``"T-001"`` or ``"t-001"``.
    """
    target = role_id.strip().upper()
    for role in get_all_roles():
        if role.id.upper() == target:
            return role
    return None


def get_sectors_summary() -> list[dict]:
    """
    Return a list of sectors with their role counts, sorted alphabetically.

    Returns
    -------
    list[dict]
        Each entry has keys ``"name"`` (str) and ``"count"`` (int).
    """
    counts: dict[str, int] = {}
    for role in get_all_roles():
        counts[role.sector] = counts.get(role.sector, 0) + 1

    return [
        {"name": sector, "count": count}
        for sector, count in sorted(counts.items())
    ]
