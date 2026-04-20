"""Query service — routes queries to demo or iDempiere data source.

Refactored from monolithic query_service.py (1,374 lines) into
domain-specific modules. All public functions re-exported here
for backward compatibility.

Structure:
  query_service/
  ├── __init__.py              (this file)
  ├── core.py                  (routing, helpers, schema)
  ├── ventas.py                (sales wrappers)
  ├── produccion.py            (production wrappers)
  ├── compras_productores.py   (producer purchases)
  ├── finanzas.py              (financial wrappers)
  ├── rrhh.py                  (HR wrappers)
  ├── compras_insumos.py       (supply purchases)
  ├── contabilidad.py          (accounting wrappers)
  └── inventario.py            (inventory wrappers)
"""

# Core
from .core import (
    _convert_value,
    _is_production,
    _rows_to_dicts,
    execute_demo_query,
    get_available_tables,
    get_table_schema,
)

# Ventas
from .ventas import (
    build_collection_summary,
    build_exchange_rates,
    build_overdue_receivables,
    build_sales_by_branch,
    build_sales_by_product,
    build_sales_orders,
    build_sales_summary,
    build_sales_tax_summary,
    build_top_clients,
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
    "execute_demo_query",
    "get_table_schema",
    "get_available_tables",
    "build_sales_summary",
    "build_collection_summary",
    "build_top_clients",
    "build_overdue_receivables",
    "build_sales_by_product",
    "build_sales_orders",
    "build_exchange_rates",
    "build_sales_tax_summary",
    "build_sales_by_branch",
    "build_production_summary",
    "build_production_orders",
    "build_producer_purchases",
    "build_registered_producers",
    "build_producer_pending_payments",
    "build_producer_price_analysis",
    "build_financial_summary",
    "build_employee_summary",
    "build_employee_list",
    "build_birthday_list",
    "build_payroll_summary",
    "build_attendance_summary",
    "build_turnover_summary",
    "build_vacation_summary",
    "build_supply_purchases",
    "build_product_purchase_history",
    "build_pending_purchase_orders",
    "build_supplier_price_comparison",
    "build_purchase_payment_status",
    "build_accounting_summary",
    "build_account_detail",
    "build_inventory_stock",
]
