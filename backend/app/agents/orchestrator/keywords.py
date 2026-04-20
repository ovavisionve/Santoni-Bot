"""Keyword rules, follow-up patterns, and domain constants for routing."""

import re

# ──────────────────────────────────────────────────────────────────
# Keyword-based classifier – instant routing, no LLM call needed
# ──────────────────────────────────────────────────────────────────

# Order matters: more specific patterns first, broader ones last.
# Each entry: (agent_name, [keyword_patterns])
# A pattern matches if ANY keyword in it appears in the lowercased message.
_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    # Compras a productores (before generic "compra")
    ("compras_productores", [
        "productor", "productores", "arroz paddy", "maiz blanco",
        "arroz acondicionado", "maiz acondicionado", "maíz acondicionado",
        "guia de compra", "guias de compra",
        "compra de arroz", "compra de maiz", "compra de maíz",
        # AGRI-103 (09/Abr/2026): variantes plurales que faltaban — los keywords
        # solo cubrían "compra de" pero los usuarios escriben "compras de" (con S).
        "compras de arroz", "compras de maiz", "compras de maíz",
        "compras a productor", "precio del arroz", "precio del maiz",
        "precio del maíz", "tonelada", "kilogramo",
        "recepcion de maiz", "recepción de maíz", "recepcion de arroz", "recepción de arroz",
        "buque", "narvi", "maiz seco", "maíz seco",
        # Debt/payment queries related to agricultural products and producers
        "pagar de maiz", "pagar de maíz", "pagar de arroz",
        "deuda de maiz", "deuda de maíz", "deuda de arroz",
        "deuda de productor", "deuda de productores", "deuda productor",
        "pago a productor", "pago a productores", "pagos a productor",
        "pagos pendientes a productor", "pagos pendientes a productores",
        "monto de maiz", "monto de maíz", "monto de arroz",
        "monto a pagar de maiz", "monto a pagar de maíz",
        "por pagar de maiz", "por pagar de maíz", "por pagar de arroz",
        "por pagar a productor", "por pagar a productores",
    ]),
    # Producción — BEFORE compras_insumos to catch "materia prima", "producto terminado"
    # and "producción"-related keywords before they fall through to inventory/compras
    ("produccion", [
        "produccion", "producción", "producir", "produjo", "producido",
        "producimos", "produjeron",
        "fabricar", "fabricó", "fabricado", "fabricamos", "fabricaron",
        "manufactura",
        "planta", "línea de producción", "linea de produccion",
        "eficiencia", "oee", "desperdicio", "merma", "scrap",
        "mantenimiento", "turno", "turnos", "lote", "lotes",
        "orden de produccion", "orden de producción",
        "ordenes de produccion", "órdenes de producción",
        # COMP-101 (09/Abr/2026): "empaque" removido porque es ambiguo en
        # Santoni — los usuarios usan "empaque" para referirse a materiales de
        # empaque (cartón, polietileno, etc.) que son INSUMOS, no producto
        # terminado. Si en el futuro se necesita matchear "empaque" como etapa
        # de producción, usar "etapa de empaque" o "línea de empaque".
        "producto terminado", "envasado",
        "recepcion de materia", "recepción de materia",
        "despacho de producto", "despachos",
        "cuanto se produjo", "cuánto se produjo",
        "arroz blanco", "harina de maiz", "harina de maíz",
        "materia prima",
    ]),
    # Compras de insumos — after produccion (which catches "materia prima", "producto terminado")
    # and before ventas (to prevent "inventario" matching "venta" substring)
    ("compras_insumos", [
        "insumo", "proveedor", "proveedores", "orden de compra",
        "ordenes de compra", "inventario de material",
        "inventario de insumo", "inventario de repuesto",
        "inventario", "material",
        "compra de insumo", "compras insumo", "suministro",
        "tiempo de entrega", "stock", "existencia", "existencias",
        "almacén", "almacen", "almacenes", "bodega",
        "disponible en almacen", "disponible en almacén",
        "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
        "historial de compra", "historial de compras",
        "compras de", "compra del producto",
        # "compra" como substring cubre "compras", "comprador", etc.
        # Variantes verbales explícitas para formas con tilde:
        "compró", "compramos", "compraron",
        "compra",
    ]),
    # Contabilidad — BEFORE ventas/finanzas to catch accounting terms first
    ("contabilidad", [
        "contab", "contabilidad",
        "balance general", "balance de comprobacion", "balance de comprobación",
        "estado de resultado", "libro diario", "libro mayor",
        "islr",
        "activo fijo", "activos fijos", "depreciacion", "depreciación",
        "asiento contable", "plan de cuenta", "plan de cuentas", "partida",
        # Account-specific (saldos de cuentas, no bancarios)
        "cuenta contable", "cuentas contables",
        "cuentas de ingreso", "cuenta de ingreso",
        "cuentas de gasto", "cuenta de gasto",
        "cuentas de egreso", "cuenta de egreso",
        "cuentas de activo", "cuentas de pasivo",
        "saldo de la cuenta", "saldo de cuenta", "saldo contable",
        "balance de la cuenta", "mayor de la cuenta",
        "periodo contable", "período contable",
        "débito", "debe y haber",
        "cierre contable", "cierre de mes", "cierre de año",
        "conciliacion", "conciliación", "conciliacion bancaria",
        "balanza de comprobacion", "balanza de comprobación", "balanza",
        "patrimonio", "capital social",
        "ingresos por venta", "ingreso por venta",
        "utilidad bruta", "utilidad neta", "ganancia neta",
        "pérdida", "perdida",
    ]),
    # Finanzas — BEFORE ventas so "cuentas por cobrar" routes here
    ("finanzas", [
        "finanza", "financiero", "financiera", "flujo de caja",
        "banco", "bancos", "bancaria", "bancario", "bancarias", "bancarios",
        "saldo bancario", "saldo de banco",
        "cuenta por cobrar", "cuentas por cobrar", "por cobrar",
        "cuenta por pagar", "cuentas por pagar", "por pagar",
        "presupuesto", "rentabilidad", "liquidez",
        "estado de flujo", "indicador financiero",
        "prestamo", "préstamo", "prestamos", "préstamos",
        "cuota", "cuotas",
        "disponibilidad bancaria", "disponibilidad",
    ]),
    # Ventas – broad keywords
    ("ventas", [
        "venta", "ventas", "vendedor", "vendedores", "cliente",
        "clientes", "factura", "facturación", "facturacion",
        # VENT-200 (14/Abr/2026): variantes verbales que no matcheaban porque
        # "factura" no es substring de "facturó" (la tilde rompe el substring).
        "facturó", "facturar", "facturaron", "facturamos",
        "vendió", "vender", "vendieron", "vendimos",
        "cobró", "cobraron", "cobramos",
        "cobranza", "cobro", "cobrar", "recaudacion", "recaudación",
        "zona", "zonas", "ranking", "pareto", "top clientes",
        "top 10", "top 20", "top 5", "mejores clientes",
        "metas de venta", "meta de venta", "cotizacion", "cotización",
        "moroso", "morosos", "deuda", "deudas", "vencido", "vencida",
        "pendiente de cobro",
        "nota de credito", "notas de credito", "nota de crédito", "notas de crédito",
        "producto más vendido", "productos más vendidos",
        "top producto", "ventas por producto", "ventas por categoria",
        "ventas por categoría", "sku",
        "orden de venta", "ordenes de venta", "órdenes de venta",
        "pedido de venta", "pedidos de venta", "pipeline de venta",
        "ventas por sucursal", "sucursal",
        "tasa de cambio", "tipo de cambio",
        "impuesto", "iva", "retencion", "retención",
        "base imponible", "exento", "gravado",
    ]),
    # RRHH
    ("rrhh", [
        "nomina", "nómina", "empleado", "empleados", "personal",
        "trabajador", "trabajadores", "plantilla",
        "obrero", "obreros", "gerente", "gerentes",
        "analista", "supervisor", "supervisora", "coordinador", "coordinadora",
        "operario", "operarios", "operador", "chofer", "choferes",
        "cargo", "cargos", "puesto", "puestos",
        "vacacion", "vacación", "vacaciones", "asistencia", "inasistencia",
        "ausentismo", "ausentimos", "ausencia", "ausencias", "falta", "faltas",
        "evaluacion", "evaluación",
        "cumpleaño", "cumpleaños", "cumpleañero", "cumpleañeros",
        # Variantes verbales de "cumplir años" — RRHH-101 (09/Abr/2026):
        # los keywords sustantivos no matcheaban "cumplen años en abril" porque
        # el matching es substring y "cumpleaños" != "cumple años" / "cumplen años".
        "cumple año", "cumple años", "cumplen año", "cumplen años",
        "cumplir año", "cumplir años", "cumplo año", "cumplo años",
        "nacido", "nacidos", "nacimiento", "fecha de nacimiento",
        "salario", "sueldo", "sueldos", "salarios",
        "recurso humano", "recursos humanos",
        "rrhh", "talento humano",
        "contrato", "contratos", "contratacion", "contratación",
        "ingreso", "ingresos", "ingresaron", "ingresó",
        "liquidacion", "liquidación",
        "prestacion", "prestación", "prestaciones",
        "renuncia", "renunciado", "renuncias", "renunció", "renunciaron",
        "despido", "despidos", "despedido", "despidió", "despidieron",
        "bono", "bonos", "bonificacion", "bonificación",
        "permiso", "permisos", "reposo", "reposos",
        "incapacidad", "incapacidades",
        "rotacion", "rotación",
        "capacitacion", "capacitación",
    ]),
]

# Greetings / general patterns
_GENERAL_PATTERNS = [
    "hola", "buenos dias", "buenos días", "buenas tardes", "buenas noches",
    "gracias", "ayuda", "que puedes hacer", "qué puedes hacer",
    "quien eres", "quién eres", "como funciona", "cómo funciona",
]

# ── Pre-routing rules ───────────────────────────────────────────────────
# Frases de ALTA ESPECIFICIDAD que se evalúan ANTES del loop genérico de
# _KEYWORD_RULES. Resuelven conflictos donde un keyword genérico de un
# agente (ej "proveedores" en compras_insumos) captura preguntas que
# realmente pertenecen a otro agente (ej "cuentas por pagar a proveedores"
# → finanzas). La frase larga es más específica y se evalúa primero.
#
# FIN-100 (09/Abr/2026): "cuentas por pagar a proveedores" iba a
#   compras_insumos por "proveedores". Pero "cuentas por pagar" es
#   terminología financiera inequívoca.
# FAIL routing_produccion_existencia (09/Abr/2026): "existencia del
#   producto" iba a compras_insumos por "existencia". Pero "existencia
#   del producto [código]" es inventario/produccion.
_PRE_ROUTING_RULES: list[tuple[str, list[str]]] = [
    ("finanzas", [
        "cuentas por pagar a proveedor", "cuentas por pagar a proveedores",
        "saldo de cuentas por pagar", "saldo de las cuentas por pagar",
        "cuentas por cobrar de", "cuentas por cobrar para",
    ]),
    ("produccion", [
        "existencia del producto", "existencia de producto",
        "existencias del producto", "stock del producto",
        "cantidad del producto", "cantidad de producto",
        "en existencia del producto",
    ]),
]


def _has_account_code(msg: str) -> bool:
    """Detect accounting codes like 1.01.04.02, 2.01.01.10 in the message."""
    return bool(re.search(r'\d\.\d{2}\.\d{2}', msg))


# VENT-100 / ORCH-101 (14/Abr/2026): Patterns that indicate a follow-up
# message (e.g., "en dólares", "dame por zona", "ok muéstrame en febrero").
# When a short message (< 40 chars) matches one of these patterns AND we
# have a last_agent, route to last_agent directly instead of re-classifying
# with keywords — because these messages modify the previous query, not
# start a new one.
_FOLLOWUP_PATTERNS = [
    # Currency switch
    "en dólar", "en dolár", "en dolares", "en dólares", "en usd",
    "en bolívar", "en bolivar", "en bolívares", "en bolivares", "en ves",
    "en moneda", "moneda dol", "moneda usd", "moneda ves", "en divisas",
    # Temporal switch
    "dame en ", "ok dame", "damelo en", "dámelo en", "muéstrame en",
    "mustrame en", "ahora en ", "y en ", "pero en ",
    "del mes", "del año", "este mes", "este año", "mes pasado", "año pasado",
    # Grouping/filter switch
    "por zona", "por producto", "por vendedor", "por mes", "por año",
    "por organización", "por organizacion", "por org", "por moneda",
    "por departamento", "por proveedor", "por cliente",
    # Confirmations/refinements
    "sí, dame", "si, dame", "ok, dame", "dale", "eso mismo",
    "más detalle", "mas detalle", "detallado", "desglosado",
    "y las notas", "y los totales",
]


# ──────────────────────────────────────────────────────────────────
# SQL Direct gate — decide si una pregunta entra a SQL Directo o se
# manda al flujo de agentes clásicos. Debe correr ANTES del routing
# por keywords. Si retorna True, intentar SQL Directo primero.
# ──────────────────────────────────────────────────────────────────

# Keywords de dominio (indicadores de que es pregunta de datos) derivados
# de los _KEYWORD_RULES. Se computan una sola vez al importar el módulo.
# Mantener este set sincronizado con _KEYWORD_RULES era frágil antes
# (lista hardcoded de ~11 fragmentos). Ahora se deriva automáticamente.
_DOMAIN_KEYWORD_FRAGMENTS: frozenset[str] = frozenset({
    # Fragmentos cortos (3-6 chars) que son prefijo/substring de los
    # keywords más comunes. Usamos fragmentos en vez de keywords completos
    # para atrapar variantes: "cuánt" matchea "cuántos"/"cuántas"/"cuánto".
    "cuánt", "cuant", "total", "saldo", "emplea", "venta", "vended",
    "compr", "produc", "factur", "cobr", "banco", "nomina", "nómina",
    "empaque", "inventa", "stock", "deuda", "vencid", "pendient",
    "arroz", "maiz", "maíz", "productor", "proveedor", "cliente",
    "cumpl", "vacacion", "sueldo", "salario", "pago", "movimiento",
})

