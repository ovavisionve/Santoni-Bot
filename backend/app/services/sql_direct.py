"""
SQL Direct — Consulta directa a iDempiere via LLM-generated SQL.

En vez de pasar por 8 capas (routing → agente → parámetros → función →
SQL → formateo → LLM → respuesta), este módulo hace:

  1. LLM recibe la pregunta + catálogo de views disponibles
  2. LLM genera un SELECT SQL
  3. Python valida y ejecuta (read-only, solo views lve_*)
  4. LLM formatea los resultados como respuesta natural

Protecciones de seguridad:
  - Solo SELECT (nunca INSERT/UPDATE/DELETE/DROP)
  - Solo views con prefijo lve_* o tablas whitelisted
  - Límite de 500 filas
  - Timeout de 30 segundos
  - Audit log de cada query generada

Creado: 10/Abr/2026 como solución al problema de fondo del bot:
demasiadas capas de interpretación entre la pregunta y los datos.
"""

import logging
import re
import time
from datetime import datetime

from sqlalchemy import text

from app.database import IdempiereSession
from app.services.llm_factory import create_llm
from app.agents.base_agent import _build_datetime_context

logger = logging.getLogger("santonibot.sql_direct")

# ─────────────────────────────────────────────────────────────────────
# Catálogo de views disponibles para el LLM
# ─────────────────────────────────────────────────────────────────────

VIEWS_CATALOG = """
## Views disponibles en iDempiere (Localización Venezuela — lve_*)

Estas son las fuentes OFICIALES de datos de Alimentos Santoni. Usa SOLO estas views.

### RRHH — Empleados
**lve_empleadosactivos** — Empleados activos del grupo Santoni (1 fila por empleado REAL)
Columnas: ad_org_id, name (nombre completo REAL del empleado), value (cédula), c_bpartner_id,
  hr_payroll_id, nomina (tipo nómina), startdate (fecha ingreso),
  hr_department_id, departamento, hr_job_id, cargo,
  birthday (fecha de nacimiento — usar para cumpleañeros: EXTRACT(MONTH FROM birthday) = N),
  sueldo (sueldo BASE sin bonos), asignacion (bonos/asignaciones),
  total (TOTAL DEVENGADO = sueldo + asignacion — usar este para "sueldo promedio" o "cuánto gana"),
  edad, tservicio (años servicio), gender
IMPORTANTE: Para "sueldo promedio" usar AVG(total), NO AVG(sueldo). La columna 'sueldo' es solo el base.
IMPORTANTE: Para cumpleañeros SIEMPRE generar SQL con SELECT name, cargo, departamento, birthday.
  NUNCA responder NO_SQL para preguntas de cumpleaños — la columna birthday está en esta view.

**lve_empleadosinactivos** — Empleados inactivos/retirados (misma estructura)

### Ventas — Facturas
**c_invoice** — Facturas de venta Y compra (tabla raw, funciona bien para ventas)
Columnas: c_invoice_id, c_bpartner_id, salesrep_id, c_currency_id,
  dateinvoiced, totallines (sin IVA), grandtotal (con IVA), docstatus,
  issotrx ('Y'=venta, 'N'=compra), ad_org_id, c_doctypetarget_id
IMPORTANTE: Para ventas filtrar issotrx='Y', docstatus IN ('CO','CL'), isactive='Y'
Para el tipo de documento: JOIN c_doctype dt ON c_doctypetarget_id = dt.c_doctype_id
  → dt.docbasetype: 'ARI'=factura, 'ARC'=nota de crédito

**c_bpartner** — Clientes/Proveedores/Empleados
Columnas: c_bpartner_id, name, value, iscustomer, isvendor, isemployee

**ad_user** — Vendedores (salesrep)
Columnas: ad_user_id, name (nombre del vendedor)
JOIN: c_invoice.salesrep_id = ad_user.ad_user_id

**ad_org** — Organizaciones del grupo Santoni
Columnas: ad_org_id, name, value
Orgs reales: INPROA SANTONI C.A., InproMaiz C.A, AGROINPROA C.A,
  AGROPECUARIA R.R. C.A., AGA AGRICOLA C.A, INVERSIONES AGA C.A, Santoni Service C.A

### Monedas
**c_currency** — Monedas
VES (Bolívares) = c_currency_id 205
USD (Dólares) = c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
Hay 9 IDs distintos para dólar porque iDempiere creó variantes (DOL, Dol, DoL, USA, dol, etc.)

### Cobranza
**c_payment** — Cobros y Pagos
Columnas: c_payment_id, c_bpartner_id, payamt, datetrx, c_currency_id,
  isreceipt ('Y'=cobro, 'N'=pago), docstatus, tendertype (método de pago)

### Finanzas — Bancos
**lve_disponibilidadbancaria** — Saldos bancarios disponibles (view oficial de Santoni)
**lve_disponibilidadbancariateso** — Saldos bancarios vista tesorería
**lve_disponibilidadbancariagerencia** — Saldos bancarios vista gerencia
**lve_compromisosbancarios** — Compromisos bancarios pendientes

### Compras a Productores — Guías
**c_order** — Órdenes de compra / Guías de recepción a productores
Columnas: c_order_id, c_bpartner_id, dateordered, issotrx, docstatus, ad_org_id
**c_orderline** — Líneas de orden (qtyordered, m_product_id, linenetamt)
**m_product** — Productos (name, value, m_product_category_id)
IMPORTANTE: compras a productores usan c_order (guías), NO c_invoice

### Compras de Insumos
Usa c_invoice con issotrx='N' (misma tabla que ventas pero filtro opuesto)

### Contabilidad
**fact_acct** — Hechos contables
Columnas: fact_acct_id, account_id, dateacct, amtacctdr (debe), amtacctcr (haber),
  ad_org_id, c_period_id
**c_elementvalue** — Plan de cuentas (nombre y tipo de cuenta)
accounttype: A=Activo, L=Pasivo, O=Patrimonio, R=Ingreso, E=Gasto

### Producción / Inventario
**m_inout** — Movimientos de inventario (recepciones y despachos)
Columnas: m_inout_id, movementdate, movementtype, docstatus, ad_org_id
movementtype: V+=Recepción, C-=Despacho, M+/M-=Mov. interno, P+/P-=Producción
**m_inoutline** — Líneas (movementqty, m_product_id)

### Saldos de clientes/proveedores
**lve_saldosclientes** — Saldos pendientes de clientes
**lve_saldosproveedor** — Saldos pendientes de proveedores
**lve_saldosproductor** — Saldos pendientes de productores agrícolas
**lve_customer_statement** — Estado de cuenta de clientes
**lve_supplier_statement** — Estado de cuenta de proveedores
**lve_analisisvencimientoinproa** — Análisis de vencimiento de facturas INPROA

### Cobranza — Views oficiales
**lve_informepago** — Informe de pagos
**lve_resumencobro** — Resumen de cobros
**lve_payment** — Pagos detallados
**lve_payment_receipt** — Recibos de pago

### Compras — Views oficiales
**lve_buy_book** — Libro de compras
**lve_buy_book_sumary** — Resumen del libro de compras
**lve_anticipoproductor** — Anticipos a productores
**lve_anticipoproveedor** — Anticipos a proveedores
**lve_guiasmovilizacion** — Guías de movilización de productores

### Contabilidad — Views oficiales
**lve_fact_acct** — Hechos contables (versión LVE)
**lve_trialbalance** — Balance de comprobación

### Inventario — Views oficiales
**lve_inventario_terminado** — Inventario de producto terminado
**lve_inventario_paddy** — Inventario de arroz paddy
**lve_inventario_maiz** — Inventario de maíz
**lve_inventario_empaque** — Inventario de materiales de empaque
**lve_inventario_granos** — Inventario de granos
**lve_inventario_repuesto** — Inventario de repuestos
**lve_inventario_comercial** — Inventario comercial
**lve_existenciayubicacion** — Existencias y ubicación por almacén

### Ventas — Views oficiales
**lve_sales_book** — Libro de ventas (por factura, estilo SENIAT)
**lve_sales_books** — Libros de ventas (plural)

## REGLAS para generar SQL:
1. SOLO usar SELECT (nunca INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE)
2. Todas las tablas deben tener prefijo 'adempiere.' (ej: adempiere.lve_empleadosactivos)
3. Limitar a 500 filas con LIMIT 500
4. Para fechas usar formato 'YYYY-MM-DD'
5. Para ventas SIEMPRE filtrar: issotrx='Y', docstatus IN ('CO','CL'), isactive='Y'
6. Para compras a proveedores: issotrx='N' en c_invoice
7. Para compras a productores: usar c_order (guías), NO c_invoice
8. VES = c_currency_id = 205. USD = c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
9. Usar totallines (sin IVA) para montos de ventas, grandtotal (con IVA) para compras
10. Si no sabes qué columna tiene una tabla, haz tu mejor intento con las columnas del catálogo
11. SIEMPRE intenta generar SQL. Solo responde NO_SQL si la pregunta no tiene nada que ver con datos (ej: "hola", "gracias", chistes). Para cualquier pregunta sobre datos empresariales, genera el SQL.

## EJEMPLOS de queries comunes:

-- Sueldo promedio por organización:
SELECT AVG(sueldo) AS sueldo_promedio, COUNT(*) AS empleados
FROM adempiere.lve_empleadosactivos
WHERE ad_org_id = (SELECT ad_org_id FROM adempiere.ad_org WHERE name ILIKE '%InproMaiz%')
LIMIT 500

-- Facturas de venta por moneda y período:
SELECT COUNT(DISTINCT i.c_invoice_id) AS facturas,
       COALESCE(SUM(i.totallines), 0) AS total
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO','CL') AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND i.dateinvoiced >= '2026-03-01' AND i.dateinvoiced < '2026-04-01'
LIMIT 500

-- Cumpleañeros de un mes en una org:
SELECT name, cargo, departamento, birthday
FROM adempiere.lve_empleadosactivos
WHERE EXTRACT(MONTH FROM birthday) = 5
  AND ad_org_id = (SELECT ad_org_id FROM adempiere.ad_org WHERE name ILIKE '%INPROA SANTONI%')
ORDER BY EXTRACT(DAY FROM birthday)
LIMIT 500

-- Top vendedores por venta neta:
SELECT au.name AS vendedor,
  COALESCE(SUM(CASE WHEN dt.docbasetype='ARI' THEN i.totallines WHEN dt.docbasetype='ARC' THEN -i.totallines ELSE 0 END),0) AS venta_neta
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
JOIN adempiere.ad_user au ON i.salesrep_id = au.ad_user_id
WHERE i.issotrx='Y' AND i.docstatus IN ('CO','CL') AND i.isactive='Y'
  AND i.c_currency_id = 205
  AND i.dateinvoiced >= '2026-02-01' AND i.dateinvoiced < '2026-03-01'
GROUP BY au.name ORDER BY venta_neta DESC
LIMIT 10
"""

# Tablas/views permitidas (whitelist)
_ALLOWED_TABLES = {
    # Views LVE oficiales
    "lve_empleadosactivos", "lve_empleadosinactivos", "lve_familygroupemployee",
    "lve_disponibilidadbancaria", "lve_disponibilidadbancariateso",
    "lve_disponibilidadbancariagerencia",
    "lve_saldosclientes", "lve_saldosproveedor", "lve_saldosproductor",
    "lve_invoice", "lve_invoiceinproa", "lve_invoiceaga",
    "lve_sales_book", "lve_sales_books",
    "lve_buy_book", "lve_buy_book_sumary",
    "lve_fact_acct", "lve_trialbalance",
    "lve_informepago", "lve_resumencobro",
    "lve_customer_statement", "lve_supplier_statement",
    "lve_analisisvencimientoinproa",
    "lve_analisisvencimientodetalladolar", "lve_analisisvencimientoinproadolar",
    "lve_compromisosbancarios",
    "lve_payment", "lve_payment_receipt",
    "lve_anticipoproductor", "lve_anticipoproveedor",
    "lve_guiasmovilizacion", "lve_guiagranelsindespacho", "lve_guiacaleta",
    "lve_facturasvsentregas",
    "lve_inventario_terminado", "lve_inventario_paddy", "lve_inventario_maiz",
    "lve_inventario_empaque", "lve_inventario_granos",
    "lve_inventario_repuesto", "lve_inventario_comercial",
    "lve_inventario_semilla", "lve_inventario_proceso", "lve_inventario_procmaiz",
    "lve_inventario_costo", "lve_inventario_maquinaria",
    "lve_existenciayubicacion", "lve_existenciaalmacenagroinproa",
    "lve_dotacionemp", "lve_prestsempleados", "lve_activos",
    # Tablas raw necesarias (no tienen view LVE equivalente)
    "c_invoice", "c_invoiceline", "c_bpartner", "c_bpartner_location",
    "c_payment", "c_order", "c_orderline",
    "c_doctype", "c_currency", "c_tax",
    "ad_user", "ad_org",
    "m_product", "m_product_category", "m_inout", "m_inoutline",
    "m_production", "m_productionline", "m_storageonhand",
    "m_movement", "m_movementline",
    "pp_product_bom", "pp_product_bomline",
    "m_warehouse", "m_locator",
    "hr_employee", "hr_department", "hr_job", "hr_process", "hr_movement",
    "fact_acct", "c_elementvalue",
    "c_bankaccount", "c_bank",
    "c_salesregion", "c_project",
    "c_allocationline", "c_allocationhdr",
    "c_paymentterm",
}

# Palabras prohibidas en SQL
_FORBIDDEN = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|EXECUTE|EXEC)\b',
    re.IGNORECASE,
)


def _validate_sql(sql: str) -> tuple[bool, str]:
    """Validate that the SQL is safe to execute.

    Returns (is_valid, error_message).
    """
    sql_clean = sql.strip().rstrip(";")

    # Must start with SELECT
    if not sql_clean.upper().startswith("SELECT"):
        return False, "Solo se permiten queries SELECT"

    # No forbidden keywords
    if _FORBIDDEN.search(sql_clean):
        match = _FORBIDDEN.search(sql_clean)
        return False, f"Operación prohibida: {match.group()}"

    # Check that all referenced tables are in the whitelist
    # Strategy: find "adempiere.TABLE" patterns (explicit schema) and
    # FROM/JOIN clauses. We must EXCLUDE "FROM" inside SQL functions like
    # EXTRACT(MONTH FROM col), LATERAL(...), etc.
    #
    # Step 1: Remove EXTRACT(...FROM...) patterns to avoid false positives
    sql_no_extract = re.sub(r'EXTRACT\s*\([^)]*\)', 'EXTRACT_REMOVED', sql_clean, flags=re.IGNORECASE)

    # Step 2: Find table references in the cleaned SQL
    table_refs = re.findall(
        r'(?:adempiere\.|\bFROM\s+|\bJOIN\s+)(\w+)',
        sql_no_extract,
        re.IGNORECASE,
    )
    for table in table_refs:
        table_lower = table.lower()
        if table_lower in ("adempiere", "extract_removed", "lateral", "select", "as"):
            continue
        if table_lower not in _ALLOWED_TABLES:
            return False, f"Tabla no permitida: {table_lower}. Solo se pueden consultar views lve_* y tablas del catálogo."

    # Must have LIMIT
    if "LIMIT" not in sql_clean.upper():
        sql_clean += " LIMIT 500"

    return True, sql_clean


def _execute_sql(sql: str, timeout_seconds: int = 30) -> tuple[list[str], list[tuple], float]:
    """Execute a validated SQL query against iDempiere (read-only).

    Returns (column_names, rows, elapsed_ms).
    """
    db = IdempiereSession()
    try:
        start = time.perf_counter()
        db.execute(text(f"SET statement_timeout = '{timeout_seconds * 1000}'"))
        result = db.execute(text(sql))
        cols = list(result.keys()) if result.returns_rows else []
        rows = result.fetchall() if result.returns_rows else []
        elapsed_ms = (time.perf_counter() - start) * 1000
        return cols, rows, elapsed_ms
    finally:
        db.close()


def _format_results_as_markdown(cols: list[str], rows: list[tuple], max_rows: int = 50) -> str:
    """Format SQL results as a markdown table for the LLM."""
    if not rows:
        return "La consulta no devolvió resultados."

    total = len(rows)
    display_rows = rows[:max_rows]

    lines = [
        f"| {' | '.join(cols)} |",
        f"| {' | '.join(['---'] * len(cols))} |",
    ]
    for row in display_rows:
        cells = []
        for val in row:
            if val is None:
                cells.append("")
            elif isinstance(val, float):
                cells.append(f"{val:,.2f}")
            elif isinstance(val, datetime):
                cells.append(val.strftime("%Y-%m-%d"))
            else:
                cells.append(str(val))
        lines.append(f"| {' | '.join(cells)} |")

    if total > max_rows:
        lines.append(f"\n*(Mostrando {max_rows} de {total} resultados)*")

    return "\n".join(lines)


async def process_with_sql_direct(
    message: str,
    history: list[tuple[str, str]] | None = None,
    org_ids: list[int] | None = None,
) -> dict | None:
    """Try to answer a user question using LLM-generated SQL.

    Returns a response dict if successful, or None if the approach failed
    (so the caller can fall back to the traditional agent routing).
    """
    llm = create_llm(temperature=0.0, max_tokens=2048, purpose="sql_direct")
    datetime_ctx = _build_datetime_context()

    # Step 1: Ask LLM to generate SQL
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    messages = [
        SystemMessage(content=(
            "Eres un asistente SQL experto para Alimentos Santoni, C.A. (Venezuela). "
            "Tu trabajo es convertir preguntas en lenguaje natural a queries SQL contra "
            "la base de datos iDempiere de Santoni.\n\n"
            f"{datetime_ctx}\n\n"
            f"{VIEWS_CATALOG}\n\n"
            "INSTRUCCIONES:\n"
            "1. Genera SOLO el SQL, sin explicaciones. No uses ```sql ni marcadores.\n"
            "2. El SQL debe ser un SELECT válido para PostgreSQL.\n"
            "3. Usa las tablas/views del catálogo con prefijo 'adempiere.'\n"
            "4. Incluye LIMIT 500 al final.\n"
            "5. SIEMPRE genera SQL para cualquier pregunta sobre datos. Solo responde NO_SQL para saludos (hola, gracias, chistes). Si la pregunta menciona empleados, ventas, compras, saldos, facturas, cumpleaños, producción, nómina, sueldos, departamentos → GENERA SQL.\n"
            "6. Para montos de ventas usa totallines (sin IVA). Para compras usa grandtotal.\n"
            "7. Si mencionan 'bolívares' o 'Bs' filtra c_currency_id = 205.\n"
            "8. Si mencionan 'dólares', 'USD' o 'divisas' filtra c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017).\n"
            "9. Para empleados activos SIEMPRE usa lve_empleadosactivos (NO hr_employee).\n"
            "10. Para 'sueldo promedio' o 'cuánto gana' usa AVG(total) de lve_empleadosactivos (total = sueldo+bonos).\n"
            "11. Para 'cumpleaños' o 'cumplen años' usa EXTRACT(MONTH FROM birthday) en lve_empleadosactivos. NUNCA respondas NO_SQL para cumpleaños.\n"
        )),
    ]

    # Add recent history for context
    if history:
        for role, content in history[-6:]:
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content[:200]))

    messages.append(HumanMessage(content=f"Genera el SQL para: {message}"))

    try:
        sql_response = await llm.ainvoke(messages)
        generated_sql = sql_response.content.strip()
    except Exception as exc:
        logger.warning("SQL Direct: LLM error generating SQL: %s", exc)
        return None

    # Check if LLM said it can't generate SQL
    if "NO_SQL" in generated_sql or not generated_sql.upper().startswith("SELECT"):
        logger.info("SQL Direct: LLM declined (NO_SQL or non-SELECT)")
        return None

    # Clean up any markdown formatting the LLM might have added
    generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()

    # Step 2: Validate
    is_valid, validated_sql = _validate_sql(generated_sql)
    if not is_valid:
        logger.warning("SQL Direct: validation failed: %s | SQL: %s", validated_sql, generated_sql[:200])
        return None

    logger.info("SQL Direct: executing: %s", validated_sql[:200])

    # Step 3: Execute
    try:
        cols, rows, elapsed_ms = _execute_sql(validated_sql)
    except Exception as exc:
        logger.warning("SQL Direct: execution error: %s | SQL: %s", exc, validated_sql[:200])
        return None

    if not rows and not cols:
        logger.info("SQL Direct: empty result")
        # Don't return None — return an explicit "no data" response
        # so the user knows the query ran but found nothing
        return {
            "response": (
                f"Consulté la base de datos con esta pregunta y no se encontraron "
                f"datos. Si crees que debería haber resultados, intenta reformular "
                f"la pregunta con más detalle (período, organización, moneda)."
            ),
            "agent_used": "sql_direct",
            "metadata": {
                "sql_generated": validated_sql,
                "rows_returned": 0,
                "elapsed_ms": elapsed_ms,
                "classification": "sql_direct",
                "has_data": False,
            },
        }

    # Step 4: Format results and ask LLM to create natural response
    results_md = _format_results_as_markdown(cols, rows)

    format_messages = [
        SystemMessage(content=(
            "Eres SantoniBot, el asistente de Alimentos Santoni. "
            "Recibes datos REALES de la base de datos de Santoni. "
            "Presenta los datos de forma clara en español. "
            "Usa formato venezolano para montos (punto=miles, coma=decimal). "
            "NUNCA inventes datos. Solo presenta lo que ves en la tabla. "
            "Si los datos incluyen montos, indica la moneda (Bs. o USD). "
            "Sé conciso pero completo."
        )),
        HumanMessage(content=(
            f"Pregunta del usuario: {message}\n\n"
            f"Datos obtenidos de iDempiere ({len(rows)} filas, {elapsed_ms:.0f}ms):\n\n"
            f"{results_md}"
        )),
    ]

    try:
        format_response = await llm.ainvoke(format_messages)
        final_response = format_response.content
    except Exception as exc:
        logger.warning("SQL Direct: LLM format error: %s", exc)
        # Fallback: return raw markdown table
        final_response = f"**Resultado de la consulta** ({len(rows)} filas):\n\n{results_md}"

    logger.info(
        "SQL Direct: success. %d rows in %.0fms. SQL: %s",
        len(rows), elapsed_ms, validated_sql[:100],
    )

    return {
        "response": final_response,
        "agent_used": "sql_direct",
        "metadata": {
            "sql_generated": validated_sql,
            "rows_returned": len(rows),
            "elapsed_ms": elapsed_ms,
            "classification": "sql_direct",
            "has_data": True,
        },
    }
