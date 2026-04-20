"""Keyword / product / org / currency extraction helpers for compras_insumos."""

import re

from app.agents.date_utils import extract_date_range, extract_month_year


# Currency IDs in Santoni's iDempiere
VES_IDS = [205]
USD_IDS = [1000000, 1000003, 1000006, 1000008, 1000011, 1000013, 1000017]

# Keywords that indicate the user wants USD
USD_KEYWORDS = [
    "dólares", "dolares", "dólar", "dolar", "usd", "dol",
    "en dólares", "en dolares", "en dólar", "en dolar",
    "en usd", "en dol", "moneda dol", "moneda usd",
    "moneda dólar", "moneda dolares",
    # VENT-400 (10/Abr/2026): "divisa/divisas" es sinónimo venezolano
    # común de dólar. esalas lo usó en producción.
    "divisa", "divisas", "en divisa", "en divisas",
]

# Keywords that indicate the user wants VES
VES_KEYWORDS = [
    "bolívares", "bolivares", "bolívar", "bolivar", "ves",
    "en bolívares", "en bolivares", "en ves",
    "moneda ves", "moneda bolivar", "moneda bolívares",
]

GENERAL_KEYWORDS = [
    "resumen", "total", "proveedor", "proveedores", "mensual",
    "principales", "inventario", "stock", "existencia", "almacén",
    "almacen", "todos los insumos",
    "cuánto se", "cuanto se", "cuánto factur", "cuanto factur",
]

INVENTORY_KEYWORDS = [
    "inventario", "stock", "existencia", "existencias",
    "almacén", "almacen", "almacenes",
    "disponible", "disponibilidad", "disponibles",
    "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
    "cuánto tenemos", "cuanto tenemos",
    "en almacén", "en almacen", "en bodega",
]

ORDER_KEYWORDS = [
    "orden", "órdenes", "ordenes", "orden de compra", "órdenes de compra",
    "ordenes de compra", "pendiente", "pendientes",
    "por recibir", "por recepcionar", "por recepción", "por recepcion",
    "solicitado", "solicitados", "pedido", "pedidos",
]

PRICE_COMPARE_KEYWORDS = [
    "comparar precio", "comparación de precio", "comparacion de precio",
    "mejor precio", "precio más bajo", "precio mas bajo",
    "quién vende más barato", "quien vende mas barato",
    "proveedores que venden", "alternativas de proveedor",
]

PAYMENT_KEYWORDS = [
    "estado de pago", "pagada", "pagadas", "pendiente de pago",
    "por pagar", "facturas pagadas", "facturas pendientes",
    "facturas vencidas", "vencida", "vencidas", "morosidad",
    "cuentas por pagar", "deuda", "adeudado",
]

# Organization name mapping (keyword → iDempiere org name)
ORG_MAP = [
    ("inpromaiz", "InproMaiz"),
    ("inpro maiz", "InproMaiz"),
    ("inproa santoni", "INPROA SANTONI"),
    ("inproa", "INPROA SANTONI"),
    ("santoni service", "Santoni Service"),
    ("agropecuaria", "AGROPECUARIA"),
    ("aga agricola", "AGA AGRICOLA"),
    ("aga agrícola", "AGA AGRICOLA"),
    ("agroinproa", "AGROINPROA"),
    ("inversiones aga", "INVERSIONES AGA"),
]


def extract_org_name(msg: str) -> str | None:
    msg_lower = msg.lower()
    for kw, val in ORG_MAP:
        if kw in msg_lower:
            return val
    return None


def extract_product_search(message: str) -> str | None:
    """Extract product code or name from user message.

    Handles:
    - Product codes: REP-LAMI-0037
    - Quoted names: "harina de avena"
    - "producto X" / "producto: X"
    - "compras de X" / "historial de compras de X"
    - "cuántas X compramos"
    - "precio de X"
    - Fallback: if message looks like a product description (no general keywords)
    """
    msg = message.strip()
    msg_lower = msg.lower()

    code_match = re.search(r'[A-Za-z]{2,}[-][A-Za-z]{2,}[-]\d+', msg)
    if code_match:
        return code_match.group()

    quoted = re.search(r'["\u201c](.+?)["\u201d]', msg)
    if quoted:
        return quoted.group(1)

    # Pronoun references ("ese producto", "este producto", etc.) refer to a
    # product from context → return None so the caller falls back to history.
    if re.search(r'\b(?:ese|este|aquel|el|del|dicho|mismo)\s+producto\b', msg_lower):
        return None

    prod_match = re.search(
        r'producto[:\s]+(.+?)(?:\s+(?:en|del|desde|este)\b|\s*[?]|$)',
        msg_lower,
    )
    if prod_match and len(prod_match.group(1).strip()) >= 3:
        return prod_match.group(1).strip()

    compras_match = re.search(
        r'(?:compras?\s+de|historial\s+de(?:\s+compras?\s+de)?)\s+'
        r'(.+?)(?:\s+(?:en|del|desde|este|el|último|ultima)\b|\s*[?]|$)',
        msg_lower,
    )
    if compras_match:
        product = compras_match.group(1).strip()
        product = re.sub(
            r'\s+(?:del?|en|este|el|[úu]ltimo|ultima|trimestre|semestre|mes|año)\s*$',
            '', product,
        )
        if len(product) >= 3 and product not in (
            'insumos', 'los insumos', 'todos', 'todos los', 'todos los insumos',
        ):
            return product

    cuanto_match = re.search(
        r'cu[aá]nt[ao]s?\s+(.+?)\s+(?:compramos|comprado|compr[oó]|se\s+compr)',
        msg_lower,
    )
    if cuanto_match:
        product = cuanto_match.group(1).strip()
        if len(product) >= 3:
            return product

    precio_match = re.search(
        r'precios?\s+de(?:\s+las?\s+[úu]ltim[ao]s?\s+\d+\s+compras?\s+de)?\s+'
        r'(.+?)(?:\s+(?:en|del|desde|este|el)\b|\s*[?]|$)',
        msg_lower,
    )
    if precio_match:
        product = precio_match.group(1).strip()
        if len(product) >= 3:
            return product

    codigo_match = re.search(
        r'c[oó]digos?\s+(?:de|del)\s+(?:las?\s+|los?\s+)?'
        r'(.+?)(?:\s*[?]|$)',
        msg_lower,
    )
    if codigo_match:
        product = codigo_match.group(1).strip()
        if len(product) >= 3:
            return product

    cantidad_match = re.search(
        r'cantidad\s+de\s+(.+?)\s+(?:se\s+ha|que\s+se|compramos|comprado|compr[oó]|en\s+la\b|desde\b)',
        msg_lower,
    )
    if cantidad_match:
        product = cantidad_match.group(1).strip()
        if len(product) >= 3:
            return product

    prov_match = re.search(
        r'proveedores?\s+(?:que\s+)?venden\s+'
        r'(.+?)(?:\s+(?:en|del|desde|este)\b|\s*[?]|$)',
        msg_lower,
    )
    if prov_match:
        product = prov_match.group(1).strip()
        if len(product) >= 3:
            return product

    cuanto_inv = re.search(
        r'cu[aá]nt[ao]s?\s+(.+?)\s+(?:quedan|hay|tenemos|tienen|queda|disponible)',
        msg_lower,
    )
    if cuanto_inv:
        product = cuanto_inv.group(1).strip()
        if len(product) >= 3:
            return product

    return None


def extract_product_from_history(history: list[tuple[str, str]]) -> str | None:
    """Try to extract a product search term from recent history."""
    if not history:
        return None
    for role, content in reversed(history):
        if role == "user":
            product = extract_product_search(content)
            if product:
                return product
    return None


def extract_dates_from_history(
    history: list[tuple[str, str]],
) -> tuple[str | None, str | None, int | None, int | None]:
    """Extract temporal context from recent history for follow-up messages."""
    for role, content in reversed(history):
        if role != "user":
            continue
        df, dt = extract_date_range(content)
        if df:
            mes_h, anio_h = extract_month_year(content)
            return df, dt, mes_h, anio_h
        mes_h, anio_h = extract_month_year(content)
        if mes_h is not None:
            return None, None, mes_h, anio_h
    return None, None, None, None


def detect_currency(
    message: str, history: list[tuple[str, str]] | None = None,
) -> list[int] | None:
    """Detect which currency the user wants based on message and history.

    Returns currency_ids list, or None for default (no filter).
    """
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in USD_KEYWORDS):
        return USD_IDS
    if any(kw in msg_lower for kw in VES_KEYWORDS):
        return VES_IDS

    if history:
        for role, content in reversed(history):
            if role == "user":
                content_lower = content.lower()
                if any(kw in content_lower for kw in USD_KEYWORDS):
                    return USD_IDS
                if any(kw in content_lower for kw in VES_KEYWORDS):
                    return VES_IDS
                break

    return None
