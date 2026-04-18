"""Capability registry — every bot query capability grouped by agent.

Each capability declares its triggering keywords and the iDempiere tables
it reads, so that role sync can map a user's iDempiere window/table access
to bot capabilities.
"""

from .types import Capability


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
    id="produccion_resumen",
    agent="produccion",
    query_function="build_production_summary",
    display_name="Resumen de producción",
    keywords=(
        "producción", "produccion", "producido", "producidos",
        "desperdicios", "desperdicio", "merma", "mermas",
        "rendimiento", "eficiencia",
        "cantidad producida", "volumen de producción",
    ),
    tables=("m_inout", "m_inoutline", "m_product", "ad_org"),
))

_reg(Capability(
    id="produccion_ordenes",
    agent="produccion",
    query_function="build_production_orders",
    display_name="Órdenes de producción",
    keywords=(
        "orden de producción", "ordenes de produccion",
        "órdenes de producción", "orden producción",
        "op", "orden de trabajo",
    ),
    tables=("m_inout", "ad_org", "c_bpartner"),
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
