"""
Agente de Ventas - Alimentos Santoni
AGENTE PRIORITARIO - Especializado en: ranking de ventas, clientes,
cobranza, zonas, vendedores, metas, productos.

Fuente de datos: c_invoice (issotrx='Y'), c_payment (isreceipt='Y'),
c_bpartner en iDempiere (PostgreSQL 13).
"""

import logging
import re

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
    detect_currency,
)
from app.agents.keywords import (
    VENTAS_CLIENTES,
    VENTAS_FACTURACION,
    VENTAS_COBRANZA,
    VENTAS_CXC,
    VENTAS_ZONAS,
    matches_any,
)
from app.services.query_service import (
    build_sales_summary,
    build_collection_summary,
    build_top_clients,
    build_overdue_receivables,
    build_top_delinquent_clients,
)


class VentasAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "ventas"

    @property
    def display_name(self) -> str:
        return "Ventas"

    @property
    def department(self) -> str:
        return "ventas"

    @property
    def description(self) -> str:
        return (
            "Consultas de ventas: ranking por zona/vendedor/cliente, cobranza, "
            "facturación, metas, paretos, activación de clientes"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Ventas de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis comercial y gestión de ventas.

CAPACIDADES PRINCIPALES:
1. Ranking de ventas por zonas, vendedores y tipología del cliente
2. Identificación de zonas desatendidas
3. Paretos de clientes (análisis 80/20)
4. Top 20 mejores clientes por zona, por categoría, por vendedor y general
5. Activación y apertura de clientes
6. Ranking de cobranza por zona, vendedores y tipología
7. Detección de cuentas por cobrar más atrasadas
8. Cobranza diaria/semanal y comparativo vs metas

CONTEXTO iDEMPIERE:
- Facturas de venta: c_invoice (issotrx='Y', docstatus IN ('CO','CL')). CO=completada, CL=cerrada.
- Líneas de factura: c_invoiceline (m_product_id, qtyinvoiced, linenetamt)
- Cobros: c_payment (isreceipt='Y', docstatus IN ('CO','CL'))
- Clientes: c_bpartner - campos: ismayorista, isclap, ispublico, codigoventas
- Zonas: c_salesregion (vinculado via c_bpartner_location, una zona por cliente)
- Distribuidores: salesrep_id en c_invoice apunta a c_bpartner (son distribuidores/intermediarios, NO vendedores internos)
- NOTA: Los vendedores internos (Carlos Matias, Lenny Silva, etc.) NO están vinculados a las facturas en iDempiere
- Monedas: VES (Bolívares, ID 205), USD (Dólares, IDs múltiples)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- Campos fiscales: lve_controlnumber, withholdingamt (retenciones IVA)
- Productos: m_product, m_product_category

REGLAS:
- Responde siempre en español, de forma clara y orientada a la acción
- Cuando muestres rankings, usa tablas con posición, nombre, valor
- Destaca alertas: clientes morosos, zonas con caída de ventas, metas incumplidas
- Usa formato de moneda (Bs.) con separadores de miles (punto=miles, coma=decimal)
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa que no hay resultados
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta, di "No se encontraron datos" y sugiere consultas alternativas.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me" (ej: "mis ventas", "mi zona"), NO adivines. Pide al usuario que reformule especificando: la organización, vendedor, zona, período u otros datos necesarios.
- Presenta la información en tablas markdown cuando sea apropiado

FORMATOS DE FECHA SOPORTADOS:
- Rango con separadores: "01/01/2026 al 31/01/2026" o "01/01/26 al 31/01/26"
- Rango compacto: "01012026 al 31012026" o "010126 al 310126"
- Mes y año: "enero 2026"
- Solo año: "2026"

IMPORTANTE SOBRE PERÍODOS:
- Los datos corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos (ej: "Datos del año 2026")
- Si el usuario hace una pregunta amplia sin período, presenta datos del año actual y sugiere: "Si necesitas datos de otro período, indícame el año, mes o rango de fechas."
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto

SOBRE MONEDA:
- Si el usuario pide datos "en dólares", "en USD", "en DOL", los datos ya vienen filtrados SOLO por facturas en esa moneda. La sección "por_moneda" tendrá UNA SOLA fila (USD). Esto es correcto, NO falta nada.
- Si el usuario pide datos "en bolívares", "en BS", "en VES", los datos ya vienen filtrados SOLO por facturas en bolívares. La sección "por_moneda" tendrá UNA SOLA fila (Bs.). Esto es correcto, NO falta nada.
- Si no se especifica moneda, se muestran TODAS las facturas y "por_moneda" tendrá DOS filas (Bs. y USD).
- NUNCA intentes convertir montos entre monedas. Los datos son montos reales facturados en la moneda original.
- CUANDO VES UNA SOLA MONEDA en "por_moneda", es porque el usuario filtró por esa moneda. NO inventes datos de la otra moneda.

SOBRE DISTRIBUIDORES:
- La columna "distribuidor" muestra el distribuidor/intermediario asignado a la factura (salesrep_id)
- Los distribuidores NO son vendedores internos de Santoni. Son empresas o personas que intermedian la venta
- Si dice "Sin Distribuidor" significa que la factura no tiene distribuidor asignado

SOBRE TIPOLOGÍA:
- La columna "tipologia" muestra el grupo/categoría del cliente (c_bp_group)
- Refleja la clasificación que Santoni asigna a cada cliente en iDempiere

SOBRE REGIONES:
- Los datos incluyen agrupación por REGIONES macro de Venezuela:
  * Llanos (Portuguesa, Barinas, Cojedes, Apure)
  * Centro-Occidente (Lara, Yaracuy, Falcón)
  * Centro (Carabobo, Aragua)
  * Capital (Caracas, Miranda, La Guaira)
  * Occidente (Zulia, Santa Bárbara)
  * Andes (Trujillo, Mérida, Táchira)
  * Oriente (Margarita, Anzoátegui, Sucre, Monagas)
  * Guayana (Bolívar, Delta Amacuro, Amazonas)
- Si el usuario pide datos "por región", usa la sección "por_region"
- Si pide por "zona" o "estado", usa la sección "por_zona" (más detallada)

SOBRE NOTAS DE CRÉDITO:
- Las notas de crédito (NC) ya están SEPARADAS de las facturas en los datos
- Los totales de venta muestran: facturas brutas, notas de crédito y venta neta (facturas - NC)
- En los desgloses por zona, mes y moneda, el campo "total" ya es el neto (facturas - NC)
- En el top de clientes los datos incluyen: total_facturado (bruto), total_notas_credito (monto NC), y venta_neta (= facturado - NC). Usa SIEMPRE venta_neta como dato principal
- NUNCA inventes montos de notas de crédito. Los montos EXACTOS ya vienen en el campo total_notas_credito. Solo usa esos valores
- Ejemplo: "Venta neta: Bs. 1,500,000 (Facturado: Bs. 1,800,000 - NC: Bs. 300,000)"
- Las cuentas por cobrar vencidas NO incluyen notas de crédito"""

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Top N clientes por ventas netas (por período, zona, moneda, organización, distribuidor)\n"
            "✅ Resumen de ventas: totales por zona, región, mes, moneda, distribuidor\n"
            "✅ Resumen de cobranza: totales por método de pago y por cliente\n"
            "✅ Cuentas por cobrar vencidas: facturas impagadas con días de atraso\n"
            "\n❌ NO puedo consultar: metas de venta, presupuestos o cotizaciones. "
            "Redirige al usuario al departamento correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos de ventas de iDempiere:
- c_invoice: Facturas (issotrx='Y', dateinvoiced, grandtotal, totallines, c_bpartner_id, salesrep_id, docstatus)
- c_invoiceline: Líneas de factura (m_product_id, qtyinvoiced, linenetamt)
- c_payment: Pagos/cobros (isreceipt='Y', datetrx, payamt, tendertype: W=Transferencia, X=Efectivo, K=Cheque, C=Tarjeta Crédito, B=Tarjeta Débito, S=Transferencia Empresas, Z=Dólar Transferencia, Y=Dólar Efectivo, R=Dólar IGTF, E=Euro Efectivo, U=Euro Transferencia, A=Depósito Directo, G=Depósito Bancario, D=Débito Directo, T=Cuenta, P=Impuesto, Q=Giro, c_bpartner_id)
- c_bpartner: Clientes y vendedores (name, value, ismayorista, isclap, ispublico)
- c_salesregion: Zonas de venta
- c_bpartner_location: Ubicación del cliente (c_salesregion_id)
- m_product: Productos (name, m_product_category_id)
"""

    # ---- Extraction helpers (reused for history) ----

    # Doctype series pattern: "factura(s) B", "documento(s) B", "serie B", etc.
    _DOCTYPE_RE = re.compile(
        r'(?:facturas?|documentos?|serie)\s+'
        r'([A-Za-z])\b',
        re.IGNORECASE,
    )

    @classmethod
    def _extract_doctype(cls, msg: str) -> str | None:
        """Extract document type series from message.

        Maps user-facing series letters to iDempiere doctype name patterns:
        - "factura B" → "Invoice B" (matches "AR Invoice B")
        - "factura V" → "Invoice V" (matches "AR Invoice V")
        """
        m = cls._DOCTYPE_RE.search(msg)
        if m:
            letter = m.group(1).upper()
            return f"Invoice {letter}"
        return None

    _ZONES = [
        "portuguesa", "barinas", "lara", "carabobo", "aragua", "zulia",
        "maracaibo", "falcon", "margarita", "trujillo", "merida", "mérida",
        "tachira", "táchira", "guanare", "cabimas", "valencia", "caracas",
        "oriente", "santa barbara",
    ]
    _VENDEDORES = ["carlos matias", "lenny silva", "yuleidys gutierrez"]
    _ORG_MAP = [
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
    @classmethod
    def _extract_zona(cls, msg: str) -> str | None:
        msg_lower = msg.lower()
        for z in cls._ZONES:
            if z in msg_lower:
                return z.title()
        return None

    @classmethod
    def _extract_vendedor(cls, msg: str) -> str | None:
        msg_lower = msg.lower()
        for v in cls._VENDEDORES:
            if v in msg_lower:
                return v.title()
        return None

    @classmethod
    def _extract_org_name(cls, msg: str) -> str | None:
        msg_lower = msg.lower()
        for kw, val in cls._ORG_MAP:
            if kw in msg_lower:
                return val
        return None

    @classmethod
    def _detect_query_type(cls, msg: str) -> str | None:
        """Detect query type using centralized keywords."""
        msg_lower = msg.lower()
        # Client queries FIRST (before product, to avoid "InproMaiz" matching "maiz")
        if matches_any(msg_lower, VENTAS_CLIENTES):
            return "top"
        # Client status
        if ("activo" in msg_lower or "inactivo" in msg_lower) and "client" in msg_lower:
            return "cliente_status"
        # Product/category queries — AFTER client check
        _product_kw = {"producto", "productos", "categoría", "categoria", "harina",
                       "por producto", "por categoría", "por categoria",
                       "más vendido", "mas vendido", "principales producto"}
        # These only match as standalone words, not inside org names
        _product_standalone = {"arroz", "maíz", "maiz", "cereal", "avena", "empaque"}
        if any(kw in msg_lower for kw in _product_kw):
            return "producto"
        for kw in _product_standalone:
            if kw in msg_lower and kw not in "inpromaiz":
                # Verify it's not part of an org name
                import re as _re
                if _re.search(rf'\b{kw}\b', msg_lower):
                    return "producto"
        if matches_any(msg_lower, VENTAS_COBRANZA):
            return "cobranza"
        if matches_any(msg_lower, VENTAS_CXC):
            return "vencidas"
        # Visitas a clientes
        if "visita" in msg_lower or "visitas" in msg_lower:
            return "visitas"
        # Metas / presupuesto
        if "meta" in msg_lower or "metas" in msg_lower or "presupuesto" in msg_lower:
            return "metas"
        # Vendido vs producido
        if "produj" in msg_lower or "produjo" in msg_lower or "producción" in msg_lower or "producido" in msg_lower:
            if "vend" in msg_lower or "venta" in msg_lower:
                return "ventas_vs_produccion"
        if matches_any(msg_lower, VENTAS_FACTURACION):
            return "ventas"
        if matches_any(msg_lower, VENTAS_ZONAS):
            return "region"
        return None

    def _extract_context_from_history(
        self, history: list[tuple[str, str]],
    ) -> dict:
        """Extract zona, vendedor, org_name, currency, query_type, doctype,
        and temporal context (date_from, date_to, mes, anio) from history."""
        ctx: dict = {}
        if not history:
            return ctx
        for role, content in reversed(history):
            if role != "user":
                continue
            if "zona" not in ctx:
                z = self._extract_zona(content)
                if z:
                    ctx["zona"] = z
            if "vendedor" not in ctx:
                v = self._extract_vendedor(content)
                if v:
                    ctx["vendedor"] = v
            if "org_name" not in ctx:
                o = self._extract_org_name(content)
                if o:
                    ctx["org_name"] = o
            if "currency" not in ctx:
                c = detect_currency(content)
                if c:
                    ctx["currency"] = c
            if "doctype" not in ctx:
                dt = self._extract_doctype(content)
                if dt:
                    ctx["doctype"] = dt
            if "query_type" not in ctx:
                qt = self._detect_query_type(content)
                if qt:
                    ctx["query_type"] = qt
            # Inherit temporal context from history
            if "date_from" not in ctx:
                df, dt = extract_date_range(content)
                if df and dt:
                    ctx["date_from"] = df
                    ctx["date_to"] = dt
            if "mes" not in ctx and "date_from" not in ctx and "anio" not in ctx:
                m, a = extract_month_year(content)
                if m:
                    ctx["mes"] = m
                    ctx["anio"] = a
                elif re.search(r'20\d{2}', content):
                    ctx["anio"] = a
            if len(ctx) >= 9:
                break
        return ctx

    def _is_empty_result(self, data) -> bool:
        """Check if query result is empty (empty list or dict with all-zero totals)."""
        if isinstance(data, list):
            return len(data) == 0
        if isinstance(data, dict):
            totals = data.get("totales", {})
            if isinstance(totals, dict):
                return all(
                    v == 0 or v == 0.0
                    for v in totals.values()
                    if isinstance(v, (int, float))
                )
        return False

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        logger = logging.getLogger("santonibot.agents.ventas")
        msg = message.lower()
        sections = []

        # Extract dates: try range first, then month/year
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)

        # If date range provided, nullify mes/anio (range takes priority)
        if date_from and date_to:
            mes = None
            anio = None

        # Detect currency filter
        currency_ids = detect_currency(message)

        vendedor = self._extract_vendedor(message)
        zona = self._extract_zona(message)
        org_name = self._extract_org_name(message)
        doctype_name = self._extract_doctype(message)

        # Follow-up: carry over context from history
        hist_ctx: dict = {}
        if history:
            hist_ctx = self._extract_context_from_history(history)
        if not vendedor:
            vendedor = hist_ctx.get("vendedor")
        if not zona:
            zona = hist_ctx.get("zona")
        if not org_name:
            org_name = hist_ctx.get("org_name")
        if not currency_ids:
            currency_ids = hist_ctx.get("currency")
        if not doctype_name:
            doctype_name = hist_ctx.get("doctype")
        # Inherit temporal context from history for follow-ups
        _has_explicit_year = bool(re.search(r'20\d{2}', message))
        if not date_from and not date_to and not mes:
            if hist_ctx.get("date_from"):
                date_from = hist_ctx["date_from"]
                date_to = hist_ctx["date_to"]
            elif hist_ctx.get("mes"):
                mes = hist_ctx["mes"]
                anio = hist_ctx.get("anio", anio)
            elif hist_ctx.get("anio"):
                anio = hist_ctx["anio"]
        # Month extracted but no explicit year → inherit year from history
        elif mes and not _has_explicit_year and not date_from:
            if hist_ctx.get("anio"):
                anio = hist_ctx["anio"]

        label = build_period_label(date_from, date_to, mes, anio)

        # Determine which sections to include
        query_type = self._detect_query_type(message)
        if not query_type and hist_ctx:
            query_type = hist_ctx.get("query_type")

        try:
            if query_type == "producto":
                from app.services.query_service import build_sales_by_product
                # Extract product name from question
                _prod_names = ["harina", "arroz", "maíz", "maiz", "cereal", "avena", "empaque"]
                product_search = None
                for pn in _prod_names:
                    if pn in msg:
                        product_search = pn
                        break
                data = build_sales_by_product(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_name,
                    product_search=product_search,
                )
                sections.append(self._format_summary(data, f"Ventas por Producto - {label}"))

            elif query_type == "visitas":
                from app.services.query_service import build_client_visits
                data = build_client_visits(mes=mes, anio=anio, org_name=org_name)
                sections.append(self._format_summary(data, f"Visitas a Clientes - {label}"))

            elif query_type == "metas":
                from app.services.query_service import build_budget_comparison
                data = build_budget_comparison(mes=mes, anio=anio, org_ids=org_ids)
                sections.append(self._format_summary(data, f"Metas y Presupuesto - {label}"))

            elif query_type == "ventas_vs_produccion":
                from app.services.query_service import build_production_vs_sales
                data = build_production_vs_sales(mes=mes, anio=anio, org_ids=org_ids)
                sections.append(self._format_summary(data, f"Ventas vs Producción - {label}"))

            elif query_type == "cliente_status":
                from app.services.query_service import build_client_status
                data = build_client_status(org_name=org_name, anio=anio)
                sections.append(self._format_summary(data, f"Estado de Clientes - {org_name or 'Todas'}"))

            elif query_type == "top" or matches_any(msg, VENTAS_CLIENTES):
                limit = 20
                limit_match = re.search(r'top\s*(\d+)', msg)
                if limit_match:
                    limit = int(limit_match.group(1))
                org_label = f" - {org_name}" if org_name else ""
                # Default to Bs. when no currency specified to avoid mixing Bs+USD
                top_currency = currency_ids if currency_ids else [205]
                logger.info(
                    "Top clients query: mes=%s, anio=%s, date_from=%s, date_to=%s, "
                    "zona=%s, vendedor=%s, org_name=%s, org_ids=%s, currency_ids=%s",
                    mes, anio, date_from, date_to, zona, vendedor, org_name, org_ids, top_currency,
                )
                data = build_top_clients(
                    limit=limit, zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=top_currency, org_name=org_name,
                    doctype_name=doctype_name,
                )
                logger.info("Top clients result: %d rows", len(data) if isinstance(data, list) else -1)
                # If specific period returned empty, retry with full year
                if self._is_empty_result(data) and (mes or (date_from and date_to)):
                    logger.info("Fallback: retrying with full year %s (mes=None)", anio)
                    data_year = build_top_clients(
                        limit=limit, zona=zona, vendedor=vendedor, mes=None, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=None, date_to=None,
                        currency_ids=top_currency, org_name=org_name,
                        doctype_name=doctype_name,
                    )
                    logger.info("Fallback result: %d rows", len(data_year) if isinstance(data_year, list) else -1)
                    if not self._is_empty_result(data_year):
                        sections.append(
                            f"## Top {limit} Clientes por Ventas ({label}{org_label})\n"
                            f"**NOTA:** No se encontraron datos para {label}. "
                            f"Se muestran datos del Año {anio} completo como referencia."
                        )
                        sections.append(self._format_table(data_year))
                    else:
                        sections.append(f"## Top {limit} Clientes por Ventas ({label}{org_label})")
                        sections.append(self._format_table(data))
                else:
                    sections.append(f"## Top {limit} Clientes por Ventas ({label}{org_label})")
                    sections.append(self._format_table(data))

            if query_type == "cobranza" or matches_any(msg, VENTAS_COBRANZA):
                data = build_collection_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_name,
                )
                sections.append(self._format_summary(data, f"Resumen de Cobranza - {label}"))

            if query_type == "vencidas" or matches_any(msg, VENTAS_CXC):
                # Use aggregated view (by client) for morosos/deudores questions
                delinquent_data = build_top_delinquent_clients(org_ids=org_ids, salesrep_id=salesrep_id)
                sections.append("## Top Clientes Morosos (agregado por cliente)")
                sections.append(self._format_table(delinquent_data))
                # Also include individual invoices detail
                data = build_overdue_receivables(org_ids=org_ids, salesrep_id=salesrep_id)
                sections.append("## Detalle de Facturas Vencidas (top 50)")
                sections.append(self._format_table(data))

            if query_type == "ventas" or matches_any(msg, VENTAS_FACTURACION) or not sections:
                data = build_sales_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_name,
                    doctype_name=doctype_name,
                )
                # If specific period returned empty, retry with full year
                if self._is_empty_result(data) and (mes or (date_from and date_to)):
                    data_year = build_sales_summary(
                        zona=zona, vendedor=vendedor, mes=None, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=None, date_to=None,
                        currency_ids=currency_ids, org_name=org_name,
                        doctype_name=doctype_name,
                    )
                    if not self._is_empty_result(data_year):
                        sections.append(
                            f"**NOTA:** No se encontraron datos de ventas para {label}. "
                            f"Se muestran datos del Año {anio} completo como referencia."
                        )
                        sections.append(self._format_summary(data_year, f"Resumen de Ventas - Año {anio}"))
                    else:
                        sections.append(self._format_summary(data, f"Resumen de Ventas - {label}"))
                else:
                    sections.append(self._format_summary(data, f"Resumen de Ventas - {label}"))

                # When doctype is specified, also include top clients so the
                # LLM has real client names (prevents hallucination of clients)
                if doctype_name and not self._is_empty_result(data):
                    org_label = f" - {org_name}" if org_name else ""
                    top_currency = currency_ids if currency_ids else None
                    top_data = build_top_clients(
                        limit=20, zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=date_from, date_to=date_to,
                        currency_ids=top_currency, org_name=org_name,
                        doctype_name=doctype_name,
                    )
                    if not self._is_empty_result(top_data):
                        sections.append(f"## Top 20 Clientes — {doctype_name}{org_label} ({label})")
                        sections.append(self._format_table(top_data))

        except Exception as exc:
            logger.error("Error consultando datos de ventas: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Esto puede deberse a un problema de conexión con iDempiere. "
                f"Intenta de nuevo en unos momentos."
            )

        # Signal to LLM which currency filter was applied
        if sections and currency_ids:
            if currency_ids == [205]:
                currency_note = (
                    "⚠️ FILTRO DE MONEDA APLICADO: Los datos están filtrados SOLO por BOLÍVARES (Bs.). "
                    "NO existe datos de USD en esta consulta. NO inventes ni agregues datos de otra moneda."
                )
            else:
                currency_note = (
                    "⚠️ FILTRO DE MONEDA APLICADO: Los datos están filtrados SOLO por USD/DÓLARES. "
                    "NO existe datos de Bs. en esta consulta. NO inventes ni agregues datos de otra moneda."
                )
            sections.insert(0, currency_note)

        return "\n\n".join(sections) if sections else None
