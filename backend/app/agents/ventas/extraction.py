"""Keyword/entity extraction for the ventas agent.

Functions here are stateless and operate on the raw user message.
"""

import re

from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    detect_currency,
)


ZONES = [
    "portuguesa", "barinas", "lara", "carabobo", "aragua", "zulia",
    "maracaibo", "falcon", "margarita", "trujillo", "merida", "mérida",
    "tachira", "táchira", "guanare", "cabimas", "valencia", "caracas",
    "oriente", "santa barbara",
]

VENDEDORES = ["carlos matias", "lenny silva", "yuleidys gutierrez"]

# Cada entrada es (keyword, display_name, filter_patterns).
# - keyword: lo que buscamos en el mensaje del usuario (match por substring)
# - display_name: etiqueta legible para los títulos en la respuesta
# - filter_patterns: lista de patrones ILIKE que se pasan a
#   `_add_org_name_filter` (combinados con OR).
#
# IMPORTANTE: solo mapeamos nombres EXPLÍCITOS. "inproa" solo (sin
# "santoni", sin "maiz") NO aparece aquí porque es ambiguo — puede
# referirse a INPROA SANTONI, InproMaiz o AGROINPROA. En ese caso el
# agente pide clarificación al usuario en vez de adivinar.
#
# El orden importa: keywords más específicos (más largos) antes que
# los cortos, porque `_extract_org_patterns` itera longest-first.
ORG_MAP = [
    ("inproa santoni", "INPROA SANTONI", ["inproa santoni"]),
    ("inversiones aga", "INVERSIONES AGA", ["inversiones aga"]),
    ("santoni service", "Santoni Service", ["santoni service"]),
    ("aga agrícola", "AGA AGRICOLA", ["aga agricola"]),
    ("aga agricola", "AGA AGRICOLA", ["aga agricola"]),
    ("agropecuaria", "AGROPECUARIA", ["agropecuaria"]),
    ("agroinproa", "AGROINPROA", ["agroinproa"]),
    ("inpromaiz", "InproMaiz", ["inpromaiz"]),
    ("inpro maiz", "InproMaiz", ["inpromaiz"]),
]

# Keywords que, cuando aparecen SIN un calificador más específico,
# se consideran ambiguos y disparan la clarificación al usuario.
AMBIGUOUS_ORG_KEYWORDS = ("inproa",)

QUERY_TYPES = {
    "vendedor": ["vendedor", "vendedores", "vendedora", "vendedoras"],
    "top": ["top", "mejor", "ranking", "pareto", "principales", "cliente", "clientes"],
    "cobranza": ["cobra", "cobro", "cobró", "cobrado", "recauda", "recaudó", "pago", "cobranza"],
    "vencidas": ["atrasa", "vencid", "pendiente", "deuda", "mora"],
    "ventas": ["venta", "factur", "ingreso", "volumen"],
    "region": ["region", "región", "regiones"],
    "producto": [
        "producto", "productos", "articulo", "artículo",
        "sku", "categoria de producto", "categoría de producto",
        "que se vende", "qué se vende", "más vendido", "mas vendido",
        "top producto", "ranking de producto",
        "nota de credito", "notas de credito", "nota de crédito", "notas de crédito",
    ],
    "ordenes": [
        "orden de venta", "ordenes de venta", "órdenes de venta",
        "pedido", "pedidos", "orden pendiente", "ordenes pendientes",
        "pipeline",
    ],
    "impuestos": [
        "impuesto", "iva", "retencion", "retención", "retenciones",
        "islr", "base imponible", "fiscal", "tributario",
    ],
    "sucursal": [
        "sucursal", "sucursales", "proyecto", "sede", "sedes",
    ],
    "tasa": [
        "tasa de cambio", "tasa", "tipo de cambio", "cambio del dolar",
        "cambio del dólar", "dolar oficial", "dólar oficial",
    ],
}

PRODUCT_KEYWORDS = [
    "harina", "arroz", "maiz", "maíz", "aceite", "sal",
    "avena", "azúcar", "azucar", "pasta",
]


def extract_zona(msg: str) -> str | None:
    msg_lower = msg.lower()
    for z in ZONES:
        if z in msg_lower:
            return z.title()
    return None


def extract_vendedor(msg: str) -> str | None:
    msg_lower = msg.lower()
    for v in VENDEDORES:
        if v in msg_lower:
            return v.title()
    return None


def match_orgs(msg: str) -> tuple[list[str], list[str]]:
    """Encuentra TODAS las orgs mencionadas en el mensaje.

    Itera los keywords más largos primero y consume (masking) cada match
    para evitar doble-conteo (ej: "inproa santoni" no debe volver a
    disparar un match por "inproa"/"santoni" sueltos).
    """
    masked = msg.lower()
    displays: list[str] = []
    patterns: list[str] = []
    sorted_map = sorted(ORG_MAP, key=lambda x: -len(x[0]))
    for kw, display, pats in sorted_map:
        if kw in masked:
            masked = masked.replace(kw, " " * len(kw))
            if display not in displays:
                displays.append(display)
            for p in pats or []:
                if p not in patterns:
                    patterns.append(p)
    return displays, patterns


def extract_org_name(msg: str) -> str | None:
    """Devuelve una etiqueta legible con todas las orgs mencionadas."""
    displays, _ = match_orgs(msg)
    return " + ".join(displays) if displays else None


def extract_org_patterns(msg: str) -> list[str] | None:
    """Devuelve la lista de patrones ILIKE para pasar a `_add_org_name_filter`."""
    _, patterns = match_orgs(msg)
    return patterns or None


def is_ambiguous_org(msg: str) -> bool:
    """True si el mensaje menciona un keyword ambiguo sin calificador específico."""
    displays, _ = match_orgs(msg)
    if displays:
        return False
    msg_lower = msg.lower()
    return any(kw in msg_lower for kw in AMBIGUOUS_ORG_KEYWORDS)


def detect_query_type(msg: str) -> str | None:
    msg_lower = msg.lower()
    for qtype, kws in QUERY_TYPES.items():
        if any(w in msg_lower for w in kws):
            return qtype
    return None


def extract_product_search(msg: str) -> str | None:
    """Extract product name/keyword from the message."""
    msg_lower = msg.lower()
    for kw in PRODUCT_KEYWORDS:
        if kw in msg_lower:
            return kw
    return None


def extract_category_search(msg: str) -> str | None:
    """Extract product category from the message."""
    m = re.search(r'categor[ií]a\s+(?:de\s+)?["\']?([^"\',.]+)', msg, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def extract_context_from_history(history: list[tuple[str, str]]) -> dict:
    """Extract zona, vendedor, org_name, currency, query_type, and temporal context."""
    ctx: dict = {}
    if not history:
        return ctx
    for role, content in reversed(history):
        if role != "user":
            continue
        if "zona" not in ctx:
            z = extract_zona(content)
            if z:
                ctx["zona"] = z
        if "vendedor" not in ctx:
            v = extract_vendedor(content)
            if v:
                ctx["vendedor"] = v
        if "org_name" not in ctx:
            o = extract_org_name(content)
            if o:
                ctx["org_name"] = o
                ctx["org_patterns"] = extract_org_patterns(content)
        if "currency" not in ctx:
            c = detect_currency(content)
            if c:
                ctx["currency"] = c
        if "query_type" not in ctx:
            qt = detect_query_type(content)
            if qt:
                ctx["query_type"] = qt
        if "date_from" not in ctx:
            df, dt = extract_date_range(content)
            if df and dt:
                ctx["date_from"] = df
                ctx["date_to"] = dt
        if "mes" not in ctx and "date_from" not in ctx:
            m, a = extract_month_year(content)
            if m:
                ctx["mes"] = m
                ctx["anio"] = a
        if len(ctx) >= 8:
            break
    return ctx
