"""iDempiere Window → Bot Capability mapping.

Maps iDempiere windows (ad_window) to specific bot query types.
Each window grants access to one or more "capabilities" — a capability
is a specific query the bot can run (e.g., "ventas_facturacion",
"rrhh_nomina", "contabilidad_balance").

This is the source of truth that connects:
  iDempiere window → iDempiere tables → bot agent → query function → keywords

Public API is re-exported here so imports keep working after the split.
"""

from .capabilities import CAPABILITIES
from .lookups import (
    TABLE_CAPABILITY_MAP,
    get_agents_for_capabilities,
    get_all_capabilities,
    get_all_keywords_for_capabilities,
    get_capabilities_for_tables,
    get_capabilities_for_windows,
    get_capability_for_keyword,
)
from .types import Capability
from .window_map import WINDOW_CAPABILITY_MAP

__all__ = [
    "CAPABILITIES",
    "Capability",
    "TABLE_CAPABILITY_MAP",
    "WINDOW_CAPABILITY_MAP",
    "get_agents_for_capabilities",
    "get_all_capabilities",
    "get_all_keywords_for_capabilities",
    "get_capabilities_for_tables",
    "get_capabilities_for_windows",
    "get_capability_for_keyword",
]
