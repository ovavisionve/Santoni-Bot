"""Catálogo de views/tablas + reglas + ejemplos para SQL Directo.

El catálogo se compone de 4 partes temáticas para facilitar el mantenimiento:
  - views_rrhh.py         → RRHH + Nómina
  - views_ventas_cxc.py   → Ventas, Monedas, Cobranza, CxC aging
  - views_financieras.py  → Bancos, Compras, Contabilidad, Producción, Inventario
  - reglas_sql.py         → 12 REGLAS de generación SQL
  - ejemplos.py           → Queries de referencia
  - allowed_tables.py     → Whitelist de tablas/views

`VIEWS_CATALOG` concatena todo en el orden que espera Claude.
"""

from .allowed_tables import ALLOWED_TABLES
from .views_rrhh import VIEWS_RRHH
from .views_ventas_cxc import VIEWS_VENTAS_CXC
from .views_financieras import VIEWS_FINANCIERAS
from .reglas_sql import REGLAS_SQL
from .ejemplos import EJEMPLOS_SQL

_HEADER = """
## Views disponibles en iDempiere (Localización Venezuela — lve_*)

Estas son las fuentes OFICIALES de datos de Alimentos Santoni. Usa SOLO estas views.
"""

VIEWS_CATALOG = (
    _HEADER
    + VIEWS_RRHH
    + VIEWS_VENTAS_CXC
    + VIEWS_FINANCIERAS
    + REGLAS_SQL
    + EJEMPLOS_SQL
)

__all__ = ["ALLOWED_TABLES", "VIEWS_CATALOG"]
