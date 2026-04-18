"""Query helpers built on top of the registries (capabilities + window map).

These are the functions that role sync and the orchestrator call to
translate iDempiere access lists into bot capability sets.
"""

from .capabilities import CAPABILITIES
from .types import Capability
from .window_map import WINDOW_CAPABILITY_MAP


# Reverse index: table name → capability IDs. Built once at import.
TABLE_CAPABILITY_MAP: dict[str, list[str]] = {}
for _cap in CAPABILITIES.values():
    for _table in _cap.tables:
        TABLE_CAPABILITY_MAP.setdefault(_table.lower(), []).append(_cap.id)


def get_capabilities_for_windows(window_names: list[str]) -> set[str]:
    """Given a list of iDempiere window names, return the capability IDs granted."""
    caps: set[str] = set()
    for wname in window_names:
        wname_lower = wname.lower()
        for pattern, cap_ids in WINDOW_CAPABILITY_MAP:
            if pattern in wname_lower:
                caps.update(cap_ids)
    return caps


def get_capabilities_for_tables(table_names: list[str]) -> set[str]:
    """Given a list of iDempiere table names, return the capability IDs granted."""
    caps: set[str] = set()
    for tname in table_names:
        if tname.lower() in TABLE_CAPABILITY_MAP:
            caps.update(TABLE_CAPABILITY_MAP[tname.lower()])
    return caps


def get_all_keywords_for_capabilities(cap_ids: set[str]) -> set[str]:
    """Get all keywords that are valid for a set of capabilities."""
    keywords: set[str] = set()
    for cap_id in cap_ids:
        cap = CAPABILITIES.get(cap_id)
        if cap:
            keywords.update(cap.keywords)
    return keywords


def get_agents_for_capabilities(cap_ids: set[str]) -> set[str]:
    """Get the set of agent names for a set of capabilities."""
    agents: set[str] = set()
    for cap_id in cap_ids:
        cap = CAPABILITIES.get(cap_id)
        if cap:
            agents.add(cap.agent)
    return agents


def get_capability_for_keyword(keyword: str) -> Capability | None:
    """Find the capability that matches a keyword."""
    keyword_lower = keyword.lower().strip()
    for cap in CAPABILITIES.values():
        if keyword_lower in cap.keywords:
            return cap
    return None


def get_all_capabilities() -> list[dict]:
    """List all capabilities for admin reference."""
    return [
        {
            "id": cap.id,
            "agent": cap.agent,
            "display_name": cap.display_name,
            "keywords_count": len(cap.keywords),
            "tables": list(cap.tables),
        }
        for cap in CAPABILITIES.values()
    ]
