"""SQL Directo — consulta directa a iDempiere via LLM-generated SQL.

Refactor 18/Abr/2026: el módulo monolítico `sql_direct.py` (~1,800 líneas)
se partió en subpaquetes para facilitar mantenimiento:

  sql_direct/
  ├── __init__.py         (este archivo — re-exporta API pública)
  ├── processor.py        (process_with_sql_direct — flujo principal)
  ├── audit.py            (write_audit — telemetría a sql_audit)
  ├── complexity.py       (is_complex_query + create_sql_direct_llm)
  ├── validator.py        (validate_sql — whitelist + security)
  ├── org_filter.py       (enforce_org_filter — blacklist demos iDempiere)
  ├── executor.py         (execute_sql + format_results_as_markdown)
  ├── catalog/            (VIEWS_CATALOG + ALLOWED_TABLES)
  │   ├── views_rrhh.py
  │   ├── views_ventas_cxc.py
  │   ├── views_financieras.py
  │   ├── reglas_sql.py
  │   ├── ejemplos.py
  │   └── allowed_tables.py
  └── prompts/            (System prompt de Claude)
      ├── intro.py
      ├── reglas_2_3.py   reglas_4_5.py
      ├── regla_6a.py     regla_6b.py
      ├── reglas_7_8.py
      ├── instrucciones.py
      └── format_prompt.py

API pública principal: `process_with_sql_direct()`. El resto se re-exporta
por compatibilidad con imports existentes (`validate_catalog.py`,
`analyze_sql_audit.py`).
"""

from .catalog import ALLOWED_TABLES, VIEWS_CATALOG
from .complexity import create_sql_direct_llm, is_complex_query
from .executor import execute_sql, format_results_as_markdown
from .org_filter import (
    IDEMPIERE_DEMO_ORGS,
    ORG_ENFORCEMENT_TABLES,
    build_santoni_org_filter,
    enforce_org_filter,
)
from .processor import process_with_sql_direct
from .validator import validate_sql

# Backward-compat aliases (nombres con prefijo underscore que usaban los
# scripts de QA y otros consumidores externos antes del refactor).
_ALLOWED_TABLES = ALLOWED_TABLES
_IDEMPIERE_DEMO_ORGS = IDEMPIERE_DEMO_ORGS
_ORG_ENFORCEMENT_TABLES = ORG_ENFORCEMENT_TABLES
_is_complex_query = is_complex_query
_create_sql_direct_llm = create_sql_direct_llm
_validate_sql = validate_sql
_enforce_org_filter = enforce_org_filter
_build_santoni_org_filter = build_santoni_org_filter
_execute_sql = execute_sql
_format_results_as_markdown = format_results_as_markdown

__all__ = [
    "process_with_sql_direct",
    "VIEWS_CATALOG",
    "ALLOWED_TABLES",
    "_ALLOWED_TABLES",  # backward compat
]
