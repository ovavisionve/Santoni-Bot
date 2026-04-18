"""Capability dataclass used across the window/capability registry."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Capability:
    """A specific bot query capability granted by an iDempiere window."""
    id: str                        # Unique ID, e.g. "ventas_facturacion"
    agent: str                     # Bot agent name, e.g. "ventas"
    query_function: str            # Function in idempiere_queries.py
    display_name: str              # Human-readable name (Spanish)
    keywords: tuple[str, ...]      # Keywords that trigger this capability
    tables: tuple[str, ...]        # iDempiere tables queried
