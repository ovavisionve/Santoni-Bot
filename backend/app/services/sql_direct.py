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

from app.config import get_settings
from app.database import IdempiereSession, SessionLocal
from app.services.llm_factory import create_llm, is_claude_available
from app.agents.base_agent import _build_datetime_context

logger = logging.getLogger("santonibot.sql_direct")


def _write_audit(
    message: str,
    sql_generated: str | None = None,
    sql_final: str | None = None,
    org_filter_injected: bool = False,
    rows_returned: int = 0,
    elapsed_ms: int = 0,
    format_failed: bool = False,
    status: str = "success",
    error_detail: str | None = None,
) -> int | None:
    """Guarda la traza del SQL en la tabla sql_audit de la DB local.

    Silencioso: si falla la escritura del audit log, no afecta la respuesta
    al usuario (la telemetría es best-effort).

    Returns el id de la fila insertada, o None si falló.
    """
    settings = get_settings()
    try:
        from app.models.sql_audit import SqlAudit
        db = SessionLocal()
        try:
            row = SqlAudit(
                message=message[:2000],  # truncado por seguridad
                sql_generated=sql_generated,
                sql_final=sql_final,
                org_filter_injected=org_filter_injected,
                rows_returned=rows_returned,
                elapsed_ms=elapsed_ms,
                format_failed=format_failed,
                llm_provider=(
                    "anthropic"
                    if (settings.use_claude_for_sql and is_claude_available())
                    else settings.ai_provider
                ),
                llm_model=(
                    settings.anthropic_model
                    if (settings.use_claude_for_sql and is_claude_available())
                    else settings.openrouter_model
                ),
                status=status,
                error_detail=error_detail[:2000] if error_detail else None,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row.id
        finally:
            db.close()
    except Exception as exc:
        # Nunca dejar que un bug del audit log rompa el bot
        logger.debug("SQL audit write failed (no crítico): %s", exc)
        return None


# ─────────────────────────────────────────────────────────────────────
# Detector de complejidad (para modo híbrido fino)
# ─────────────────────────────────────────────────────────────────────

# Palabras que indican query compleja (agregado, multi-tabla, financial).
# Si la pregunta del usuario contiene alguna de estas, se considera
# "compleja" y se usa Claude. Sino, DeepSeek maneja la query.
_COMPLEX_KEYWORDS = frozenset({
    # Agregados
    "total", "totales", "suma", "promedio", "ranking", "top ",
    "resumen", "desglose", "desglosado", "agrupado", "agrupada",
    # Financial
    "gasto", "gastos", "ingreso", "ingresos", "devengado", "deducido",
    "deducción", "deduccion", "utilidad", "balance", "saldo",
    "cobranza", "cobrado", "facturado", "facturación", "facturacion",
    "ausentismo", "ausencia",
    # Desglose por categoría
    "por zona", "por organización", "por organizacion", "por org",
    "por departamento", "por cargo", "por tipología", "por tipologia",
    "por moneda", "por cliente", "por proveedor", "por mes",
    "por tipo", "por categoria", "por categoría",
    # Comparaciones
    "comparar", "comparación", "comparacion", "versus",
    # Rangos temporales extensos
    "primer trimestre", "segundo trimestre", "tercer trimestre",
    "cuarto trimestre", "semestre", "año ", "anual", "acumulado",
    "histórico", "historico",
})

# Patrones SIMPLES — si matchea alguno de estos, la query se considera
# simple SIN evaluar los patrones complejos. Esto evita falsos positivos
# como "fecha de ingreso" → "ingreso" (palabra ambigua).
_SIMPLE_PATTERNS = frozenset({
    "cumpleañeros", "cumpleaños", "cumple año", "cumplen año", "nacidos",
    "fecha de ingreso", "fecha de nacimiento", "fecha de contratación",
    "cuántos empleados", "cuantos empleados",
    "cuántos activos", "cuantos activos",
    "cuantos trabajadores", "cuántos trabajadores",
    "quién es", "quien es", "quién cumple", "quien cumple",
    "dame la fecha", "dime la fecha",
})


def _is_complex_query(message: str, history: list | None = None) -> bool:
    """Clasifica una query como compleja o simple (heurística).

    Lógica:
      1. Si matchea un patrón SIMPLE → simple (prioritario, evita falsos positivos)
      2. Si el historial tiene > 3 turnos → compleja (follow-ups encadenados)
      3. Si matchea _COMPLEX_KEYWORDS → compleja
      4. Si menciona ≥ 2 meses → compleja
      5. Default → simple

    El default "simple" ahorra costo (DeepSeek). Las queries realmente
    complejas casi siempre tienen alguno de los patrones conocidos.
    """
    msg_lower = message.lower()

    # PASO 1: patrones simples tienen prioridad
    if any(p in msg_lower for p in _SIMPLE_PATTERNS):
        return False

    # PASO 2: historial largo = contexto complejo
    if history and len(history) > 6:  # 3 intercambios = 6 mensajes
        return True

    # PASO 3: keywords complejas
    if any(kw in msg_lower for kw in _COMPLEX_KEYWORDS):
        return True

    # PASO 4: rangos temporales (múltiples meses)
    import re as _re
    meses = _re.findall(
        r"\b(enero|febrero|marzo|abril|mayo|junio|julio|"
        r"agosto|septiembre|octubre|noviembre|diciembre)\b",
        msg_lower,
    )
    if len(meses) >= 2:
        return True

    # Default: simple (ahorra costo Claude)
    return False


def _create_sql_direct_llm(
    temperature: float = 0.0,
    max_tokens: int = 2048,
    user_message: str = "",
    history: list | None = None,
):
    """Create the LLM for SQL Direct (hybrid mode con opcional fine-grained).

    Modos:
      1. USE_CLAUDE_FOR_SQL=false
         → SQL Directo usa el AI_PROVIDER default (OpenRouter/DeepSeek).

      2. USE_CLAUDE_FOR_SQL=true + USE_CLAUDE_ONLY_FOR_COMPLEX=false (default)
         → Todas las queries de SQL Directo van a Claude (modo actual).

      3. USE_CLAUDE_FOR_SQL=true + USE_CLAUDE_ONLY_FOR_COMPLEX=true
         → Modo híbrido fino: Claude solo para queries complejas (agregados,
           financial, follow-ups largos); DeepSeek para simples (cumpleaños,
           conteos directos, búsquedas por nombre). Ahorro ~70% del costo de
           Claude manteniendo calidad donde importa.

    Fallback: si Claude falla o no está configurada, usa el AI_PROVIDER
    por defecto — SQL Directo sigue funcionando, solo con menor precisión.
    """
    settings = get_settings()
    claude_available = settings.use_claude_for_sql and is_claude_available()

    # Modo híbrido fino activo: elegir según complejidad
    if claude_available and settings.use_claude_only_for_complex:
        is_complex = _is_complex_query(user_message, history)
        if is_complex:
            logger.info(
                "SQL Direct híbrido: Claude (%s) para query compleja: '%s'",
                settings.anthropic_model, user_message[:60],
            )
            return create_llm(
                temperature=temperature,
                max_tokens=max_tokens,
                purpose="sql_direct_complex",
                provider="anthropic",
            )
        logger.info(
            "SQL Direct híbrido: %s para query simple: '%s'",
            settings.openrouter_model, user_message[:60],
        )
        return create_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            purpose="sql_direct_simple",
        )

    # Modo Claude completo (todas las queries a Claude)
    if claude_available:
        logger.debug(
            "SQL Direct: usando Claude (%s) por USE_CLAUDE_FOR_SQL=True",
            settings.anthropic_model,
        )
        return create_llm(
            temperature=temperature,
            max_tokens=max_tokens,
            purpose="sql_direct",
            provider="anthropic",
        )

    # Fallback: provider por defecto
    return create_llm(
        temperature=temperature,
        max_tokens=max_tokens,
        purpose="sql_direct",
    )

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
  edad (TEXT con formato "N años M meses D dias"),
  tservicio (TEXT con formato "N años M meses D dias" — NO es numérico),
  gender
IMPORTANTE: Para "sueldo promedio" usar AVG(total), NO AVG(sueldo). La columna 'sueldo' es solo el base.
IMPORTANTE: Para cumpleañeros SIEMPRE generar SQL con SELECT name, cargo, departamento, birthday.
  NUNCA responder NO_SQL para preguntas de cumpleaños — la columna birthday está en esta view.
⚠️ tservicio y edad son TEXTO (no numérico). Si necesitás años de servicio como número,
calculalo desde startdate: `EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate))`.
NO uses `FLOOR(tservicio)` ni `tservicio::numeric` — va a fallar con "invalid input syntax".
Para control de vacaciones (cálculo LOTT venezolano basado en antigüedad), usar startdate:
  `EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate))` = años enteros de servicio.

**lve_empleadosinactivos** — Empleados inactivos/retirados (misma estructura)

### RRHH — Nómina (movimientos de pago)
**hr_movement** — Filas de movimientos de nómina (cada concepto por empleado por período)
Columnas: hr_movement_id, hr_process_id, hr_concept_id, c_bpartner_id, ad_org_id,
  validfrom (fecha inicio del período), validto (fecha fin),
  amount (monto en Bs para conceptos de dinero; qty (cantidad para conceptos de días/horas))
IMPORTANTE: para montos $ usar `amount`. Para días/horas, usar `qty`. Muchos conceptos tienen
  AMBOS (ej: "Días de Reposo" tiene qty=días y amount=0).

**hr_concept** — Catálogo de conceptos de nómina (sueldos, asignaciones, deducciones, etc.)
Columnas: hr_concept_id, name (ej: 'Sueldo Mensual', 'Monto a deducir por Faltas y Atrasos'),
  value (código corto), hr_concept_category_id, type (E=Earning devengado, D=Deduction, etc.)
IMPORTANTE: para filtrar por concepto, usar `c.name ILIKE '%XXX%'`.
Conceptos comunes para ausentismo (buscar con ILIKE):
  - 'Faltas y Atrasos' → monto descontado
  - 'Permiso No Remunerado'
  - 'Permiso Remunerado'
  - 'Reposo Pagado', 'Reposo Medico'
  - 'Inasistencia Injustificada'
  - 'Días de Asignación de Permiso'
  - 'Días de Asignación de Reposo'
Conceptos de ingresos: 'Sueldo Mensual', 'Salario', 'Total Asignaciones', 'Provisión Utilidades'.
Conceptos de vacaciones (buscar 'vacacion' ILIKE): muchos tipos.

**hr_process** — Proceso de nómina (un proceso = correr una nómina para un período)
Columnas: hr_process_id, name, dateacct (fecha contable del proceso), datetrx (fecha
  de transacción), hr_payroll_id, hr_period_id, ad_org_id, docstatus, c_bpartner_id
⚠️ CRÍTICO: en Santoni, la columna NO se llama `hrdate` (ese es el nombre en otras
instalaciones de iDempiere). En Santoni la fecha del proceso es **`dateacct`**.
Si usás `hrdate` va a fallar con "column does not exist".
IMPORTANTE: para filtrar nóminas de un período, usar
  `p.dateacct >= 'YYYY-MM-DD' AND p.dateacct < 'YYYY-MM-DD'`
Alternativa más segura: filtrar por `hr_movement.validfrom` que SIEMPRE tiene la
fecha del período directamente (sin necesidad de JOIN con hr_process).

**hr_payroll** — Catálogo de tipos de nómina (Nómina Semanal, Quincenal, Directivos, etc.)
Columnas: hr_payroll_id, name (ej: 'Nómina Semanal OBREROS', 'Nómina Directivos'),
  value (código)
IMPORTANTE: para desglosar un resumen por tipo de nómina, JOIN hr_process.hr_payroll_id →
  hr_payroll.hr_payroll_id.

**hr_employee** — Metadata del empleado (NO usar para contar activos — usar lve_empleadosactivos).
Columnas: c_bpartner_id (foreign key a c_bpartner que tiene el nombre),
  hr_department_id, hr_job_id, startdate, enddate, isactive

**c_bpartner** (para nómina) — el NOMBRE real del empleado está en c_bpartner.name.
  JOIN: hr_movement.c_bpartner_id = c_bpartner.c_bpartner_id para traer el nombre.
  La cédula suele estar en c_bpartner.taxid.

**hr_department** — Departamentos (hr_department_id, name, value)
**hr_job** — Cargos (hr_job_id, name, value)

### Ventas — Facturas
**c_invoice** — Facturas de venta Y compra (tabla raw, funciona bien para ventas)
Columnas: c_invoice_id, c_bpartner_id, salesrep_id, c_currency_id,
  dateinvoiced, totallines (sin IVA), grandtotal (con IVA), docstatus,
  issotrx ('Y'=venta, 'N'=compra), ad_org_id, c_doctypetarget_id
IMPORTANTE: Para ventas filtrar issotrx='Y', docstatus IN ('CO','CL'), isactive='Y'
Para el tipo de documento: JOIN c_doctype dt ON c_doctypetarget_id = dt.c_doctype_id
  → dt.docbasetype: 'ARI'=factura o proforma (ambas comparten docbasetype),
                    'ARC'=nota de crédito
  → dt.name: distingue entre ProForma ('ProDolares', 'ProDolaresV', 'ProDolaresC',
             'Proforma') y Factura Legal ('AR Invoice Dolares', 'AR Invoice B/F/E',
             'Factura AGA', 'AR Invoice Dolares Valencia/Caracas'). Ver REGLA #8.

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
4. Para fechas SIEMPRE usar rangos `dateXX >= 'YYYY-MM-DD' AND dateXX < 'YYYY-MM-DD'`.
   NO usar `EXTRACT(YEAR FROM ...)` ni `EXTRACT(MONTH FROM ...)` en filtros de fecha
   (excepto para cumpleaños en `birthday`) porque rompe el uso de índices y causa
   timeouts de > 120s. Ejemplo OK: `dateinvoiced >= '2026-02-01' AND dateinvoiced < '2026-03-01'`.
5. Para ventas SIEMPRE filtrar: issotrx='Y', docstatus IN ('CO','CL'), isactive='Y'
6. Para compras a proveedores: issotrx='N' en c_invoice
7. Para compras a productores: usar c_order (guías), NO c_invoice
8. VES = c_currency_id = 205. USD = c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
9. Usar totallines (sin IVA) para montos de ventas, grandtotal (con IVA) para compras
10. Si no sabes qué columna tiene una tabla, haz tu mejor intento con las columnas del catálogo
11. SIEMPRE intenta generar SQL. Solo responde NO_SQL si la pregunta no tiene nada que ver con datos (ej: "hola", "gracias", chistes). Para cualquier pregunta sobre datos empresariales, genera el SQL.
12. **FILTRO DE ORGS DEMO (blacklist, no whitelist):** iDempiere trae orgs DEMO
    de fábrica (HQ, Store Central/East/North/South/West, Stores, Furniture,
    Fertilizer) y la org system-wide (nombre '*'). No son orgs reales de Santoni
    y pueden contaminar totales. Cuando el usuario NO especifique una organización
    concreta Y estés sumando/contando datos financieros (c_invoice, c_payment,
    c_order, fact_acct), **agregá SIEMPRE este filtro para excluirlas**:
    ```
    AND {alias}.ad_org_id IN (
      SELECT ad_org_id FROM adempiere.ad_org
      WHERE isactive = 'Y'
        AND name NOT ILIKE 'HQ' AND name NOT ILIKE 'Fertilizer'
        AND name NOT ILIKE 'Furniture'
        AND name NOT ILIKE 'Store Central' AND name NOT ILIKE 'Store East'
        AND name NOT ILIKE 'Store North' AND name NOT ILIKE 'Store South'
        AND name NOT ILIKE 'Store West' AND name NOT ILIKE 'Stores'
        AND name NOT ILIKE '*'
    )
    ```
    Este filtro es BLACKLIST: incluye TODAS las orgs reales (INPROA SANTONI,
    InproMaiz, AGROINPROA, AGROPECUARIA R.R., AGA AGRICOLA, INVERSIONES AGA,
    Santoni Service, Ocean Equipment Industries LLC, Venecauchos, Agro Import,
    y cualquier filial nueva que Santoni cree a futuro) y solo excluye las demos
    conocidas de iDempiere. Esto es mejor que whitelist porque no oculta orgs
    reales durmientes si el usuario pregunta histórico.
    Esto NO aplica para `lve_empleadosactivos` (ya filtra internamente) ni para
    queries de RRHH/cumpleaños.

## EJEMPLOS de queries comunes:

-- Sueldo promedio por organización:
SELECT AVG(sueldo) AS sueldo_promedio, COUNT(*) AS empleados
FROM adempiere.lve_empleadosactivos
WHERE ad_org_id = (SELECT ad_org_id FROM adempiere.ad_org WHERE name ILIKE '%InproMaiz%')
LIMIT 500

-- Facturas de venta por moneda y período (CON filtro blacklist de orgs demo):
SELECT COUNT(DISTINCT i.c_invoice_id) AS facturas,
       COALESCE(SUM(i.totallines), 0) AS total
FROM adempiere.c_invoice i
JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
WHERE i.issotrx = 'Y' AND i.docstatus IN ('CO','CL') AND i.isactive = 'Y'
  AND dt.docbasetype = 'ARI'
  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
  AND i.dateinvoiced >= '2026-03-01' AND i.dateinvoiced < '2026-04-01'
  AND i.ad_org_id IN (
    SELECT ad_org_id FROM adempiere.ad_org
    WHERE isactive = 'Y'
      AND name NOT ILIKE 'HQ' AND name NOT ILIKE 'Fertilizer'
      AND name NOT ILIKE 'Furniture'
      AND name NOT ILIKE 'Store Central' AND name NOT ILIKE 'Store East'
      AND name NOT ILIKE 'Store North' AND name NOT ILIKE 'Store South'
      AND name NOT ILIKE 'Store West' AND name NOT ILIKE 'Stores'
      AND name NOT ILIKE '*'
  )
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

-- Resumen de procesos de nómina por tipo (desglose COMPLETO + TOTAL en una query):
-- OJO: NO calcules el total sumando en tu cabeza al formatear — el SQL incluye
-- la fila TOTAL GENERAL vía UNION ALL para que el número sea exacto.
-- IMPORTANTE: hr_process usa `dateacct`, NO `hrdate`. Filtramos por m.validfrom
-- (en hr_movement) que es más directo.
WITH desglose AS (
    SELECT pr.name AS tipo_nomina,
           COUNT(DISTINCT p.hr_process_id) AS procesos,
           COUNT(DISTINCT m.c_bpartner_id) AS empleados,
           COALESCE(SUM(m.amount), 0) AS total_bs
    FROM adempiere.hr_movement m
    JOIN adempiere.hr_process p ON m.hr_process_id = p.hr_process_id
    JOIN adempiere.hr_payroll pr ON p.hr_payroll_id = pr.hr_payroll_id
    JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
    WHERE m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
      AND o.name ILIKE '%INPROA SANTONI%'
    GROUP BY pr.name
)
-- Usamos una columna 'sort_order' auxiliar para ordenar el resultado.
-- PostgreSQL NO acepta expresiones calculadas como ORDER BY tras UNION ALL,
-- pero SÍ acepta columnas del SELECT. Por eso agregamos sort_order (0/1).
SELECT tipo_nomina, procesos, empleados, total_bs, 0 AS sort_order FROM desglose
UNION ALL
SELECT 'TOTAL GENERAL',
       (SELECT SUM(procesos) FROM desglose),
       (SELECT SUM(empleados) FROM desglose),
       (SELECT SUM(total_bs) FROM desglose),
       1 AS sort_order
ORDER BY sort_order, total_bs DESC
LIMIT 500

-- Ausentismo por concepto en un período (AGROINPROA marzo 2026):
-- USAR FILTROS GENÉRICOS: %Permiso% captura "Dias de Asignacion de Permiso",
-- "Horas de Permiso No Remunerado", "Monto por Permiso Remunerado", etc.
-- Si usás sólo "%Permiso No Remunerado%" perdés las asignaciones de permiso.
-- Incluye TOTAL GENERAL vía UNION ALL para evitar que Claude sume mal.
WITH desglose AS (
    SELECT c.name AS concepto,
           COUNT(DISTINCT m.c_bpartner_id) AS empleados_afectados,
           COUNT(*) AS ocurrencias,
           COALESCE(SUM(m.amount), 0) AS monto_bs,
           COALESCE(SUM(m.qty), 0) AS cantidad
    FROM adempiere.hr_movement m
    JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
    JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
    WHERE m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
      AND o.name ILIKE '%AGROINPROA%'
      AND (c.name ILIKE '%Falta%' OR c.name ILIKE '%Permiso%'
           OR c.name ILIKE '%Inasistencia%' OR c.name ILIKE '%Reposo%'
           OR c.name ILIKE '%Ausencia%' OR c.name ILIKE '%Atraso%')
    GROUP BY c.name
)
SELECT concepto, empleados_afectados, ocurrencias, monto_bs, cantidad, 0 AS sort_order FROM desglose
UNION ALL
SELECT 'TOTAL GENERAL',
       NULL,
       (SELECT SUM(ocurrencias) FROM desglose),
       (SELECT SUM(monto_bs) FROM desglose),
       (SELECT SUM(cantidad) FROM desglose),
       1 AS sort_order
ORDER BY sort_order, monto_bs DESC
LIMIT 500

-- Nombres de trabajadores con un concepto específico (ej: Faltas y Atrasos):
-- El nombre real del empleado viene de c_bpartner, NO de hr_employee.
SELECT DISTINCT bp.name AS empleado,
       bp.taxid AS cedula,
       j.name AS cargo,
       COUNT(*) AS ocurrencias,
       COALESCE(SUM(m.amount), 0) AS monto_bs,
       COALESCE(SUM(m.qty), 0) AS qty
FROM adempiere.hr_movement m
JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
JOIN adempiere.c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_employee e ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
WHERE c.name ILIKE '%Faltas y Atrasos%'
  AND m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
  AND o.name ILIKE '%AGROINPROA%'
GROUP BY bp.name, bp.taxid, j.name
ORDER BY monto_bs DESC
LIMIT 500

-- Conceptos pagados/deducidos a UN empleado específico en un período:
SELECT c.name AS concepto,
       COUNT(*) AS ocurrencias,
       COALESCE(SUM(m.amount), 0) AS monto_bs,
       COALESCE(SUM(m.qty), 0) AS qty
FROM adempiere.hr_movement m
JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
JOIN adempiere.c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id
WHERE bp.name ILIKE '%Geovanna%'
  AND m.validfrom >= '2026-03-01' AND m.validfrom < '2026-04-01'
GROUP BY c.name
ORDER BY monto_bs DESC
LIMIT 500

-- Control vacacional (vacaciones pagadas/disfrutadas en un período).
-- NO intentar calcular "días acumulados LOTT" con joins complejos contra
-- múltiples tablas y funciones fecha — eso da timeout (>30s). En su lugar
-- listar los movimientos de nómina con concepto ILIKE '%vacacion%':
SELECT bp.name AS empleado,
       bp.taxid AS cedula,
       j.name AS cargo,
       c.name AS concepto,
       m.validfrom::date AS periodo_desde,
       m.validto::date AS periodo_hasta,
       m.qty AS dias,
       m.amount AS monto_bs
FROM adempiere.hr_movement m
JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
JOIN adempiere.c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_employee e ON e.c_bpartner_id = bp.c_bpartner_id
LEFT JOIN adempiere.hr_job j ON e.hr_job_id = j.hr_job_id
JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
WHERE c.name ILIKE '%vacacion%'
  AND m.validfrom >= '2026-04-01' AND m.validfrom < '2026-06-01'
  AND o.name ILIKE '%INPROA SANTONI%'
ORDER BY bp.name, m.validfrom
LIMIT 500

-- Ventas USD separando ProFormas de Facturas Legales (REGLA #8):
-- El usuario pregunta "ventas en dólares marzo 2026". Santoni distingue
-- ProFormas (USD real pre-factura) de Facturas Legales (cierre Bs/USD).
-- Devolvemos AMBAS métricas así el usuario entiende la diferencia.
WITH clasificacion AS (
    SELECT i.c_invoice_id, i.totallines, dt.name AS tipo_doc,
           dt.docbasetype,
           CASE
               WHEN dt.name ILIKE '%Proforma%' OR dt.name ILIKE '%ProDolares%'
                    OR dt.name ILIKE '%Pro-Forma%' THEN 'ProForma'
               ELSE 'FacturaLegal'
           END AS categoria
    FROM adempiere.c_invoice i
    JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id
    WHERE i.issotrx='Y' AND i.docstatus IN ('CO','CL') AND i.isactive='Y'
      AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)
      AND i.dateinvoiced >= '2026-03-01' AND i.dateinvoiced < '2026-04-01'
)
SELECT categoria,
       docbasetype,
       COUNT(*) FILTER (WHERE docbasetype='ARI') AS facturas,
       COUNT(*) FILTER (WHERE docbasetype='ARC') AS notas_credito,
       COALESCE(SUM(CASE WHEN docbasetype='ARI' THEN totallines
                         WHEN docbasetype='ARC' THEN -totallines ELSE 0 END), 0) AS neto_usd
FROM clasificacion
GROUP BY categoria, docbasetype
ORDER BY categoria, docbasetype
LIMIT 500

-- Empleados con antigüedad >= N años (usar EXTRACT sobre startdate, NO
-- tservicio que es texto). Ejemplo para priorización de vacaciones:
SELECT name, cargo, departamento, startdate::date AS ingreso,
       EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate))::int AS anos_servicio
FROM adempiere.lve_empleadosactivos v
JOIN adempiere.ad_org o ON v.ad_org_id = o.ad_org_id
WHERE EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate)) >= 5
  AND o.name ILIKE '%INPROA SANTONI%'
ORDER BY anos_servicio DESC
LIMIT 500

-- Ausentismo MULTI-MES (Enero, Febrero, Marzo) — patrón correcto para ORDER BY
-- tras UNION ALL con columna cronológica.
-- CLAVE: las columnas del ORDER BY DEBEN estar en TODAS las ramas del UNION,
-- aunque sean NULL en la fila TOTAL. PostgreSQL solo acepta columnas del
-- SELECT como ORDER BY tras UNION ALL, NUNCA expresiones CASE ni cálculos.
WITH desglose AS (
    SELECT EXTRACT(MONTH FROM m.validfrom)::int AS mes_num,
           TO_CHAR(m.validfrom, 'TMMonth') AS mes,
           c.name AS concepto,
           COUNT(DISTINCT m.c_bpartner_id) AS empleados,
           COUNT(*) AS ocurrencias,
           COALESCE(SUM(m.amount), 0) AS monto_bs
    FROM adempiere.hr_movement m
    JOIN adempiere.hr_concept c ON m.hr_concept_id = c.hr_concept_id
    JOIN adempiere.ad_org o ON m.ad_org_id = o.ad_org_id
    WHERE m.validfrom >= '2026-01-01' AND m.validfrom < '2026-04-01'
      AND o.name ILIKE '%AGROINPROA%'
      AND (c.name ILIKE '%Falta%' OR c.name ILIKE '%Permiso%'
           OR c.name ILIKE '%Inasistencia%' OR c.name ILIKE '%Reposo%')
    GROUP BY EXTRACT(MONTH FROM m.validfrom), TO_CHAR(m.validfrom, 'TMMonth'), c.name
)
-- FIJARSE: mes_num, mes, concepto, empleados, ocurrencias, monto_bs, sort_order
-- Las 7 columnas están en AMBAS ramas del UNION, con NULL donde no aplique.
SELECT mes_num, mes, concepto, empleados, ocurrencias, monto_bs, 0 AS sort_order
FROM desglose
UNION ALL
SELECT NULL AS mes_num, 'TOTAL GENERAL' AS mes, NULL AS concepto,
       NULL AS empleados,
       (SELECT SUM(ocurrencias) FROM desglose) AS ocurrencias,
       (SELECT SUM(monto_bs) FROM desglose) AS monto_bs,
       1 AS sort_order
ORDER BY sort_order, mes_num, monto_bs DESC  -- mes_num funciona porque
                                              -- está en AMBAS ramas (NULL en TOTAL)
LIMIT 500
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
    "hr_concept", "hr_concept_category", "hr_payroll", "hr_contract",
    "hr_period", "hr_year", "hr_attribute",
    # Nota: hr_rule NO existe en Santoni. Tampoco hr_payslip.
    "fact_acct", "c_elementvalue",
    "c_bankaccount", "c_bank",
    "c_salesregion", "c_project",
    "c_location", "c_region", "c_country", "c_city",
    "c_bp_group",  # tipología de cliente (Clientes, Proveedores, etc.)
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

    # Must start with SELECT or WITH (CTE prefix).
    # Antes solo aceptábamos SELECT, pero después de enseñarle a Claude
    # a usar `WITH desglose AS (...) SELECT ... UNION ALL ...` para totales
    # (REGLA #7), todos los SQL con CTE quedaban rechazados con
    # "Solo se permiten queries SELECT" y se marcaban como llm_declined.
    # Los CTE (WITH) son SELECTs también — solo con scope local.
    sql_upper = sql_clean.upper()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Solo se permiten queries SELECT (o WITH ... SELECT)"

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

    # Step 1.5: Extract CTE names declared with "WITH cte_name AS (...)".
    # Estas son tablas TEMPORALES válidas durante la ejecución del SQL —
    # NO están en _ALLOWED_TABLES (porque no son tablas reales de iDempiere)
    # pero sí son referencias legítimas que no hay que rechazar.
    #
    # Patrones que soporta:
    #   WITH desglose AS (SELECT ...)
    #   WITH desglose AS (SELECT ...), otro AS (SELECT ...)
    #   WITH RECURSIVE desglose AS (...)
    cte_names = set()
    # Caso 1: WITH primer_cte AS (...)
    for m in re.finditer(
        r'\bWITH\s+(?:RECURSIVE\s+)?(\w+)\s+AS\s*\(',
        sql_no_extract, re.IGNORECASE,
    ):
        cte_names.add(m.group(1).lower())
    # Caso 2: CTEs encadenados: "), nombre AS ("
    for m in re.finditer(r'\)\s*,\s*(\w+)\s+AS\s*\(', sql_no_extract, re.IGNORECASE):
        cte_names.add(m.group(1).lower())
    # Caso 3 (defensivo): cualquier "nombre AS (SELECT ..." que aparezca
    # después de WITH en la cabecera del query — maneja casos con saltos
    # de línea inusuales o comas mal puestas que los patrones anteriores
    # no atrapan. Solo si el SQL empieza con WITH.
    if sql_no_extract.upper().lstrip().startswith("WITH"):
        # Extraer el "bloque WITH" (desde WITH hasta el SELECT principal)
        # Heurística: los CTEs declarados antes del último paréntesis
        # cerrado que precede al SELECT final.
        for m in re.finditer(
            r'(?:^|[,\s])(\w+)\s+AS\s*\(\s*(?:SELECT|WITH)',
            sql_no_extract, re.IGNORECASE,
        ):
            name = m.group(1).lower()
            if name not in ("with", "select", "recursive", "as", "adempiere"):
                cte_names.add(name)

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
        # Aceptar nombres de CTEs declarados en el mismo SQL
        if table_lower in cte_names:
            continue
        if table_lower not in _ALLOWED_TABLES:
            return False, f"Tabla no permitida: {table_lower}. Solo se pueden consultar views lve_* y tablas del catálogo."

    # Must have LIMIT
    if "LIMIT" not in sql_clean.upper():
        sql_clean += " LIMIT 500"

    return True, sql_clean


# ─────────────────────────────────────────────────────────────────────
# Enforcement: forzar filtro de orgs reales en queries financieras
# ─────────────────────────────────────────────────────────────────────

# Tablas donde aplica el filtro de orgs demo (tienen ad_org_id y datos
# financieros contaminados por orgs de fábrica de iDempiere).
_ORG_ENFORCEMENT_TABLES = {
    "c_invoice", "c_payment", "c_order", "fact_acct",
}

# Nombres de orgs DEMO de iDempiere (a excluir explícitamente).
#
# 14/Abr/2026: cambio de estrategia whitelist → blacklist. Las 7 orgs reales
# de Santoni eran una lista cerrada, pero había orgs reales DURMIENTES que
# el whitelist ocultaba sin avisar (Ocean Equipment Industries LLC con
# $114,625 USD en marzo 2025, Venecauchos con 2,607 facturas históricas,
# Agro Import C.A. con 498 facturas). Si alguien preguntaba por histórico,
# el bot ocultaba datos legítimos silenciosamente.
#
# La blacklist lista solo las demos estándar de iDempiere (HQ, Store*,
# Furniture, Fertilizer, "*" system-wide). Cualquier otra org del ERP se
# considera real. Si Santoni crea una filial nueva, se incluye
# automáticamente sin cambios de código.
#
# Confirmado con consulta a ad_org del 14/Abr/2026: las 11 orgs listadas
# abajo tienen 0 facturas activas (o 10 obsoletas en el caso de HQ) —
# son definitivamente demos sin uso operativo.
_IDEMPIERE_DEMO_ORGS = (
    "HQ",
    "Fertilizer",
    "Furniture",
    "Store Central",
    "Store East",
    "Store North",
    "Store South",
    "Store West",
    "Stores",
    "*",  # la org system-wide, nunca debe sumar transacciones reales
)


def _build_santoni_org_filter(alias: str) -> str:
    """Construye el WHERE clause para excluir orgs demo de iDempiere.

    Estrategia blacklist: se incluyen TODAS las orgs del ERP excepto las
    ~10 demos conocidas de fábrica. Esto garantiza que:
      - Orgs reales durmientes (Ocean Equipment, Venecauchos, etc.) SÍ
        aparezcan en reportes históricos
      - Nuevas filiales de Santoni se incluyan automáticamente
      - Las demos de iDempiere queden excluidas (no contaminan totales)
    """
    names_sql = " AND ".join(
        f"name NOT ILIKE '{n}'" for n in _IDEMPIERE_DEMO_ORGS
    )
    return (
        f"{alias}.ad_org_id IN (SELECT ad_org_id FROM adempiere.ad_org WHERE "
        f"isactive = 'Y' AND {names_sql})"
    )


def _enforce_org_filter(sql: str) -> tuple[str, bool]:
    """Inyecta filtro de orgs reales de Santoni cuando falta (PROTECCIÓN DEFENSIVA).

    ⚠️ IMPORTANTE (14/Abr/2026): en la producción actual de Santoni las 7 orgs
    del ERP son TODAS reales (INPROA SANTONI, InproMaiz, AGROINPROA, etc.). No
    hay orgs demo de fábrica (HQ, Store Central, Ocean Equipment, Furniture,
    etc.). Esta función fue pensada para bloquear contaminación por orgs demo
    y por eso fue menos relevante de lo esperado al activar Claude.

    Se mantiene activa como PROTECCIÓN FUTURA para 3 escenarios:
      1. Si en el futuro se restaura un dump de iDempiere con orgs demo
         incluidas (es lo que pasa cuando un sysadmin hace un full import).
      2. Si se crea manualmente una org de prueba en el ERP sin eliminarla
         antes de producción.
      3. Si Santoni adquiere otra empresa y su ERP se migra con sus propias
         orgs demo.

    El problema real de totales inflados que pensábamos resolver aquí resultó
    ser AMBIGÜEDAD DE ORGANIZACIÓN (el usuario pregunta sin especificar qué
    org quiere y el bot asume "el grupo"). Ese problema se resuelve en el
    system prompt con la regla de "desglose por org obligatorio".

    Criterios para inyectar:
      - El SQL toca una de las tablas financieras (_ORG_ENFORCEMENT_TABLES)
      - Usa un alias identificable (ej. `FROM adempiere.c_invoice i`)
      - NO tiene ya un filtro `ad_org_id IN (...)` o `ad_org_id = N` en el
        WHERE clause (no en JOINs, que no son filtros)

    Returns (sql_modificado, se_inyecto_flag).
    """
    sql_upper = sql.upper()

    # Si el SQL ya tiene un filtro de ad_org_id en el WHERE clause, asumimos
    # que el LLM o el usuario ya restringieron y no tocamos (evita doble-filtro).
    # IMPORTANTE: solo contamos filtros en WHERE, NO en JOINs (un `ON o.ad_org_id
    # = i.ad_org_id` es una relación, no un filtro — el SQL seguiría incluyendo
    # todas las orgs demo).
    #
    # Heurística: cortamos el SQL en el WHERE y buscamos ad_org_id ahí (y en el
    # resto, excluyendo zonas de JOIN).
    where_match = re.search(r"\bWHERE\b", sql_upper)
    if where_match:
        # Todo lo que viene después del WHERE, hasta GROUP BY/ORDER BY/LIMIT
        where_and_after = sql_upper[where_match.end():]
        # Cortar cualquier subquery que venga después (simplificación)
        for tok in ("GROUP BY", "ORDER BY", "LIMIT"):
            m = re.search(rf"\b{tok}\b", where_and_after)
            if m:
                where_and_after = where_and_after[:m.start()]
                break
        # Buscar ad_org_id = N / IN (...) / etc. en el WHERE
        if re.search(r"\bAD_ORG_ID\s*(=|IN|<>|!=)", where_and_after):
            return sql, False

    # Buscar el primer alias de una tabla enforceable.
    # Pattern: FROM adempiere.TABLE [AS] ALIAS  (el alias es 1-2 letras típicamente)
    alias_to_enforce: str | None = None
    for table in _ORG_ENFORCEMENT_TABLES:
        m = re.search(
            rf"FROM\s+adempiere\.{table}\s+(?:AS\s+)?(\w+)\b",
            sql,
            re.IGNORECASE,
        )
        if m:
            alias_to_enforce = m.group(1)
            break

    if not alias_to_enforce:
        return sql, False

    # Inyectar el filtro justo antes del GROUP BY / ORDER BY / LIMIT.
    # Buscamos esos tokens y agregamos el AND antes.
    org_filter = _build_santoni_org_filter(alias_to_enforce)
    insertion = f" AND {org_filter}\n"

    # Regex para encontrar dónde cortar: el primer GROUP BY / ORDER BY / LIMIT
    # fuera de paréntesis. Como simplificación, buscamos la última ocurrencia
    # de cada uno y elegimos la de posición más baja (más temprana en el SQL).
    cut_tokens = ["GROUP BY", "ORDER BY", "LIMIT"]
    cut_pos = len(sql)
    for tok in cut_tokens:
        m = re.search(rf"\b{tok}\b", sql, re.IGNORECASE)
        if m and m.start() < cut_pos:
            cut_pos = m.start()

    modified = sql[:cut_pos].rstrip() + insertion + sql[cut_pos:]
    return modified, True


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
    # Hybrid mode: usa Claude para SQL gen + formateo si está configurada.
    # Si Claude no está, cae automáticamente al proveedor por defecto.
    # Pasamos user_message + history para que el modo híbrido fino pueda
    # decidir si es query compleja (Claude) o simple (DeepSeek).
    # Si el flag USE_CLAUDE_ONLY_FOR_COMPLEX está en False, se ignoran.
    llm = _create_sql_direct_llm(
        temperature=0.0,
        max_tokens=2048,
        user_message=message,
        history=history or [],
    )
    datetime_ctx = _build_datetime_context()

    # Step 1: Ask LLM to generate SQL
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    # ──────────────────────────────────────────────────────────────────
    # PROMPT CACHING (15/Abr/2026) — ahorro ~10x en costo de input
    # ──────────────────────────────────────────────────────────────────
    # El system prompt tiene ~10-12K tokens (catálogo completo + 8 reglas
    # + ejemplos). Es IDÉNTICO en todas las queries. Anthropic ofrece
    # prompt caching con 90% descuento en tokens cacheados.
    #
    # Estructura: separamos el prompt en 2 partes:
    #   - SYSTEM_PROMPT_CACHED: catálogo + reglas + instrucciones (cacheable)
    #   - datetime_ctx: varía cada 5-10 minutos (no cacheable, va aparte)
    #
    # Con cache_control={"type": "ephemeral"} Anthropic cachea el prefix
    # por ~5 min. Si hay tráfico continuo, el cache se renueva y nunca
    # expira — ahorro perpetuo del 90% en el system prompt.
    #
    # LangChain Anthropic soporta este formato desde v0.3+ usando content
    # blocks en lugar de strings planos.
    system_cacheable_text = (
            "Eres un asistente SQL experto para Alimentos Santoni, C.A. (Venezuela). "
            "Tu trabajo es convertir preguntas en lenguaje natural a queries SQL contra "
            "la base de datos iDempiere de Santoni.\n\n"
            "🎯 REGLA CRÍTICA #1 — DESGLOSE POR ORGANIZACIÓN (evitar ambigüedad):\n"
            "Santoni es un GRUPO de organizaciones (INPROA SANTONI es la principal; "
            "InproMaiz, AGROINPROA, AGROPECUARIA R.R., AGA AGRICOLA, INVERSIONES AGA, "
            "Santoni Service son subsidiarias activas; hay también orgs durmientes como "
            "Ocean Equipment Industries LLC, Venecauchos, Agro Import). Cuando el usuario "
            "pregunta por montos agregados (ventas, compras, cobranza, saldos) y NO "
            "menciona una organización específica, hay dos interpretaciones igual de "
            "válidas: 'el grupo consolidado' o 'la org principal'. No podés adivinar "
            "cuál. La SOLUCIÓN macro de Santoni es:\n\n"
            "  SI la pregunta es agregada (SUM/COUNT) contra c_invoice, c_payment, "
            "c_order o fact_acct, Y no menciona una org específica → GENERÁ el SQL "
            "con GROUP BY por organización (uniendo ad_org para traer el name). La "
            "respuesta final va a mostrar el desglose por org + el total consolidado.\n\n"
            "Ejemplo correcto para 'ventas USD marzo 2026' (sin org específica):\n"
            "```sql\n"
            "SELECT o.name AS organizacion,\n"
            "       COUNT(DISTINCT CASE WHEN dt.docbasetype='ARI' THEN i.c_invoice_id END) AS facturas,\n"
            "       COUNT(DISTINCT CASE WHEN dt.docbasetype='ARC' THEN i.c_invoice_id END) AS notas_credito,\n"
            "       COALESCE(SUM(CASE WHEN dt.docbasetype='ARI' THEN i.totallines "
            "WHEN dt.docbasetype='ARC' THEN -i.totallines ELSE 0 END), 0) AS venta_neta\n"
            "FROM adempiere.c_invoice i\n"
            "JOIN adempiere.c_doctype dt ON i.c_doctypetarget_id = dt.c_doctype_id\n"
            "JOIN adempiere.ad_org o ON i.ad_org_id = o.ad_org_id\n"
            "WHERE i.issotrx='Y' AND i.docstatus IN ('CO','CL') AND i.isactive='Y'\n"
            "  AND i.c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017)\n"
            "  AND i.dateinvoiced >= '2026-03-01' AND i.dateinvoiced < '2026-04-01'\n"
            "GROUP BY o.name\n"
            "ORDER BY venta_neta DESC\n"
            "LIMIT 500\n"
            "```\n\n"
            "Cuando el usuario SÍ mencione una org (ej. 'de INPROA SANTONI'), filtrá por\n"
            "esa org con `WHERE o.name ILIKE '%INPROA SANTONI%'` o equivalente, SIN "
            "GROUP BY. Si menciona VARIAS orgs ('INPROA SANTONI e InproMaiz'), usá IN + "
            "ILIKE. No apliques esta regla a queries sobre lve_empleadosactivos (RRHH), "
            "cumpleaños, nómina — esas son internas por diseño.\n\n"
            "🎯 REGLA CRÍTICA #2 — SEPARAR FACTURAS DE NOTAS DE CRÉDITO:\n"
            "Cuando contés documentos en c_invoice, NO agrupes facturas (ARI) con notas "
            "de crédito (ARC) en un solo COUNT. En Santoni, una factura grande puede "
            "ser anulada con una NC del mismo monto (ejemplo real: marzo 2026 tiene una "
            "AR Invoice de USD 9.4M con su correspondiente AR Credit Memo de USD 9.4M "
            "que la anula). Si sumás todo el COUNT, el usuario no se da cuenta que son "
            "cosas distintas. Usá siempre dos contadores:\n"
            "  `COUNT(DISTINCT CASE WHEN dt.docbasetype='ARI' THEN i.c_invoice_id END) AS facturas`\n"
            "  `COUNT(DISTINCT CASE WHEN dt.docbasetype='ARC' THEN i.c_invoice_id END) AS notas_credito`\n"
            "En la respuesta final mostrá ambos por separado. Para montos, usá la "
            "expresión neta (ARI positivo − ARC negativo) en un SUM con CASE como "
            "mostré arriba.\n\n"
            "🎯 REGLA CRÍTICA #3 — DESTACAR TRANSACCIONES GRANDES ANULATORIAS:\n"
            "Si el SQL devuelve resultados donde una sola factura (ARI) representa "
            ">20% del total bruto del período Y hay una NC (ARC) del mismo monto "
            "aproximado en el mismo período, probable es una transacción anulada. "
            "No podés detectar esto en el SQL inicial, pero al formatear la respuesta "
            "para el usuario, si ves esa situación, mencionala explícitamente: 'hay "
            "una factura de USD X que parece haber sido anulada con una NC del mismo "
            "monto — el neto del mes sería Y sin considerar esa anulación'.\n\n"
            "🎯 REGLA CRÍTICA #4 — SOS LA FUENTE DE DATOS, NO DERIVES A OTRA:\n"
            "NUNCA, JAMÁS respondas con frases tipo 'ver respuesta original', "
            "'(Se consultaron datos reales)', 'consulte al departamento', 'contacte "
            "Talento Humano', '(datos omitidos por confidencialidad)', 'Ejemplo 1 "
            "/ Ejemplo 2', 'los nombres exactos se omiten', ni datos placeholder. "
            "Vos SOS la fuente de datos de Santoni — no existe otra fuente para el "
            "usuario. Si el usuario pide detalle sobre un resumen que diste en un "
            "turno anterior (ej: primero diste totales, ahora te pide nombres), "
            "GENERÁ UNA NUEVA QUERY SQL que obtenga los detalles individuales desde "
            "iDempiere. Los datos del turno anterior NO están en tu contexto — "
            "tenés que ir a la DB a buscarlos de nuevo. Si realmente no podés "
            "generar SQL para la pregunta, respondé NO_SQL (el sistema hace fallback). "
            "Pero nunca des respuestas con plantillas que pretendan tener datos "
            "reales sin tenerlos.\n\n"
            "🎯 REGLA CRÍTICA #5 — DESGLOSES COMPLETOS, NO RESÚMENES INCOMPLETOS:\n"
            "Cuando el usuario pide un 'resumen', 'total', 'reporte' o 'índice' que "
            "involucre múltiples categorías (tipos de nómina, conceptos de ausentismo, "
            "organizaciones, departamentos, etc.), tu SQL debe devolver TODAS las "
            "categorías agrupadas — no una sola. NO uses LIMIT 1, NO filtres a un "
            "tipo específico, NO uses DISTINCT ON sin razón. Si el usuario dice "
            "'resumen de nómina', debe incluir TODOS los payrolls (semanal, quincenal, "
            "directivos, gerencial, obreros, etc.), no solo uno. El total global debe "
            "ser la SUMA de todo lo desglosado, NUNCA inferior a una categoría "
            "individual (si eso pasa, el SQL está mal). Aplicá este 'sanity check' "
            "mentalmente antes de entregar: 'el total que digo, ¿es la suma real de "
            "mi desglose?' Si no cuadra, el SQL está mal — regenéralo.\n\n"
            "🎯 REGLA CRÍTICA #6 — MAPEO COLUMNA → TABLA (Santoni específico):\n"
            "Guía rápida para evitar errores 'column does not exist':\n"
            "\n"
            "  Filtrar período en nómina → SIEMPRE `m.validfrom` (hr_movement).\n"
            "    No usar: p.hrdate, m.dateacct, m.startdate (no existen).\n"
            "    dateacct SOLO existe en hr_process; startdate SOLO en hr_period/hr_employee.\n"
            "\n"
            "  Nombre empleado en nómina → c_bpartner.name (hr_employee no tiene name).\n"
            "    JOIN c_bpartner bp ON m.c_bpartner_id = bp.c_bpartner_id.\n"
            "    Cédula: bp.taxid.\n"
            "\n"
            "  Región/zona de cliente → c_bpartner NO tiene c_region_id ni\n"
            "    c_salesregion_id directos. Hay que ir a través de c_bpartner_location:\n"
            "      JOIN c_bpartner_location bpl ON bp.c_bpartner_id = bpl.c_bpartner_id\n"
            "    Luego, para región geográfica: bpl.c_location_id → c_location.c_region_id\n"
            "    Para zona de venta: bpl.c_salesregion_id → c_salesregion (es la Zona\n"
            "    comercial tipo 'ZONA BARQUISIMETO', 'ZONA MARACAIBO').\n"
            "    NO uses ni `bp.c_salesregion_id` ni `loc.c_salesregion_id` —\n"
            "    la columna vive en `c_bpartner_location`.\n"
            "\n"
            "  Tablas que NO existen en Santoni: hr_payslip, hr_rule, hr_payroll_employee.\n"
            "  Usar hr_movement para cualquier consulta de nómina/pagos/ausentismo.\n\n"
            "🎯 REGLA CRÍTICA #7 — NO HAGAS ARITMÉTICA MENTAL (es fuente de errores):\n"
            "Los LLMs cometemos errores sistemáticos al sumar muchos números grandes\n"
            "en texto. Ejemplo real: 28 valores de millones de bolívares → sumé mal\n"
            "por ~11M (277M en lugar de 266M reales).\n"
            "POR ESTO, NUNCA calcules 'Total General' sumando mentalmente las filas\n"
            "del desglose al formatear la respuesta. En su lugar:\n"
            "  (a) Si generaste un SQL con GROUP BY y querés un total también, usá\n"
            "      UNION ALL con una columna auxiliar `sort_order` (0 para filas,\n"
            "      1 para el total). PostgreSQL NO acepta expresiones calculadas\n"
            "      en ORDER BY después de UNION ALL — solo columnas del SELECT.\n"
            "      Patrón correcto:\n"
            "        WITH desglose AS (SELECT ... GROUP BY categoria)\n"
            "        SELECT categoria, valor, 0 AS sort_order FROM desglose\n"
            "        UNION ALL\n"
            "        SELECT 'TOTAL GENERAL', SUM(valor), 1 AS sort_order FROM desglose\n"
            "        ORDER BY sort_order, valor DESC\n"
            "      ⚠️ NUNCA uses ORDER BY con EXPRESIONES después de UNION ALL:\n"
            "         NO: `ORDER BY (col = 'X')` → FeatureNotSupported\n"
            "         NO: `ORDER BY CASE WHEN ... END` → FeatureNotSupported\n"
            "         NO: `ORDER BY SUBSTRING(col, 1, 3)` → FeatureNotSupported\n"
            "         SÍ: `ORDER BY sort_order, valor DESC` (solo columnas del SELECT)\n"
            "         SÍ: `ORDER BY 1, 2 DESC` (por posición).\n"
            "      Si necesitás ordenar por mes/CASE/expresión tras UNION ALL,\n"
            "      calculalo DENTRO del SELECT como columna: `..., CASE mes WHEN 'Enero' THEN 1 ... END AS mes_num FROM ...`\n"
            "      y después usar `ORDER BY mes_num` (columna real, no expresión).\n"
            "      ⚠️ CRÍTICO: esa columna DEBE aparecer en TODAS las ramas del UNION,\n"
            "      no solo en una. Si la primera rama tiene `..., 0 AS sort_order, 1 AS mes_num`\n"
            "      la segunda rama TAMBIÉN tiene que tener esas 2 columnas, aunque sean\n"
            "      NULL. Si el ORDER BY referencia `mes_num` y solo está en la primera\n"
            "      rama, PostgreSQL tira 'column mes_num does not exist'.\n"
            "  (b) O en la respuesta, si el SQL no devolvió total explícito, NO lo\n"
            "      muestres. Di 'para ver el total general, regenerame con total'.\n"
            "  (c) Solo muestres totales que VIENEN TEXTUALMENTE del SQL. Los números\n"
            "      de las filas individuales SIEMPRE los mostrás exactos como vienen.\n"
            "Sanity check: ¿el 'total' que voy a mostrar está en los datos que recibí,\n"
            "o lo estoy sumando yo? Si es lo segundo — NO LO HAGAS.\n\n"
            "🎯 REGLA CRÍTICA #8 — FLUJO DE DOCUMENTOS (Orden → ProForma → Factura):\n"
            "El flujo oficial de Santoni para ventas es:\n"
            "  1. ORDEN DE VENTA (c_order) — disparador. No es un documento legal.\n"
            "     Prefijos típicos: PFV, PFC, PF. Vive en `c_order`.\n"
            "  2. PRO-FORMA (c_invoice con doctype 'ProDolares', 'ProDolaresV',\n"
            "     'ProDolaresC', 'Proforma') — el corazón del REPORTE USD. Son\n"
            "     facturas preliminares en dólares, antes de que se emita la\n"
            "     factura legal. Es lo que esalas/contabilidad usa para reportar\n"
            "     'ventas en dólares' del mes.\n"
            "  3. FACTURA LEGAL (c_invoice con doctype 'AR Invoice B', 'InvoiceE',\n"
            "     'InvoiceF', 'Factura AGA', 'AR Invoice Dolares', 'AR Invoice\n"
            "     Dolares Valencia/Caracas', etc.) — cierre legal en Bs. Lo que\n"
            "     se declara al SENIAT.\n"
            "\n"
            "TODOS los proformas tienen `docbasetype='ARI'` EN IDEMPIERE (no usan\n"
            "'ARP'). Lo que diferencia una PROFORMA de una FACTURA es el `dt.name`\n"
            "del c_doctype, NO el docbasetype. Por eso tenés que filtrar por\n"
            "`dt.name` cuando el usuario pide explícitamente 'facturas' vs\n"
            "'proformas' o reporta divergencias contra el reporte oficial.\n"
            "\n"
            "Patrón de filtro para separar proformas de facturas reales:\n"
            "  PROFORMAS:  dt.name ILIKE '%Proforma%' OR dt.name ILIKE '%ProDolares%'\n"
            "              OR dt.name ILIKE '%Pro-Forma%'\n"
            "  FACTURAS:   NOT (dt.name ILIKE '%Proforma%' OR dt.name ILIKE '%ProDolares%'\n"
            "                   OR dt.name ILIKE '%Pro-Forma%')\n"
            "\n"
            "HEURÍSTICA DEL USUARIO:\n"
            "  • 'ventas USD de marzo' / 'ventas en dólares de InproMaiz' →\n"
            "    devolvé AMBAS métricas separadas:\n"
            "       (a) Total ProFormas USD (el reporte USD oficial)\n"
            "       (b) Total Facturas legales USD (cierre SENIAT)\n"
            "    Y aclarale al usuario que son dos conceptos distintos.\n"
            "  • 'ventas de bolívares' / 'factura en Bs' → SOLO facturas legales\n"
            "    (excluí proformas, no tienen sentido en Bs).\n"
            "  • 'proformas emitidas' / 'reporte USD contabilidad' → SOLO proformas.\n"
            "  • Pregunta genérica ('total ventas marzo') → facturas legales, pero\n"
            "    mencionale que las proformas son otro conjunto si detectás que\n"
            "    hay muchas en el período.\n"
            "\n"
            "SANITY CHECK post-query: si el total USD que devolvés tiene avg por\n"
            "factura > $500K, probablemente estás sumando FACTURAS DOLARES (que\n"
            "tienen monto en Bs). Si el avg por factura < $100, probable es\n"
            "proforma de prueba. Valores USD reales de Santoni suelen estar entre\n"
            "$1K y $100K por factura.\n"
            "\n"
            "Este filtro NO aplica a `c_payment` (cobros) ni a `c_order`\n"
            "(órdenes) — esos no tienen el concepto de proforma.\n\n"
            # NOTA: el {datetime_ctx} NO se incluye acá — se concatena aparte
            # después para que el content cacheable sea 100% estático (sin
            # fechas que cambian). Eso permite que el cache se mantenga activo
            # al 100% entre requests.
            f"{VIEWS_CATALOG}\n\n"
            "INSTRUCCIONES:\n"
            "1. Genera SOLO el SQL, sin explicaciones. No uses ```sql ni marcadores.\n"
            "2. El SQL debe ser un SELECT válido para PostgreSQL.\n"
            "3. Usa las tablas/views del catálogo con prefijo 'adempiere.'\n"
            "4. Incluye LIMIT 500 al final.\n"
            "5. ⚠️ GENERÁ SQL SIEMPRE. La respuesta NO_SQL está PROHIBIDA "
            "excepto para: (a) saludos puros ('hola', 'gracias'), (b) chistes, "
            "(c) meta-preguntas ('qué puedes hacer'). Para CUALQUIER otra "
            "pregunta sobre datos de Santoni — empleados, ventas, compras, "
            "nómina, clientes, zonas, cumpleaños, etc. — HACÉ TU MEJOR INTENTO "
            "de SQL incluso si tenés dudas. El sistema tiene auto-retry: si tu "
            "primer intento falla, PostgreSQL te dice exactamente qué está mal "
            "y tenés 2 chances más de corregir. Si dudás entre NO_SQL y un SQL "
            "imperfecto, SIEMPRE elegí el SQL imperfecto — el sistema lo "
            "corrige. Decir NO_SQL cuando podrías intentar es FALLAR al usuario.\n"
            "6. Para montos de ventas usa totallines (sin IVA). Para compras usa grandtotal.\n"
            "7. Si mencionan 'bolívares' o 'Bs' filtra c_currency_id = 205.\n"
            "8. Si mencionan 'dólares', 'USD' o 'divisas' filtra c_currency_id IN (100,1000000,1000003,1000006,1000008,1000009,1000011,1000013,1000017).\n"
            "9. Para empleados activos SIEMPRE usa lve_empleadosactivos (NO hr_employee).\n"
            "10. Para 'sueldo promedio' o 'cuánto gana' usa AVG(total) de lve_empleadosactivos (total = sueldo+bonos).\n"
            "11. Para 'cumpleaños' o 'cumplen años' usa EXTRACT(MONTH FROM birthday) en lve_empleadosactivos. NUNCA respondas NO_SQL para cumpleaños.\n"
            "12. Para fechas usá siempre rangos `dateXX >= 'YYYY-MM-DD' AND dateXX < 'YYYY-MM-DD'` (NO EXTRACT en filtros salvo birthday). Esto evita timeouts por falta de índice.\n"
    )

    # Construir el system message con content blocks para habilitar cache.
    # Si el LLM es ChatAnthropic, usamos el formato [{type:text, cache_control:...}]
    # que Anthropic reconoce para caching. Si no (fallback a OpenRouter), usamos
    # string plano — OpenRouter ignora cache_control sin romper.
    settings = get_settings()
    # use_cache: solo si vamos a usar Anthropic realmente (no OpenRouter).
    # En modo híbrido fino, la decisión depende de la complejidad de la
    # query — si Claude NO se va a usar para esta query, no aplicamos
    # cache_control (OpenRouter lo ignora pero mejor no enviar el header).
    claude_available = settings.use_claude_for_sql and is_claude_available()
    if settings.use_claude_only_for_complex:
        use_cache = claude_available and _is_complex_query(message, history)
    else:
        use_cache = claude_available
    if use_cache:
        system_msg = SystemMessage(content=[
            {
                "type": "text",
                "text": system_cacheable_text,
                "cache_control": {"type": "ephemeral"},
            },
            # El datetime_ctx va DESPUÉS del cacheable, sin cache_control.
            # Así el contexto temporal se actualiza cada request sin invalidar
            # el prefix cacheado.
            {
                "type": "text",
                "text": f"\n\n{datetime_ctx}",
            },
        ])
    else:
        # Formato plano para proveedores que no soportan cache (DeepSeek/OpenRouter)
        system_msg = SystemMessage(
            content=system_cacheable_text + f"\n\n{datetime_ctx}"
        )

    messages = [system_msg]

    # Add recent history for context.
    # 14/Abr/2026: ampliamos el truncado de 200 → 1500 chars para respuestas
    # del asistente. 200 chars cortaban tablas markdown a mitad de header y el
    # LLM perdía el contexto de qué columnas/period había en la respuesta
    # anterior. 1500 chars es suficiente para header + 10-15 filas de tabla.
    # El mensaje del usuario se limita a 1000 chars para evitar prompts
    # gigantes cuando alguien pega un email/doc entero.
    if history:
        for role, content in history[-6:]:
            if role == "user":
                messages.append(HumanMessage(content=content[:1000]))
            elif role == "assistant":
                messages.append(AIMessage(content=content[:1500]))

    messages.append(HumanMessage(content=f"Genera el SQL para: {message}"))

    # ──────────────────────────────────────────────────────────────────
    # LOOP DE RETRY CON ERROR FEEDBACK (15/Abr/2026 — capa macro)
    # ──────────────────────────────────────────────────────────────────
    # Si el SQL falla (validation_failed o execute_error), le pasamos el
    # error al LLM como feedback y pedimos que lo regenere. Esto se hace
    # hasta MAX_RETRIES veces. Con esto el bot se auto-corrige sin
    # intervención humana ante errores del tipo "columna no existe",
    # "tabla no permitida", "tipo incorrecto", etc.
    #
    # Cada intento queda en sql_audit con status específico para
    # diagnosticar en qué intento tuvo éxito o qué error final quedó.
    MAX_RETRIES = 2  # 1 intento inicial + 2 retries = 3 intentos totales
    retry_count = 0
    sql_pre_enforce: str | None = None
    validated_sql: str | None = None
    enforced = False
    cols: list[str] = []
    rows: list = []
    elapsed_ms: float = 0.0
    last_error: str | None = None

    while retry_count <= MAX_RETRIES:
        # Generar SQL (primer intento o retry con error de contexto)
        try:
            sql_response = await llm.ainvoke(messages)
            generated_sql = sql_response.content.strip()
        except Exception as exc:
            logger.warning("SQL Direct: LLM error generating SQL: %s", exc)
            _write_audit(
                message=message,
                status=f"llm_gen_error{'_retry' + str(retry_count) if retry_count else ''}",
                error_detail=str(exc),
            )
            return None

        # Chequear si el LLM declinó.
        # Aceptar también SQL que empiece con WITH (CTE) — antes solo
        # SELECT era válido y los SQL con CTE generados por Claude
        # (después de REGLA #7 que les pide usar UNION ALL para totales)
        # se marcaban erróneamente como llm_declined.
        sql_upper_check = generated_sql.upper().strip()
        is_valid_start = (
            sql_upper_check.startswith("SELECT")
            or sql_upper_check.startswith("WITH ")
            or sql_upper_check.startswith("(SELECT")
        )
        if "NO_SQL" in generated_sql or not is_valid_start:
            logger.info("SQL Direct: LLM declined (NO_SQL or non-SELECT/WITH)")
            _write_audit(
                message=message,
                sql_generated=generated_sql[:500],
                status=f"llm_declined{'_retry' + str(retry_count) if retry_count else ''}",
            )
            return None

        # Limpiar markdown
        generated_sql = generated_sql.replace("```sql", "").replace("```", "").strip()

        # Validar
        is_valid, validated_sql = _validate_sql(generated_sql)
        if not is_valid:
            last_error = f"VALIDATION_FAILED: {validated_sql}"
            logger.warning(
                "SQL Direct: validation failed (intento %d/%d): %s | SQL: %s",
                retry_count + 1, MAX_RETRIES + 1, validated_sql, generated_sql[:200],
            )
            _write_audit(
                message=message,
                sql_generated=generated_sql,
                status=f"validation_failed{'_retry' + str(retry_count) if retry_count else ''}",
                error_detail=validated_sql,
            )
            if retry_count >= MAX_RETRIES:
                return None
            # Preparar mensaje de retry
            messages.append(AIMessage(content=generated_sql))
            messages.append(HumanMessage(content=(
                f"El SQL que generaste fue RECHAZADO por el validador con este error:\n"
                f"  {validated_sql}\n\n"
                "Regeneralo corrigiendo el problema. Recordá:\n"
                "- Todas las tablas deben tener prefijo 'adempiere.'\n"
                "- Solo podés usar views lve_* y tablas del catálogo\n"
                "- Solo SELECT (no INSERT/UPDATE/DELETE/etc)\n"
                "- Incluye LIMIT 500\n"
                "Devolvé SOLO el SQL corregido, sin explicaciones."
            )))
            retry_count += 1
            continue

        # Enforcement de filtro de orgs
        sql_pre_enforce = validated_sql
        validated_sql, enforced = _enforce_org_filter(validated_sql)
        if enforced:
            logger.info(
                "SQL Direct: filtro de orgs reales INYECTADO (Claude no lo aplicó)"
            )

        logger.info(
            "SQL Direct: executing (intento %d/%d): %s",
            retry_count + 1, MAX_RETRIES + 1, validated_sql[:300],
        )

        # Ejecutar
        try:
            cols, rows, elapsed_ms = _execute_sql(validated_sql)
            # ¡Éxito! Salir del loop de retry.
            if retry_count > 0:
                logger.info("SQL Direct: éxito en intento %d de %d", retry_count + 1, MAX_RETRIES + 1)
            break
        except Exception as exc:
            last_error = str(exc)
            logger.warning(
                "SQL Direct: execution error (intento %d/%d): %s | SQL: %s",
                retry_count + 1, MAX_RETRIES + 1, exc, validated_sql[:200],
            )
            _write_audit(
                message=message,
                sql_generated=sql_pre_enforce,
                sql_final=validated_sql,
                org_filter_injected=enforced,
                status=f"execute_error{'_retry' + str(retry_count) if retry_count else ''}",
                error_detail=str(exc),
            )
            if retry_count >= MAX_RETRIES:
                return None
            # Preparar mensaje de retry con el error de PostgreSQL
            # El error de psycopg2 trae el HINT de PostgreSQL que es oro puro
            # ej: "column p.hrdate does not exist. HINT: Perhaps you meant p.created or p.updated"
            messages.append(AIMessage(content=generated_sql))
            messages.append(HumanMessage(content=(
                f"El SQL que generaste falló al ejecutarse contra PostgreSQL con "
                f"este error:\n\n  {str(exc)[:600]}\n\n"
                "Regeneralo corrigiendo el problema específico. El error de "
                "PostgreSQL ya te dice qué está mal (columna inexistente, tipo "
                "incorrecto, etc.) y a veces sugiere la columna correcta con 'HINT:'. "
                "Seguí ese hint si está disponible.\n"
                "Devolvé SOLO el SQL corregido, sin explicaciones."
            )))
            retry_count += 1
            continue

    # Si salimos del loop sin éxito (no debería pasar por los return None), retornar
    if not cols and not rows:
        _write_audit(
            message=message,
            sql_generated=sql_pre_enforce,
            sql_final=validated_sql,
            org_filter_injected=enforced,
            status="retry_exhausted",
            error_detail=last_error,
        )
        return None

    if not rows and not cols:
        logger.info("SQL Direct: empty result")
        _write_audit(
            message=message,
            sql_generated=sql_pre_enforce,
            sql_final=validated_sql,
            org_filter_injected=enforced,
            rows_returned=0,
            elapsed_ms=int(elapsed_ms),
            status="empty_result",
        )
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

    format_failed = False
    try:
        format_response = await llm.ainvoke(format_messages)
        final_response = format_response.content
    except Exception as exc:
        # 14/Abr/2026: antes esto era silencioso (usuario veía tabla cruda
        # sin saber por qué). Ahora avisamos explícitamente para que el
        # usuario sepa que los datos son reales pero el formateo falló
        # (posiblemente por timeout de Claude o error del proxy).
        logger.error("SQL Direct: LLM format error (usando fallback markdown): %s", exc)
        format_failed = True
        final_response = (
            "⚠️ *(El formateo automático de la respuesta falló — "
            "mostrando datos crudos. Los números SÍ son correctos.)*\n\n"
            f"**Resultado de la consulta** ({len(rows)} filas):\n\n{results_md}"
        )

    logger.info(
        "SQL Direct: success. %d rows in %.0fms. SQL: %s",
        len(rows), elapsed_ms, validated_sql[:100],
    )

    # Registrar en audit log para diagnóstico posterior.
    # Si hubo retries antes del éxito, lo marcamos como 'success_retryN' para
    # medir la efectividad del auto-retry en datos reales.
    success_status = (
        "success" if retry_count == 0
        else f"success_after_retry{retry_count}"
    )
    audit_id = _write_audit(
        message=message,
        sql_generated=sql_pre_enforce,
        sql_final=validated_sql,
        org_filter_injected=enforced,
        rows_returned=len(rows),
        elapsed_ms=int(elapsed_ms),
        format_failed=format_failed,
        status=success_status,
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
            "format_failed": format_failed,
            "audit_id": audit_id,
        },
    }
