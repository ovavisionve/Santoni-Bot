"""iDempiere query functions — modular package.

Refactored from monolithic idempiere_queries.py (3,843 lines) into
domain-specific modules for maintainability.

All public functions are re-exported here for backward compatibility —
existing imports like `from app.services.idempiere_queries import build_sales_summary`
continue working unchanged.

Structure:
  idempiere_queries/
  ├── __init__.py           (this file — re-exports)
  ├── common.py             (shared helpers, filters, constants)
  ├── ventas_helpers.py     (zone mapping, currency label, salesrep dedup)
  ├── ventas_core.py        (sales summary, collection, top clients)
  ├── ventas_extended.py    (receivables, by-product, orders, tax, branch)
  ├── finanzas.py           (bank balances, AR/AP)
  ├── rrhh.py               (employees, birthdays, payroll, attendance)
  ├── produccion.py         (production summary, orders)
  ├── compras_productores.py (agricultural purchases, producers)
  ├── compras_insumos.py    (supply purchases, pending orders, prices)
  ├── contabilidad.py       (balance sheet, account detail)
  └── inventario.py         (stock levels)
"""

# Common helpers & constants
from .common import (
    _ALLOC_JOIN,
    _IDEMPIERE_DEMO_ORGS,
    _OPEN_EXPR,
    _PRODUCT_STOP_WORDS,
    _SANTONI_ORG_FILTER,
    _add_currency_filter,
    _add_date_filter,
    _add_org_filter,
    _add_org_name_filter,
    _add_product_search_filter,
    _convert_value,
    _get_cutoff_date,
    _get_session,
    _is_before_cutoff,
    _is_historical_enabled,
    _normalize_search_word,
    _rows_to_dicts,
    execute_idempiere_query,
    logger,
)

# Ventas helpers
from .ventas_helpers import (
    _ZONE_TO_REGION,
    _add_salesrep_filter,
    _currency_label,
    _dedupe_salesrep_rows,
    _region_case_sql,
)

# Ventas — core
from .ventas_core import (
    build_collection_summary,
    build_sales_summary,
    build_top_clients,
)

# Ventas — extended
from .ventas_extended import (
    build_exchange_rates,
    build_overdue_receivables,
    build_sales_by_branch,
    build_sales_by_product,
    build_sales_orders,
    build_sales_tax_summary,
)

# Finanzas
from .finanzas import build_financial_summary

# RRHH
from .rrhh import (
    build_attendance_summary,
    build_birthday_list,
    build_employee_list,
    build_employee_summary,
    build_payroll_summary,
    build_turnover_summary,
    build_vacation_summary,
)

# Producción
from .produccion import (
    build_production_orders,
    build_production_summary,
)

# Compras Productores
from .compras_productores import (
    build_producer_pending_payments,
    build_producer_price_analysis,
    build_producer_purchases,
    build_registered_producers,
)

# Compras Insumos
from .compras_insumos import (
    build_pending_purchase_orders,
    build_product_purchase_history,
    build_purchase_payment_status,
    build_supply_purchases,
    build_supplier_price_comparison,
)

# Contabilidad
from .contabilidad import (
    build_account_detail,
    build_accounting_summary,
)

# Inventario
from .inventario import build_inventory_stock

__all__ = [
    # Common
    "execute_idempiere_query",
    "_IDEMPIERE_DEMO_ORGS",
    "_SANTONI_ORG_FILTER",
    # Ventas
    "build_sales_summary",
    "build_collection_summary",
    "build_top_clients",
    "build_overdue_receivables",
    "build_sales_by_product",
    "build_sales_orders",
    "build_exchange_rates",
    "build_sales_tax_summary",
    "build_sales_by_branch",
    # Finanzas
    "build_financial_summary",
    # RRHH
    "build_employee_summary",
    "build_employee_list",
    "build_birthday_list",
    "build_payroll_summary",
    "build_attendance_summary",
    "build_turnover_summary",
    "build_vacation_summary",
    # Producción
    "build_production_summary",
    "build_production_orders",
    # Compras Productores
    "build_producer_purchases",
    "build_registered_producers",
    "build_producer_pending_payments",
    "build_producer_price_analysis",
    # Compras Insumos
    "build_supply_purchases",
    "build_product_purchase_history",
    "build_pending_purchase_orders",
    "build_supplier_price_comparison",
    "build_purchase_payment_status",
    # Contabilidad
    "build_accounting_summary",
    "build_account_detail",
    # Inventario
    "build_inventory_stock",
]
