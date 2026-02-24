"""
Test scenarios basados en el historial real de Jorge Chahine (23-24/02/2026).
Valida routing del orchestrator y detección de inventario en compras_insumos.

Ejecutar:
    cd backend && python -m pytest tests/test_jorge_scenarios.py -v

Sin pytest:
    cd backend && python tests/test_jorge_scenarios.py

NO requiere Groq API key ni conexión a iDempiere.
"""

import sys
import os
import re

# Ensure backend is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.agents.orchestrator import classify_by_keywords

# We can't instantiate ComprasInsumosAgent (needs Groq API key),
# so we duplicate the class-level constants and extraction logic.
# These MUST match the lists in ComprasInsumosAgent exactly.

_INVENTORY_KEYWORDS = [
    "inventario", "stock", "existencia", "existencias",
    "almacén", "almacen", "almacenes",
    "disponible", "disponibilidad", "disponibles",
    "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
    "cuánto tenemos", "cuanto tenemos",
    "en almacén", "en almacen", "en bodega",
]

_GENERAL_KEYWORDS = [
    "resumen", "total", "proveedor", "proveedores", "mensual",
    "principales", "inventario", "stock", "existencia", "almacén",
    "almacen", "todos los insumos",
    "cuánto se", "cuanto se", "cuánto factur", "cuanto factur",
]


def _extract_product_search(message: str) -> str | None:
    """Replica of ComprasInsumosAgent._extract_product_search (no instance needed).
    Updated to match v2: specific patterns only, no aggressive fallback."""
    msg = message.strip()
    msg_lower = msg.lower()

    # Product code pattern
    code_match = re.search(r'[A-Za-z]{2,}[-][A-Za-z]{2,}[-]\d+', msg)
    if code_match:
        return code_match.group()

    # Quoted product name
    quoted = re.search(r'["\u201c](.+?)["\u201d]', msg)
    if quoted:
        return quoted.group(1)

    # "producto X"
    prod_match = re.search(
        r'producto[:\s]+(.+?)(?:\s+(?:en|del|desde|este)\b|\s*[?]|$)',
        msg_lower,
    )
    if prod_match and len(prod_match.group(1).strip()) >= 3:
        return prod_match.group(1).strip()

    # "compras de {product}"
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

    # "cuántas {product} compramos"
    cuanto_match = re.search(
        r'cu[aá]nt[ao]s?\s+(.+?)\s+(?:compramos|comprado|compr[oó]|se\s+compr)',
        msg_lower,
    )
    if cuanto_match:
        product = cuanto_match.group(1).strip()
        if len(product) >= 3:
            return product

    # "precio(s) de ... {product}"
    precio_match = re.search(
        r'precios?\s+de(?:\s+las?\s+[úu]ltim[ao]s?\s+\d+\s+compras?\s+de)?\s+'
        r'(.+?)(?:\s+(?:en|del|desde|este|el)\b|\s*[?]|$)',
        msg_lower,
    )
    if precio_match:
        product = precio_match.group(1).strip()
        if len(product) >= 3:
            return product

    # "código de X" / "codigo del X"
    codigo_match = re.search(
        r'c[oó]digos?\s+(?:de|del)\s+(?:las?\s+|los?\s+)?'
        r'(.+?)(?:\s*[?]|$)',
        msg_lower,
    )
    if codigo_match:
        product = codigo_match.group(1).strip()
        if len(product) >= 3:
            return product

    # "cantidad de X se ha comprado / que se compró"
    cantidad_match = re.search(
        r'cantidad\s+de\s+(.+?)\s+(?:se\s+ha|que\s+se|compramos|comprado|compr[oó]|en\s+la\b|desde\b)',
        msg_lower,
    )
    if cantidad_match:
        product = cantidad_match.group(1).strip()
        if len(product) >= 3:
            return product

    # "proveedores (que) venden X"
    prov_match = re.search(
        r'proveedores?\s+(?:que\s+)?venden\s+'
        r'(.+?)(?:\s+(?:en|del|desde|este)\b|\s*[?]|$)',
        msg_lower,
    )
    if prov_match:
        product = prov_match.group(1).strip()
        if len(product) >= 3:
            return product

    # "cuántas X quedan/hay/tenemos" (inventory-oriented)
    cuanto_inv = re.search(
        r'cu[aá]nt[ao]s?\s+(.+?)\s+(?:quedan|hay|tenemos|tienen|queda|disponible)',
        msg_lower,
    )
    if cuanto_inv:
        product = cuanto_inv.group(1).strip()
        if len(product) >= 3:
            return product

    # No aggressive fallback - return None and let general summary handle it
    return None


# Currency constants (must match ComprasInsumosAgent)
_VES_IDS = [205]
_USD_IDS = [1000000, 1000003, 1000006, 1000008, 1000011, 1000013, 1000017]

_USD_KEYWORDS = [
    "dólares", "dolares", "dólar", "dolar", "usd",
    "en dólares", "en dolares", "en dólar", "en dolar",
]

_VES_KEYWORDS = [
    "bolívares", "bolivares", "bolívar", "bolivar", "ves",
    "en bolívares", "en bolivares",
]


def _detect_currency(message: str, history: list[tuple[str, str]] | None = None) -> list[int] | None:
    """Replica of ComprasInsumosAgent._detect_currency (no instance needed)."""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in _USD_KEYWORDS):
        return _USD_IDS

    if any(kw in msg_lower for kw in _VES_KEYWORDS):
        return _VES_IDS

    if history:
        for role, content in reversed(history):
            if role == "user":
                content_lower = content.lower()
                if any(kw in content_lower for kw in _USD_KEYWORDS):
                    return _USD_IDS
                if any(kw in content_lower for kw in _VES_KEYWORDS):
                    return _VES_IDS
                break

    return _VES_IDS


# Jorge's departments: compras_insumos (primary) + ventas, compras_productores, produccion (extra)
JORGE_DEPARTMENTS = ["compras_insumos", "ventas", "compras_productores", "produccion"]

# ===========================================================================
# 1. ROUTING TESTS - Does the orchestrator send Jorge to the right agent?
# ===========================================================================

def test_routing_compras_insumos_este_mes():
    """'¿Cuánto se compró de insumos este mes?' → compras_insumos"""
    result = classify_by_keywords(
        "¿Cuánto se compró de insumos este mes?",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_ordenes_pendientes():
    """'Órdenes de compra pendientes por recepción de insumos del mes de febrero' → compras_insumos"""
    result = classify_by_keywords(
        "Órdenes de compra pendientes por recepción de insumos del mes de febrero",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_inventario_cajas():
    """'quisiera saber cuantas cajas de carton quedan en inventario' → compras_insumos"""
    result = classify_by_keywords(
        "quisiera saber cuantas cajas de carton quedan en inventario",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_codigo_producto():
    """'tienes el codigo de las cajas de carton para cereales' → compras_insumos (follow-up)"""
    # Without last_agent, no keyword matches → general
    result = classify_by_keywords(
        "tienes el codigo de las cajas de carton para cereales",
        JORGE_DEPARTMENTS,
        last_agent="compras_insumos",
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_proveedores_laminas():
    """'que proveedores venden laminas de hierro negro' → compras_insumos"""
    result = classify_by_keywords(
        "que proveedores venden laminas de hierro negro",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_busca_historial():
    """'busca en el sistema el historial de compras de laminas de hierro negro' → compras_insumos"""
    result = classify_by_keywords(
        "busca en el sistema el historial de compras de laminas de hierro negro",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_historial_producto_codigo():
    """'quiero el historial de compra del siguiente producto REP-LAMI-0037' → compras_insumos"""
    result = classify_by_keywords(
        "quiero el historial de compra del siguiente producto REP-LAMI-0037",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_cliente_inproa_rango():
    """'cliente inproa santoni, en el rango de fecha 01-11-25 hasta el 23-02-26'
    Contains 'cliente' which matches ventas. Jorge has access to ventas,
    so it routes there. The original bug was no_access - now it's accessible.
    Key: result must NOT be 'no_access' or 'general'."""
    result = classify_by_keywords(
        "cliente inproa santoni, en el rango de fecha 01-11-25 hasta el 23-02-26",
        JORGE_DEPARTMENTS,
        last_agent="compras_insumos",
    )
    assert result != "no_access", f"Must NOT be no_access, got {result}"
    assert result != "general", f"Must NOT be general, got {result}"
    # 'cliente' keyword → ventas (Jorge has access), which is acceptable
    assert result in ("ventas", "compras_insumos"), f"Expected ventas or compras_insumos, got {result}"


def test_routing_ultimo_proveedor():
    """'quien fue el ultimo proveedor del siguiente producto REP-LAMI-0037 en la empresa inproa santoni' → compras_insumos"""
    result = classify_by_keywords(
        "quien fue el ultimo proveedor del siguiente producto REP-LAMI-0037 en la empresa inproa santoni",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_cantidad_gasoil():
    """'que cantidad de gasoil se ha comprado en la empresa Inproa santoni desde el 01-01-26 hasta el 23-02-26' → compras_insumos"""
    result = classify_by_keywords(
        "que cantidad de gasoil se ha comprado en la empresa Inproa santoni desde el 01-01-26 hasta el 23-02-26",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_inventario_actual_producto():
    """'dame el inventario actual de ese producto en inproa santoni' → compras_insumos"""
    result = classify_by_keywords(
        "dame el inventario actual de ese producto en inproa santoni",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_stock_arroz():
    """'cuanto stock de arroz hay en almacen' → compras_insumos"""
    result = classify_by_keywords(
        "cuanto stock de arroz hay en almacen",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_existencia():
    """'cual es la existencia de repuestos' → compras_insumos"""
    result = classify_by_keywords(
        "cual es la existencia de repuestos",
        JORGE_DEPARTMENTS,
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_followup_si():
    """'si' (follow-up to previous compras_insumos context) → compras_insumos"""
    result = classify_by_keywords(
        "si",
        JORGE_DEPARTMENTS,
        last_agent="compras_insumos",
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


def test_routing_en_gastos_followup():
    """'En gastos?' follow-up after compras_insumos → should stay in compras_insumos"""
    result = classify_by_keywords(
        "En gastos?",
        JORGE_DEPARTMENTS,
        last_agent="compras_insumos",
    )
    assert result == "compras_insumos", f"Expected compras_insumos, got {result}"


# ===========================================================================
# 2. INVENTORY DETECTION TESTS - Does compras_insumos detect inventory queries?
# ===========================================================================


def test_inventory_detection_inventario():
    """'inventario' keyword triggers inventory path"""
    msg = "quisiera saber cuantas cajas de carton quedan en inventario"
    assert any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should detect inventory in: {msg}"


def test_inventory_detection_stock():
    """'stock' keyword triggers inventory path"""
    msg = "cuanto stock de arroz hay"
    assert any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should detect inventory in: {msg}"


def test_inventory_detection_existencia():
    """'existencia' keyword triggers inventory path"""
    msg = "cual es la existencia de repuestos"
    assert any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should detect inventory in: {msg}"


def test_inventory_detection_cuanto_hay():
    """'cuanto hay' keyword triggers inventory path"""
    msg = "cuanto hay de laminas en el almacen"
    assert any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should detect inventory in: {msg}"


def test_inventory_detection_inventario_actual():
    """'dame el inventario actual' triggers inventory"""
    msg = "dame el inventario actual de ese producto en inproa santoni"
    assert any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should detect inventory in: {msg}"


def test_inventory_NOT_detected_for_compras():
    """Regular purchase queries should NOT trigger inventory"""
    msg = "cuanto se compro de insumos este mes"
    assert not any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should NOT detect inventory in: {msg}"


def test_inventory_NOT_detected_for_historial():
    """Purchase history should NOT trigger inventory"""
    msg = "quiero el historial de compra del siguiente producto REP-LAMI-0037"
    assert not any(w in msg.lower() for w in _INVENTORY_KEYWORDS), \
        f"Should NOT detect inventory in: {msg}"


# ===========================================================================
# 3. PRODUCT EXTRACTION TESTS - Does compras_insumos extract product correctly?
# ===========================================================================

def test_extract_product_code_rep_lami():
    """Should extract REP-LAMI-0037 from message"""
    result = _extract_product_search(
        "quiero el historial de compra del siguiente producto REP-LAMI-0037"
    )
    assert result == "REP-LAMI-0037", f"Expected REP-LAMI-0037, got {result}"


def test_extract_product_code_rep_tuer():
    """Should extract REP-TUER-0115 from message"""
    result = _extract_product_search(
        "quien fue el ultimo proveedor del siguiente producto REP-TUER-0115 en la empresa inproa santoni"
    )
    assert result == "REP-TUER-0115", f"Expected REP-TUER-0115, got {result}"


def test_extract_product_laminas():
    """Should extract product name from 'historial de compras de laminas de hierro negro'"""
    result = _extract_product_search(
        "busca en el sistema el historial de compras de laminas de hierro negro"
    )
    assert result is not None, "Should extract product from 'compras de laminas de hierro negro'"
    assert "laminas" in result.lower() or "hierro" in result.lower(), \
        f"Expected product containing 'laminas' or 'hierro', got: {result}"


def test_extract_product_gasoil():
    """Should extract 'gasoil' from 'cantidad de gasoil se ha comprado'"""
    result = _extract_product_search(
        "que cantidad de gasoil se ha comprado en la empresa Inproa santoni"
    )
    assert result is not None, "Should extract 'gasoil' from message"
    assert "gasoil" in result.lower(), f"Expected 'gasoil' in result, got: {result}"


def test_extract_product_cajas_carton_codigo():
    """Should extract 'cajas de carton para cereales' from 'codigo de' pattern"""
    result = _extract_product_search(
        "tienes el codigo de las cajas de carton para cereales"
    )
    assert result is not None, "Should extract product from 'codigo de' pattern"
    assert "carton" in result.lower() or "cereales" in result.lower(), \
        f"Expected 'carton' or 'cereales' in result, got: {result}"


def test_extract_product_cajas_quedan():
    """Should extract 'cajas de carton' from 'cuantas X quedan en inventario'"""
    result = _extract_product_search(
        "quisiera saber cuantas cajas de carton quedan en inventario"
    )
    assert result is not None, "Should extract product from 'cuantas X quedan'"
    assert "carton" in result.lower() or "caja" in result.lower(), \
        f"Expected 'carton' or 'caja' in result, got: {result}"


def test_extract_product_proveedores_venden():
    """Should extract 'laminas de hierro negro' from 'proveedores venden X'"""
    result = _extract_product_search(
        "que proveedores venden laminas de hierro negro"
    )
    assert result is not None, "Should extract product from 'proveedores venden X'"
    assert "laminas" in result.lower() or "hierro" in result.lower(), \
        f"Expected 'laminas' or 'hierro' in result, got: {result}"


# ===========================================================================
# 4. FALSE POSITIVE TESTS - Messages that should NOT extract a product
# ===========================================================================

def test_no_product_dolares_followup():
    """'Y en dólares?' should NOT extract a product"""
    result = _extract_product_search("Y en dólares?")
    assert result is None, f"Expected None for follow-up 'Y en dólares?', got: {result}"


def test_no_product_gastos_followup():
    """'En gastos?' should NOT extract a product"""
    result = _extract_product_search("En gastos?")
    assert result is None, f"Expected None for follow-up 'En gastos?', got: {result}"


def test_no_product_ordenes_pendientes():
    """'Órdenes de compra pendientes...' should NOT extract a product"""
    result = _extract_product_search(
        "Órdenes de compra pendientes por recepción de insumos del mes de febrero"
    )
    assert result is None, f"Expected None for 'ordenes pendientes', got: {result}"


def test_no_product_cuanto_se_compro():
    """'¿Cuánto se compró de insumos este mes?' should NOT extract a product (general query)"""
    result = _extract_product_search("¿Cuánto se compró de insumos este mes?")
    assert result is None, f"Expected None for general compras query, got: {result}"


def test_no_product_administrativos():
    """'administrativos' should NOT extract a product"""
    result = _extract_product_search("administrativos")
    assert result is None, f"Expected None for 'administrativos', got: {result}"


# ===========================================================================
# 5. CURRENCY DETECTION TESTS - Does compras_insumos detect currency correctly?
# ===========================================================================

def test_currency_default_ves():
    """Default currency (no keyword) should be VES"""
    result = _detect_currency("¿Cuánto se compró de insumos este mes?")
    assert result == _VES_IDS, f"Expected VES {_VES_IDS}, got {result}"


def test_currency_dolares_keyword():
    """'Y en dólares?' should detect USD"""
    result = _detect_currency("Y en dólares?")
    assert result == _USD_IDS, f"Expected USD {_USD_IDS}, got {result}"


def test_currency_dolares_no_accent():
    """'en dolares' (no accent) should detect USD"""
    result = _detect_currency("cuanto se compro en dolares?")
    assert result == _USD_IDS, f"Expected USD {_USD_IDS}, got {result}"


def test_currency_usd_keyword():
    """'en usd' should detect USD"""
    result = _detect_currency("dame el total en usd")
    assert result == _USD_IDS, f"Expected USD {_USD_IDS}, got {result}"


def test_currency_bolivares_keyword():
    """'en bolívares' should detect VES"""
    result = _detect_currency("Y en bolívares?")
    assert result == _VES_IDS, f"Expected VES {_VES_IDS}, got {result}"


def test_currency_from_history():
    """Follow-up should inherit USD from history"""
    history = [
        ("user", "cuanto se compro en dólares?"),
        ("assistant", "Las compras en dólares fueron..."),
    ]
    result = _detect_currency("dame más detalle", history)
    assert result == _USD_IDS, f"Expected USD {_USD_IDS} from history, got {result}"


def test_currency_no_inherit_unrelated_history():
    """Should NOT inherit currency from non-immediate history"""
    history = [
        ("user", "cuanto se compro en dólares?"),
        ("assistant", "Las compras en dólares fueron..."),
        ("user", "cuantos proveedores tenemos?"),
        ("assistant", "Hay 50 proveedores..."),
    ]
    # Last user message is "cuantos proveedores tenemos?" (no currency)
    # _detect_currency checks reversed history and stops at first user msg
    result = _detect_currency("dame más detalle", history)
    assert result == _VES_IDS, f"Expected VES {_VES_IDS} (last user msg had no currency), got {result}"


# ===========================================================================
# 6. CONFIDENCE SCORE TESTS - Does classify_with_confidence return correct scores?
# ===========================================================================

from app.agents.orchestrator import classify_with_confidence, compute_confidence_score


def test_confidence_keyword_directo():
    """Direct keyword match should have score 1.0"""
    agent, score, match_type = classify_with_confidence(
        "¿Cuánto se compró de insumos este mes?", JORGE_DEPARTMENTS,
    )
    assert agent == "compras_insumos", f"Expected compras_insumos, got {agent}"
    assert score == 1.0, f"Expected score 1.0, got {score}"
    assert match_type == "keyword_directo", f"Expected keyword_directo, got {match_type}"


def test_confidence_followup_last_agent():
    """Follow-up via last_agent should have score 0.7"""
    agent, score, match_type = classify_with_confidence(
        "Y en dólares?", JORGE_DEPARTMENTS, last_agent="compras_insumos",
    )
    assert agent == "compras_insumos", f"Expected compras_insumos, got {agent}"
    assert score == 0.7, f"Expected score 0.7, got {score}"
    assert match_type == "followup_last_agent", f"Expected followup_last_agent, got {match_type}"


def test_confidence_general_sin_match():
    """No match, no last_agent → general with low score"""
    agent, score, match_type = classify_with_confidence(
        "que hora es?", JORGE_DEPARTMENTS,
    )
    assert agent == "general", f"Expected general, got {agent}"
    assert score <= 0.3, f"Expected score <= 0.3, got {score}"


def test_confidence_saludo():
    """Greeting should score 1.0 (confident it's general)"""
    agent, score, match_type = classify_with_confidence(
        "hola", JORGE_DEPARTMENTS,
    )
    assert agent == "general", f"Expected general, got {agent}"
    assert score == 1.0, f"Expected 1.0 for greeting, got {score}"
    assert match_type == "saludo_directo"


def test_compute_confidence_agent_with_data():
    """Specialized agent with data should score high"""
    score, breakdown = compute_confidence_score(1.0, True, "compras_insumos")
    assert score == 1.0, f"Expected 1.0, got {score}"
    assert breakdown["routing"] == 1.0
    assert breakdown["data"] == 1.0


def test_compute_confidence_agent_no_data():
    """Specialized agent without data should score lower"""
    score, breakdown = compute_confidence_score(1.0, False, "compras_insumos")
    assert score == 0.68, f"Expected 0.68, got {score}"
    assert breakdown["data"] == 0.2


def test_compute_confidence_general():
    """General agent should have low overall score"""
    score, breakdown = compute_confidence_score(0.3, False, "general")
    assert score <= 0.5, f"Expected <= 0.5 for general, got {score}"


# ===========================================================================
# 7. TEMPORAL CONTEXT INHERITANCE TESTS - Follow-ups inherit date/month
# ===========================================================================

from app.agents.date_utils import extract_date_range, extract_month_year


def _extract_dates_from_history(
    history: list[tuple[str, str]],
) -> tuple[str | None, str | None, int | None, int | None]:
    """Replica of ComprasInsumosAgent._extract_dates_from_history."""
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


def test_temporal_inherit_este_mes():
    """'Y en dólares?' after 'compras este mes' should inherit current month"""
    history = [
        ("user", "¿Cuánto se compró de insumos este mes?"),
        ("assistant", "En febrero de 2026 se compraron..."),
    ]
    df, dt, mes, anio = _extract_dates_from_history(history)
    from datetime import datetime
    assert mes == datetime.now().month, f"Expected current month {datetime.now().month}, got {mes}"
    assert df is None, f"Expected no date_from, got {df}"


def test_temporal_inherit_explicit_month():
    """'Y en dólares?' after 'compras en enero' should inherit enero"""
    history = [
        ("user", "¿Cuánto se compró de insumos en enero 2026?"),
        ("assistant", "En enero de 2026 se compraron..."),
    ]
    df, dt, mes, anio = _extract_dates_from_history(history)
    assert mes == 1, f"Expected mes=1 (enero), got {mes}"
    assert anio == 2026, f"Expected anio=2026, got {anio}"


def test_temporal_inherit_date_range():
    """Follow-up after date range query should inherit the range"""
    history = [
        ("user", "compras desde el 01/01/2026 al 31/01/2026"),
        ("assistant", "Las compras en ese período..."),
    ]
    df, dt, mes, anio = _extract_dates_from_history(history)
    assert df == "2026-01-01", f"Expected date_from=2026-01-01, got {df}"
    assert dt == "2026-01-31", f"Expected date_to=2026-01-31, got {dt}"


def test_temporal_inherit_chain():
    """Third follow-up should still inherit from first query"""
    history = [
        ("user", "¿Cuánto se compró de insumos en enero?"),
        ("assistant", "En enero se compraron..."),
        ("user", "Y en dólares?"),
        ("assistant", "En dólares, enero..."),
    ]
    # "Y en dólares?" has no temporal context → keeps scanning back
    # Finds "enero" in first user message
    df, dt, mes, anio = _extract_dates_from_history(history)
    assert mes == 1, f"Expected mes=1 (enero) from chain, got {mes}"


def test_temporal_no_inherit_without_history():
    """No history → no temporal context"""
    df, dt, mes, anio = _extract_dates_from_history([])
    assert df is None
    assert mes is None
    assert anio is None


def test_temporal_no_inherit_generic_history():
    """History with no temporal info → no inheritance"""
    history = [
        ("user", "hola"),
        ("assistant", "¡Hola! ¿En qué puedo ayudarte?"),
    ]
    df, dt, mes, anio = _extract_dates_from_history(history)
    assert mes is None, f"Expected mes=None, got {mes}"


# ===========================================================================
# MAIN: Run all tests and print results
# ===========================================================================

if __name__ == "__main__":
    import traceback

    tests = [
        # Routing tests
        ("ROUTING: compras insumos este mes", test_routing_compras_insumos_este_mes),
        ("ROUTING: ordenes pendientes", test_routing_ordenes_pendientes),
        ("ROUTING: inventario cajas", test_routing_inventario_cajas),
        ("ROUTING: codigo producto (follow-up)", test_routing_codigo_producto),
        ("ROUTING: proveedores laminas", test_routing_proveedores_laminas),
        ("ROUTING: busca historial", test_routing_busca_historial),
        ("ROUTING: historial producto codigo", test_routing_historial_producto_codigo),
        ("ROUTING: cliente inproa rango (follow-up)", test_routing_cliente_inproa_rango),
        ("ROUTING: ultimo proveedor", test_routing_ultimo_proveedor),
        ("ROUTING: cantidad gasoil", test_routing_cantidad_gasoil),
        ("ROUTING: inventario actual producto", test_routing_inventario_actual_producto),
        ("ROUTING: stock arroz", test_routing_stock_arroz),
        ("ROUTING: existencia repuestos", test_routing_existencia),
        ("ROUTING: follow-up 'si'", test_routing_followup_si),
        ("ROUTING: follow-up 'En gastos?'", test_routing_en_gastos_followup),
        # Inventory detection
        ("INVENTARIO: detecta 'inventario'", test_inventory_detection_inventario),
        ("INVENTARIO: detecta 'stock'", test_inventory_detection_stock),
        ("INVENTARIO: detecta 'existencia'", test_inventory_detection_existencia),
        ("INVENTARIO: detecta 'cuanto hay'", test_inventory_detection_cuanto_hay),
        ("INVENTARIO: detecta 'inventario actual'", test_inventory_detection_inventario_actual),
        ("INVENTARIO: NO detecta compras normales", test_inventory_NOT_detected_for_compras),
        ("INVENTARIO: NO detecta historial", test_inventory_NOT_detected_for_historial),
        # Product extraction
        ("PRODUCTO: extrae REP-LAMI-0037", test_extract_product_code_rep_lami),
        ("PRODUCTO: extrae REP-TUER-0115", test_extract_product_code_rep_tuer),
        ("PRODUCTO: extrae laminas hierro negro", test_extract_product_laminas),
        ("PRODUCTO: extrae gasoil (cantidad de X)", test_extract_product_gasoil),
        ("PRODUCTO: extrae cajas carton (codigo de X)", test_extract_product_cajas_carton_codigo),
        ("PRODUCTO: extrae cajas carton (cuantas X quedan)", test_extract_product_cajas_quedan),
        ("PRODUCTO: extrae laminas (proveedores venden)", test_extract_product_proveedores_venden),
        # False positive tests
        ("NO-PRODUCT: 'Y en dólares?'", test_no_product_dolares_followup),
        ("NO-PRODUCT: 'En gastos?'", test_no_product_gastos_followup),
        ("NO-PRODUCT: ordenes pendientes", test_no_product_ordenes_pendientes),
        ("NO-PRODUCT: cuanto se compro insumos", test_no_product_cuanto_se_compro),
        ("NO-PRODUCT: administrativos", test_no_product_administrativos),
        # Currency detection
        ("MONEDA: default VES", test_currency_default_ves),
        ("MONEDA: dólares → USD", test_currency_dolares_keyword),
        ("MONEDA: dolares sin acento → USD", test_currency_dolares_no_accent),
        ("MONEDA: usd → USD", test_currency_usd_keyword),
        ("MONEDA: bolívares → VES", test_currency_bolivares_keyword),
        ("MONEDA: hereda USD de historial", test_currency_from_history),
        ("MONEDA: NO hereda de historial lejano", test_currency_no_inherit_unrelated_history),
        # Confidence score
        ("CONFIDENCE: keyword directo = 1.0", test_confidence_keyword_directo),
        ("CONFIDENCE: followup last_agent = 0.7", test_confidence_followup_last_agent),
        ("CONFIDENCE: general sin match <= 0.3", test_confidence_general_sin_match),
        ("CONFIDENCE: saludo = 1.0", test_confidence_saludo),
        ("CONFIDENCE: compute agente+datos = 1.0", test_compute_confidence_agent_with_data),
        ("CONFIDENCE: compute agente-datos = 0.68", test_compute_confidence_agent_no_data),
        ("CONFIDENCE: compute general <= 0.5", test_compute_confidence_general),
        # Temporal context inheritance
        ("TEMPORAL: hereda 'este mes' del historial", test_temporal_inherit_este_mes),
        ("TEMPORAL: hereda mes explícito (enero)", test_temporal_inherit_explicit_month),
        ("TEMPORAL: hereda rango de fechas", test_temporal_inherit_date_range),
        ("TEMPORAL: hereda en cadena (3er follow-up)", test_temporal_inherit_chain),
        ("TEMPORAL: sin historial → sin herencia", test_temporal_no_inherit_without_history),
        ("TEMPORAL: historial genérico → sin herencia", test_temporal_no_inherit_generic_history),
    ]

    passed = 0
    failed = 0
    errors = []

    print("=" * 70)
    print("TEST SCENARIOS JORGE CHAHINE - SantoniBot v2")
    print("=" * 70)

    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}")
            print(f"         -> {e}")
            failed += 1
            errors.append((name, str(e)))
        except Exception as e:
            print(f"  ERROR {name}")
            print(f"         -> {traceback.format_exc().splitlines()[-1]}")
            failed += 1
            errors.append((name, str(e)))

    print("=" * 70)
    print(f"Resultados: {passed} PASS, {failed} FAIL de {len(tests)} tests")
    print("=" * 70)

    if errors:
        print("\nFallas:")
        for name, err in errors:
            print(f"  - {name}: {err}")

    sys.exit(0 if failed == 0 else 1)
