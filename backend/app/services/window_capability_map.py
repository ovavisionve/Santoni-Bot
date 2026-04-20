"""iDempiere Window → Bot Capability mapping.

Maps iDempiere windows (ad_window) to specific bot query types.
Each window grants access to one or more "capabilities" — a capability
is a specific query the bot can run (e.g., "ventas_facturacion",
"rrhh_nomina", "contabilidad_balance").

This is the source of truth that connects:
  iDempiere window → iDempiere tables → bot agent → query function → keywords

When a user's iDempiere role grants access to a window, they get
the capabilities associated with that window, which determines:
  1. Which agent handles the query
  2. Which query functions can be called
  3. Which keywords trigger the capability
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Capability:
    """A specific bot query capability granted by an iDempiere window."""
    id: str                        # Unique ID, e.g. "ventas_facturacion"
    agent: str                     # Bot agent name, e.g. "ventas"
    query_function: str            # Function in idempiere_queries.py
    display_name: str              # Human-readable name (Spanish)
    keywords: tuple[str, ...]      # Keywords that trigger this capability
    tables: tuple[str, ...]        # iDempiere tables queried


# ──────────────────────────────────────────────────────────────
# CAPABILITY REGISTRY
# All possible bot capabilities, organized by agent
# ──────────────────────────────────────────────────────────────

CAPABILITIES: dict[str, Capability] = {}


def _reg(cap: Capability) -> Capability:
    CAPABILITIES[cap.id] = cap
    return cap


# ─── VENTAS ───────────────────────────────────────────────────

_reg(Capability(
    id="ventas_facturacion",
    agent="ventas",
    query_function="build_sales_summary",
    display_name="Facturación de ventas",
    keywords=(
        "facturación", "facturacion", "factura", "facturas",
        "ventas", "venta", "vendido", "vendidos",
        "ingreso", "ingresos", "revenue",
        "por zona", "por vendedor", "por cliente",
        "facturado", "facturamos", "se vendió", "se vendio",
    ),
    tables=("c_invoice", "c_bpartner", "c_salesregion", "c_bpartner_location",
            "c_doctype", "ad_org", "c_currency"),
))

_reg(Capability(
    id="ventas_cobranza",
    agent="ventas",
    query_function="build_collection_summary",
    display_name="Cobranzas y pagos recibidos",
    keywords=(
        "cobranza", "cobranzas", "cobro", "cobros", "cobrado",
        "pago recibido", "pagos recibidos", "recaudación", "recaudacion",
        "efectivo", "transferencia", "cheque",
        "forma de pago", "método de pago", "metodo de pago",
    ),
    tables=("c_payment", "c_bpartner", "c_allocationline", "c_invoice", "c_currency"),
))

_reg(Capability(
    id="ventas_top_clientes",
    agent="ventas",
    query_function="build_top_clients",
    display_name="Top clientes por facturación",
    keywords=(
        "top clientes", "mejores clientes", "clientes principales",
        "clientes más", "clientes mas", "ranking clientes",
        "quién compra más", "quien compra mas",
        "cliente", "clientes",
        "tipología", "tipologia", "tipo de cliente",
    ),
    tables=("c_invoice", "c_bpartner", "c_bpartner_location", "c_salesregion",
            "c_bp_group", "c_doctype", "ad_org", "c_currency"),
))

_reg(Capability(
    id="ventas_cxc",
    agent="ventas",
    query_function="build_overdue_receivables",
    display_name="Cuentas por cobrar vencidas",
    keywords=(
        "cuentas por cobrar", "por cobrar", "cxc",
        "vencido", "vencidos", "vencida", "vencidas",
        "mora", "morosos", "deuda", "deudas",
        "pendiente de cobro", "antigüedad", "antiguedad",
    ),
    tables=("c_invoice", "c_bpartner", "c_bpartner_location", "c_salesregion",
            "c_paymentterm", "c_doctype", "ad_org"),
))

# ─── FINANZAS ─────────────────────────────────────────────────

_reg(Capability(
    id="finanzas_saldos_bancarios",
    agent="finanzas",
    query_function="build_financial_summary",
    display_name="Saldos bancarios y flujo de caja",
    keywords=(
        "saldo bancario", "saldos bancarios", "banco", "bancos",
        "cuenta bancaria", "cuentas bancarias",
        "flujo de caja", "flujo caja", "cash flow",
        "disponibilidad", "liquidez",
        "saldo", "saldos",
    ),
    tables=("c_bankaccount", "c_bank", "c_currency", "ad_org"),
))

_reg(Capability(
    id="finanzas_cxc",
    agent="finanzas",
    query_function="build_overdue_receivables",
    display_name="Cuentas por cobrar (finanzas)",
    keywords=(
        "cuentas por cobrar", "por cobrar", "cxc",
        "cartera", "cartera vencida",
    ),
    tables=("c_invoice", "c_bpartner", "c_paymentterm", "c_doctype", "ad_org"),
))

_reg(Capability(
    id="finanzas_cxp",
    agent="finanzas",
    query_function="build_financial_summary",
    display_name="Cuentas por pagar",
    keywords=(
        "cuentas por pagar", "por pagar", "cxp",
        "deuda proveedores", "deudas", "obligaciones",
        "pagar", "pagos pendientes",
    ),
    tables=("c_invoice", "c_bpartner", "c_paymentterm", "ad_org"),
))

# ─── CONTABILIDAD ─────────────────────────────────────────────

_reg(Capability(
    id="contabilidad_balance",
    agent="contabilidad",
    query_function="build_accounting_summary",
    display_name="Balance general / Estado de resultados",
    keywords=(
        "balance general", "balance", "estado de resultados",
        "resultado", "resultados", "pérdidas y ganancias", "perdidas y ganancias",
        "activo", "activos", "pasivo", "pasivos", "patrimonio",
        "ingresos contables", "gastos contables", "egresos contables",
        "utilidad", "pérdida", "perdida",
        "situación financiera", "situacion financiera",
    ),
    tables=("fact_acct", "c_elementvalue"),
))

_reg(Capability(
    id="contabilidad_cuenta",
    agent="contabilidad",
    query_function="build_account_detail",
    display_name="Detalle de cuenta contable",
    keywords=(
        "cuenta contable", "cuentas contables", "plan de cuentas",
        "libro mayor", "mayor", "libro diario", "diario",
        "asiento", "asientos", "movimiento contable", "movimientos contables",
        "partida", "partidas",
        "debe", "haber", "débito", "debito", "crédito", "credito",
        # Account code patterns
        "1.01", "1.02", "1.03", "2.01", "2.02", "3.01",
        "4.01", "5.01", "6.01",
    ),
    tables=("c_elementvalue", "fact_acct", "c_currency"),
))

# ─── RRHH ─────────────────────────────────────────────────────

_reg(Capability(
    id="rrhh_empleados",
    agent="rrhh",
    query_function="build_employee_summary",
    display_name="Plantilla de empleados",
    keywords=(
        "empleado", "empleados", "trabajador", "trabajadores",
        "plantilla", "personal", "headcount",
        "activos", "inactivos", "cuántos empleados", "cuantos empleados",
        "recurso humano", "recursos humanos",
    ),
    tables=("hr_employee", "ad_org", "c_bpartner"),
))

_reg(Capability(
    id="rrhh_lista_empleados",
    agent="rrhh",
    query_function="build_employee_list",
    display_name="Lista de empleados por cargo/departamento",
    keywords=(
        "lista de empleados", "listado de empleados",
        "cargo", "cargos", "puesto", "puestos",
        "departamento", "departamentos",
        "quién trabaja", "quien trabaja", "quiénes trabajan", "quienes trabajan",
        "buscar empleado", "nombre del empleado",
    ),
    tables=("hr_employee", "c_bpartner", "ad_org", "hr_department", "hr_job"),
))

_reg(Capability(
    id="rrhh_cumpleanos",
    agent="rrhh",
    query_function="build_birthday_list",
    display_name="Cumpleañeros del mes",
    keywords=(
        "cumpleaños", "cumpleanos", "cumpleañero", "cumpleanero",
        "cumpleañeros", "cumpleaneros",
        "nacido", "nacidos", "nacimiento", "fecha de nacimiento",
        "nació en", "nacio en", "nacieron en",
        "aniversario",
    ),
    tables=("hr_employee", "c_bpartner", "ad_org", "hr_department", "hr_job"),
))

_reg(Capability(
    id="rrhh_nomina",
    agent="rrhh",
    query_function="build_payroll_summary",
    display_name="Nómina y conceptos de pago",
    keywords=(
        "nómina", "nomina", "nóminas", "nominas",
        "salario", "salarios", "sueldo", "sueldos",
        "concepto de nómina", "conceptos de nomina",
        "pago de nómina", "pagos de nomina",
        "bono", "bonos", "bonificación", "bonificacion",
        "asignación", "asignacion", "deducción", "deduccion",
        "vacaciones", "utilidades", "prestaciones",
        "aguinaldo", "liquidación", "liquidacion",
    ),
    tables=("hr_process", "hr_movement", "hr_payroll", "hr_concept", "ad_org"),
))

_reg(Capability(
    id="rrhh_ausentismo",
    agent="rrhh",
    query_function="build_attendance_summary",
    display_name="Ausentismo y asistencia",
    keywords=(
        "ausentismo", "ausencia", "ausencias",
        "inasistencia", "inasistencias", "falta", "faltas",
        "asistencia", "permiso", "permisos", "reposo", "reposos",
        "incapacidad", "licencia",
    ),
    tables=("hr_movement", "hr_process", "hr_concept", "ad_org"),
))

_reg(Capability(
    id="rrhh_rotacion",
    agent="rrhh",
    query_function="build_turnover_summary",
    display_name="Rotación de personal",
    keywords=(
        "rotación", "rotacion", "desincorporado", "desincorporados",
        "retiro", "retiros", "despido", "despidos", "renuncia", "renuncias",
        "baja", "bajas", "egreso de personal", "egresos de personal",
        "cesante", "cesantes",
    ),
    tables=("hr_employee", "ad_org", "c_bpartner"),
))

# ─── PRODUCCION ───────────────────────────────────────────────

_reg(Capability(
    id="produccion_runs",
    agent="produccion",
    query_function="build_production_runs",
    display_name="Producciones reales",
    keywords=(
        "producción", "produccion", "producido", "producidos",
        "producciones", "fabricó", "fabricado", "fabricar",
        "fabricación", "fabricacion", "manufactura",
        "cantidad producida", "volumen de producción",
        "producto terminado", "productos terminados",
        "insumo consumido", "insumos consumidos",
    ),
    tables=("m_production", "m_productionline", "m_product", "ad_org"),
))

_reg(Capability(
    id="produccion_resumen",
    agent="produccion",
    query_function="build_production_summary",
    display_name="Movimientos de inventario",
    keywords=(
        "recepción", "recepcion", "recepciones",
        "despacho", "despachos",
        "movimiento de inventario", "movimientos de inventario",
        "desperdicios", "desperdicio", "merma", "mermas",
    ),
    tables=("m_inout", "m_inoutline", "m_product", "ad_org"),
))

_reg(Capability(
    id="produccion_ordenes",
    agent="produccion",
    query_function="build_production_orders",
    display_name="Documentos de movimiento",
    keywords=(
        "documento", "documentos de movimiento",
        "últimos movimientos", "movimientos recientes",
    ),
    tables=("m_inout", "ad_org", "c_bpartner"),
))

_reg(Capability(
    id="produccion_bom",
    agent="produccion",
    query_function="build_bom_info",
    display_name="Recetas / BOMs",
    keywords=(
        "receta", "recetas", "bom", "bill of material",
        "ingrediente", "ingredientes", "componente", "componentes",
        "fórmula", "formula", "composición", "composicion",
        "qué lleva", "de qué está hecho", "cómo se hace",
    ),
    tables=("pp_product_bom", "pp_product_bomline", "m_product", "c_uom"),
))

_reg(Capability(
    id="produccion_movimientos_almacen",
    agent="produccion",
    query_function="build_warehouse_movements",
    display_name="Movimientos entre almacenes",
    keywords=(
        "traslado", "traslados", "transferencia", "transferencias",
        "movimiento interno", "movimientos internos",
        "entre almacenes", "entre silos",
        "mover", "trasladar",
    ),
    tables=("m_movement", "m_movementline", "m_locator", "m_warehouse", "m_product"),
))

_reg(Capability(
    id="produccion_inventario",
    agent="produccion",
    query_function="build_inventory_stock",
    display_name="Inventario / Stock actual",
    keywords=(
        "inventario", "stock", "existencia", "existencias",
        "almacén", "almacen", "bodega",
        "disponible", "disponibilidad",
        "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
    ),
    tables=("m_storageonhand", "m_locator", "m_warehouse", "ad_org",
            "m_product", "m_product_category", "c_uom"),
))

# ─── COMPRAS INSUMOS ──────────────────────────────────────────

_reg(Capability(
    id="compras_insumos_facturas",
    agent="compras_insumos",
    query_function="build_supply_purchases",
    display_name="Facturas de compra de insumos",
    keywords=(
        "compras de insumos", "compra de insumos",
        "factura de compra", "facturas de compra",
        "compras a proveedores", "compra a proveedor",
        "gasto en insumos", "gastos en insumos",
        "insumo", "insumos", "materia prima",
        "proveedor", "proveedores",
    ),
    tables=("c_invoice", "c_invoiceline", "c_bpartner", "m_product", "c_currency"),
))

_reg(Capability(
    id="compras_insumos_historial",
    agent="compras_insumos",
    query_function="build_product_purchase_history",
    display_name="Historial de compras por producto",
    keywords=(
        "historial de compras", "histórico de compras", "historico de compras",
        "compras de", "compras del producto",
        "precio de compra", "precios de compra",
        "cuánto compramos", "cuanto compramos",
    ),
    tables=("c_invoice", "c_invoiceline", "m_product", "c_bpartner"),
))

_reg(Capability(
    id="compras_insumos_oc_pendientes",
    agent="compras_insumos",
    query_function="build_pending_purchase_orders",
    display_name="Órdenes de compra pendientes",
    keywords=(
        "orden de compra", "órdenes de compra", "ordenes de compra",
        "oc pendiente", "oc pendientes",
        "pedido pendiente", "pedidos pendientes",
        "por recibir", "sin recibir",
    ),
    tables=("c_order", "c_orderline", "c_bpartner", "ad_org", "m_product"),
))

_reg(Capability(
    id="compras_insumos_comparacion",
    agent="compras_insumos",
    query_function="build_supplier_price_comparison",
    display_name="Comparación de precios entre proveedores",
    keywords=(
        "comparar precios", "comparación de precios", "comparacion de precios",
        "mejor precio", "precio más bajo", "precio mas bajo",
        "proveedor más barato", "proveedor mas barato",
        "cotización", "cotizacion",
    ),
    tables=("c_invoice", "c_invoiceline", "m_product", "c_bpartner"),
))

_reg(Capability(
    id="compras_insumos_estado_pago",
    agent="compras_insumos",
    query_function="build_purchase_payment_status",
    display_name="Estado de pago de facturas de compra",
    keywords=(
        "estado de pago", "pagadas", "pendientes de pago",
        "facturas pagadas", "facturas pendientes",
        "vencidas", "por vencer",
    ),
    tables=("c_invoice", "c_bpartner", "c_paymentterm"),
))

_reg(Capability(
    id="compras_insumos_inventario",
    agent="compras_insumos",
    query_function="build_inventory_stock",
    display_name="Inventario de insumos",
    keywords=(
        "inventario de insumos", "stock de insumos",
        "existencia de insumo",
    ),
    tables=("m_storageonhand", "m_locator", "m_warehouse", "ad_org",
            "m_product", "m_product_category", "c_uom"),
))

# ─── COMPRAS PRODUCTORES ─────────────────────────────────────

_reg(Capability(
    id="compras_productores_compras",
    agent="compras_productores",
    query_function="build_producer_purchases",
    display_name="Compras a productores agrícolas",
    keywords=(
        "compras a productores", "compra a productor",
        "arroz", "maíz", "maiz", "maíz acondicionado", "maiz acondicionado",
        "maíz seco", "maiz seco",
        "recepción de arroz", "recepcion de arroz",
        "recepción de maíz", "recepcion de maiz",
        "recepción de maiz", "recepcion de maíz",
        "cosecha", "acopio", "buque", "narvi",
        "productor", "productores", "agricultor", "agricultores",
    ),
    tables=("c_order", "c_orderline", "m_product", "c_bpartner"),
))

_reg(Capability(
    id="compras_productores_registrados",
    agent="compras_productores",
    query_function="build_registered_producers",
    display_name="Productores registrados",
    keywords=(
        "productores registrados", "lista de productores",
        "listado de productores", "productores activos",
        "cuántos productores", "cuantos productores",
    ),
    tables=("c_bpartner", "c_bpartner_location"),
))

_reg(Capability(
    id="compras_productores_pagos_pendientes",
    agent="compras_productores",
    query_function="build_producer_pending_payments",
    display_name="Pagos pendientes a productores",
    keywords=(
        "pagos pendientes productores", "deuda productores",
        "deuda de productor", "deuda de productores", "deuda productor",
        "pendiente de pago a productor", "le debemos a productores",
        "pagar a productor", "pagar a productores",
        "pago a productor", "pagos a productor",
        "por pagar a productor", "por pagar a productores",
        "deuda de maiz", "deuda de maíz", "deuda de arroz",
        "pagar de maiz", "pagar de maíz", "pagar de arroz",
        "monto a pagar de maiz", "monto a pagar de maíz",
        "monto a pagar de arroz",
        "por pagar de maiz", "por pagar de maíz", "por pagar de arroz",
    ),
    tables=("c_invoice", "c_bpartner", "c_invoiceline", "m_product"),
))

_reg(Capability(
    id="compras_productores_precios",
    agent="compras_productores",
    query_function="build_producer_price_analysis",
    display_name="Análisis de precios agrícolas",
    keywords=(
        "precio del arroz", "precio del maíz", "precio del maiz",
        "precio pagado", "precios pagados",
        "precio por kilo", "precio por tonelada",
        "evolución de precios", "evolucion de precios",
    ),
    tables=("c_order", "c_orderline", "m_product"),
))


# ──────────────────────────────────────────────────────────────
# iDEMPIERE WINDOW → CAPABILITY MAPPING
#
# Maps iDempiere window names to the bot capabilities they grant.
# This is how we translate "user has access to window X" → "user
# can run query Y".
#
# The mapping uses window name patterns (lowercased substring match).
# ──────────────────────────────────────────────────────────────

# (window_name_pattern, list of capability IDs granted)
WINDOW_CAPABILITY_MAP: list[tuple[str, list[str]]] = [
    # ─── Ventas ───
    ("factura (cliente)", [
        "ventas_facturacion", "ventas_top_clientes", "ventas_cxc",
    ]),
    ("customer invoice", [
        "ventas_facturacion", "ventas_top_clientes", "ventas_cxc",
    ]),
    ("cobros", ["ventas_cobranza"]),
    ("recibo de cobro", ["ventas_cobranza"]),
    ("payment receipt", ["ventas_cobranza"]),
    ("socio del negocio", [
        "ventas_top_clientes", "compras_insumos_facturas",
        "compras_productores_registrados",
    ]),
    ("business partner", [
        "ventas_top_clientes", "compras_insumos_facturas",
        "compras_productores_registrados",
    ]),

    # ─── Finanzas ───
    ("cuenta bancaria", ["finanzas_saldos_bancarios"]),
    ("bank account", ["finanzas_saldos_bancarios"]),
    ("banco", ["finanzas_saldos_bancarios"]),
    ("estado de cuenta", ["finanzas_saldos_bancarios"]),
    ("payment", ["ventas_cobranza", "finanzas_cxc"]),
    ("pago", ["finanzas_cxp"]),

    # ─── Contabilidad ───
    ("esquema contable", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("accounting schema", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("diario contable", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("gl journal", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("asiento", ["contabilidad_balance", "contabilidad_cuenta"]),
    ("cuenta contable", ["contabilidad_cuenta"]),
    ("element value", ["contabilidad_cuenta"]),
    ("plan de cuentas", ["contabilidad_cuenta"]),
    ("informe financiero", ["contabilidad_balance"]),
    ("financial report", ["contabilidad_balance"]),
    ("balance", ["contabilidad_balance"]),
    ("fact_acct", ["contabilidad_balance", "contabilidad_cuenta"]),

    # ─── RRHH ───
    ("empleado", ["rrhh_empleados", "rrhh_lista_empleados", "rrhh_cumpleanos",
                   "rrhh_rotacion"]),
    ("employee", ["rrhh_empleados", "rrhh_lista_empleados", "rrhh_cumpleanos",
                   "rrhh_rotacion"]),
    ("nómina", ["rrhh_nomina", "rrhh_ausentismo"]),
    ("nomina", ["rrhh_nomina", "rrhh_ausentismo"]),
    ("payroll", ["rrhh_nomina", "rrhh_ausentismo"]),
    ("proceso de nómina", ["rrhh_nomina"]),
    ("concepto de nómina", ["rrhh_nomina"]),
    ("payroll concept", ["rrhh_nomina"]),
    ("departamento rrhh", ["rrhh_lista_empleados"]),
    ("hr department", ["rrhh_lista_empleados"]),
    ("puesto", ["rrhh_lista_empleados"]),
    ("hr job", ["rrhh_lista_empleados"]),

    # ─── Producción ───
    ("producción", ["produccion_runs", "produccion_resumen"]),
    ("produccion", ["produccion_runs", "produccion_resumen"]),
    ("production", ["produccion_runs", "produccion_resumen"]),
    ("fabricación", ["produccion_runs"]),
    ("manufactura", ["produccion_runs"]),
    ("producto terminado", ["produccion_runs"]),
    ("receta", ["produccion_bom"]),
    ("bom", ["produccion_bom"]),
    ("ingrediente", ["produccion_bom"]),
    ("componente", ["produccion_bom"]),
    ("traslado", ["produccion_movimientos_almacen"]),
    ("transferencia", ["produccion_movimientos_almacen"]),
    ("movimiento interno", ["produccion_movimientos_almacen"]),
    ("entre almacenes", ["produccion_movimientos_almacen"]),
    ("entre silos", ["produccion_movimientos_almacen"]),
    ("inventario", ["produccion_inventario", "compras_insumos_inventario"]),
    ("inventory", ["produccion_inventario", "compras_insumos_inventario"]),
    ("almacén", ["produccion_inventario"]),
    ("almacen", ["produccion_inventario"]),
    ("warehouse", ["produccion_inventario"]),
    ("movimiento de inventario", ["produccion_resumen"]),
    ("inventory move", ["produccion_resumen"]),
    ("recibo de material", ["produccion_resumen"]),
    ("material receipt", ["produccion_resumen"]),
    ("entrega", ["produccion_resumen"]),
    ("shipment", ["produccion_resumen"]),

    # ─── Compras Insumos ───
    ("factura (proveedor)", [
        "compras_insumos_facturas", "compras_insumos_historial",
        "compras_insumos_comparacion", "compras_insumos_estado_pago",
    ]),
    ("vendor invoice", [
        "compras_insumos_facturas", "compras_insumos_historial",
        "compras_insumos_comparacion", "compras_insumos_estado_pago",
    ]),
    ("orden de compra", [
        "compras_insumos_oc_pendientes", "compras_productores_compras",
    ]),
    ("purchase order", [
        "compras_insumos_oc_pendientes", "compras_productores_compras",
    ]),

    # ─── Compras Productores ───
    ("recepción", ["compras_productores_compras"]),
    ("recepcion", ["compras_productores_compras"]),
    ("agricultor", ["compras_productores_registrados",
                     "compras_productores_compras"]),
    ("productor", ["compras_productores_registrados",
                    "compras_productores_compras",
                    "compras_productores_pagos_pendientes"]),
]

# ──────────────────────────────────────────────────────────────
# TABLE → CAPABILITY REVERSE MAPPING
# If we can't match by window name, we can match by the tables
# the window's tabs reference (ad_tab.ad_table_id → ad_table.tablename)
# ──────────────────────────────────────────────────────────────

TABLE_CAPABILITY_MAP: dict[str, list[str]] = {}
for _cap in CAPABILITIES.values():
    for _table in _cap.tables:
        TABLE_CAPABILITY_MAP.setdefault(_table.lower(), []).append(_cap.id)


# ──────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────

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
