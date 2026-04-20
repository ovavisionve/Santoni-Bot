"""Data Catalog Service — extracts iDempiere metadata and indexes it in ChromaDB.

Refactored from monolithic data_catalog.py (~910 lines) into domain modules:
  data_catalog/
  ├── __init__.py          (this file — re-exports)
  ├── constants.py         (DEPARTMENT_TABLES, PROFILE_COLUMNS, DATE_COLUMNS)
  ├── discovery.py         (schema discovery, relationships, profiling, sampling)
  ├── department_stats.py  (per-department operational queries)
  ├── documents.py         (build ChromaDB documents)
  └── service.py           (DataCatalogService + get_catalog_service)
"""

from .constants import DATE_COLUMNS, DEPARTMENT_TABLES, PROFILE_COLUMNS
from .service import DataCatalogService, get_catalog_service

__all__ = [
    "DataCatalogService",
    "get_catalog_service",
    "DEPARTMENT_TABLES",
    "PROFILE_COLUMNS",
    "DATE_COLUMNS",
]
