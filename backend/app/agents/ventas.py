"""
Agente de Ventas - Alimentos Santoni
AGENTE PRIORITARIO - Especializado en: ranking de ventas, clientes,
cobranza, zonas, vendedores, metas, productos.

Fuente de datos: c_invoice (issotrx='Y'), c_invoiceline, c_payment (isreceipt='Y'),
c_bpartner (iscustomer='Y'), ad_user (vendedores), m_product en iDempiere.
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
from app.services.query_service import (
    build_sales_summary,
    build_collection_summary,
    build_top_clients,
    build_overdue_receivables,
    build_sales_by_product,
    build_sales_orders,
    build_exchange_rates,
    build_sales_tax_summary,
    build_sales_by_branch,
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
9. Ventas por producto: top productos vendidos, ventas por categoría, SKUs
10. Órdenes de venta: pipeline por estado (borrador, en proceso, completada), vendedor, cliente, sucursal
11. Impuestos: IVA, retenciones y base imponible por factura de venta
12. Ventas por sucursal (C_Project)
13. Tasas de cambio recientes VES/USD

CONTEXTO iDEMPIERE (tablas de ventas):
- C_ORDER: Órdenes de venta (issotrx='Y')
- C_ORDERLINE: Líneas de orden de venta
- C_INVOICE: Facturas de venta (issotrx='Y', docstatus IN ('CO','CL')). CO=completada, CL=cerrada
- C_INVOICELINE: Líneas de factura (m_product_id, qtyinvoiced, linenetamt) — ventas por producto
- C_PAYMENT: Cobros (isreceipt='Y', docstatus IN ('CO','CL'))
- C_AllocationLine: Pagos asignados a facturas específicas
- C_BPARTNER: Terceros. ISCUSTOMER='Y'=cliente, ISVENDOR='Y'=proveedor, ISEMPLOYEE='Y'=empleado
- C_BPartner_Location: Dirección del cliente (vincula con zona de venta)
- C_SalesRegion: Zona/Región de ventas
- DCS_SalesRegionGroup: Grupo de región de ventas
- VENDEDORES: salesrep_id en facturas/órdenes → AD_USER (tabla de usuarios del sistema)
- M_PRODUCT: Productos. M_PRODUCT_CATEGORY: Categorías. ISKPI='Y' indica que es SKU
- C_UOM: Unidad de medida del producto
- M_PriceList / M_ProductPrice: Listas de precios y precios por producto
- C_Conversion_Rate: Tasa de cambio
- C_Tax: Impuestos
- Monedas: C_CURRENCY_ID=205 → Bolívares (Bs.), C_CURRENCY_ID<>205 → Dólar (USD)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- C_Project: Sucursales

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
- Si el usuario pide datos "en dólares", "en USD", "en DOL", los datos ya vienen filtrados SOLO por facturas en esa moneda
- Si el usuario pide datos "en bolívares", "en BS", "en VES", los datos ya vienen filtrados SOLO por facturas en bolívares
- Si no se especifica moneda, se muestran TODAS las facturas. Los datos incluyen columna "moneda" (Bs. o USD) para que indiques claramente la moneda de cada monto
- NUNCA intentes convertir montos entre monedas. Los datos son montos reales facturados en la moneda original
- La sección "por_moneda" muestra el desglose de totales por moneda

SOBRE VENDEDORES:
- La columna "vendedor" muestra el vendedor asignado a la factura/orden (salesrep_id → ad_user)
- Si dice "Sin Vendedor" significa que la factura no tiene vendedor asignado

SOBRE ÓRDENES DE VENTA:
- Los datos de órdenes incluyen: desglose por estado, por vendedor, por cliente, por sucursal y por moneda
- Presenta TODOS los desgloses disponibles en los datos recibidos

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
- En el top de clientes, el total_facturado ya es neto (restadas las NC del cliente)
- SIEMPRE presenta la venta neta como el dato principal y menciona las NC como referencia
- Ejemplo: "Venta neta: Bs. 1,500,000 (Facturado: Bs. 1,800,000 - NC: Bs. 300,000)"
- Las cuentas por cobrar vencidas NO incluyen notas de crédito"""

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Top N clientes por ventas netas (por período, zona, moneda, organización, vendedor)\n"
            "✅ Resumen de ventas: totales por zona, región, mes, moneda, vendedor\n"
            "✅ Resumen de cobranza: totales por método de pago y por cliente\n"
            "✅ Cuentas por cobrar vencidas: facturas impagadas con días de atraso\n"
            "✅ Ventas por producto: top productos vendidos, ventas por categoría, filtro por SKU\n"
            "✅ Órdenes de venta: pipeline por estado, vendedor, cliente, sucursal\n"
            "✅ Impuestos: desglose IVA/retenciones por factura de venta\n"
            "✅ Ventas por sucursal (C_Project)\n"
            "✅ Tasas de cambio recientes (VES/USD)\n"
            "\n❌ NO puedo consultar: metas de venta, presupuestos ni cotizaciones. "
            "Redirige al usuario al departamento correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos de ventas de iDempiere:
- c_invoice: Facturas (issotrx='Y', dateinvoiced, grandtotal, totallines, c_bpartner_id, salesrep_id, docstatus)
- c_invoiceline: Líneas de factura (m_product_id, qtyinvoiced, linenetamt) — ventas por producto
- c_order: Órdenes de venta (issotrx='Y', dateordered, grandtotal, salesrep_id)
- c_payment: Cobros (isreceipt='Y', datetrx, payamt, tendertype, c_bpartner_id)
- c_allocationline: Pagos asignados a facturas (c_payment_id, c_invoice_id)
- c_bpartner: Terceros (iscustomer='Y'=cliente, isvendor='Y'=proveedor)
- ad_user: Vendedores (salesrep_id → ad_user.ad_user_id)
- c_salesregion: Zonas de venta
- c_bpartner_location: Ubicación del cliente (c_salesregion_id)
- m_product: Productos (name, m_product_category_id)
- m_product_category: Categorías (iskpi='Y' = SKU)
- c_uom: Unidad de medida
- c_currency: Moneda (id=205 → Bs., otros → USD)
"""

    # ---- Extraction helpers (reused for history) ----

    _ZONES = [
        "portuguesa", "barinas", "lara", "carabobo", "aragua", "zulia",
        "maracaibo", "falcon", "margarita", "trujillo", "merida", "mérida",
        "tachira", "táchira", "guanare", "cabimas", "valencia", "caracas",
        "oriente", "santa barbara",
    ]
    _VENDEDORES = ["carlos matias", "lenny silva", "yuleidys gutierrez"]
    # Cada entrada es (keyword, display_name, filter_patterns).
    # - keyword: lo que buscamos en el mensaje del usuario (match por substring)
    # - display_name: etiqueta legible para los títulos en la respuesta
    # - filter_patterns: lista de patrones ILIKE que se pasan a
    #   `_add_org_name_filter` (combinados con OR).
    #
    # IMPORTANTE: solo mapeamos nombres EXPLÍCITOS. "inproa" solo (sin
    # "santoni", sin "maiz") NO aparece aquí porque es ambiguo — puede
    # referirse a INPROA SANTONI, InproMaiz o AGROINPROA. En ese caso el
    # agente pide clarificación al usuario en vez de adivinar
    # (ver `_is_ambiguous_org` y el bloque de clarificación en `fetch_data`).
    #
    # El orden importa: keywords más específicos (más largos) antes que
    # los cortos, porque `_extract_org_patterns` itera longest-first.
    _ORG_MAP = [
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
    _AMBIGUOUS_ORG_KEYWORDS = ("inproa",)
    _QUERY_TYPES = {
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

    _PRODUCT_KEYWORDS = [
        "harina", "arroz", "maiz", "maíz", "aceite", "sal",
        "avena", "azúcar", "azucar", "pasta",
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
    def _match_orgs(cls, msg: str) -> tuple[list[str], list[str]]:
        """Encuentra TODAS las orgs mencionadas en el mensaje.

        Itera los keywords más largos primero y consume (masking) cada
        match para evitar doble-conteo (ej: "inproa santoni" no debe
        volver a disparar un match por "inproa"/"santoni" sueltos).

        Returns:
            Tupla (displays, patterns):
              - displays: lista de nombres legibles (ej: ['INPROA SANTONI', 'InproMaiz'])
              - patterns: lista única de patrones ILIKE para el filtro SQL
        """
        masked = msg.lower()
        displays: list[str] = []
        patterns: list[str] = []
        sorted_map = sorted(cls._ORG_MAP, key=lambda x: -len(x[0]))
        for kw, display, pats in sorted_map:
            if kw in masked:
                masked = masked.replace(kw, " " * len(kw))
                if display not in displays:
                    displays.append(display)
                for p in pats or []:
                    if p not in patterns:
                        patterns.append(p)
        return displays, patterns

    @classmethod
    def _extract_org_name(cls, msg: str) -> str | None:
        """Devuelve una etiqueta legible con todas las orgs mencionadas.
        Si hay varias, las une con ' + '."""
        displays, _ = cls._match_orgs(msg)
        return " + ".join(displays) if displays else None

    @classmethod
    def _extract_org_patterns(cls, msg: str) -> list[str] | None:
        """Devuelve la lista de patrones ILIKE para pasar a
        `_add_org_name_filter`. Soporta múltiples orgs en un solo mensaje."""
        _, patterns = cls._match_orgs(msg)
        return patterns or None

    @classmethod
    def _is_ambiguous_org(cls, msg: str) -> bool:
        """True si el mensaje menciona un keyword ambiguo (ej: "inproa")
        sin un calificador más específico (ej: "inproa santoni",
        "inpromaiz", "agroinproa"). En ese caso el agente debe pedir
        clarificación al usuario en vez de adivinar."""
        displays, _ = cls._match_orgs(msg)
        if displays:
            # Ya hay al menos una org específica mencionada; no hay ambigüedad.
            return False
        msg_lower = msg.lower()
        return any(kw in msg_lower for kw in cls._AMBIGUOUS_ORG_KEYWORDS)

    @classmethod
    def _detect_query_type(cls, msg: str) -> str | None:
        msg_lower = msg.lower()
        for qtype, kws in cls._QUERY_TYPES.items():
            if any(w in msg_lower for w in kws):
                return qtype
        return None

    @classmethod
    def _extract_product_search(cls, msg: str) -> str | None:
        """Extract product name/keyword from the message."""
        msg_lower = msg.lower()
        for kw in cls._PRODUCT_KEYWORDS:
            if kw in msg_lower:
                return kw
        return None

    @classmethod
    def _extract_category_search(cls, msg: str) -> str | None:
        """Extract product category from the message."""
        import re
        m = re.search(r'categor[ií]a\s+(?:de\s+)?["\']?([^"\',.]+)', msg, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    def _extract_context_from_history(
        self, history: list[tuple[str, str]],
    ) -> dict:
        """Extract zona, vendedor, org_name, currency, query_type, and
        temporal context (date_from, date_to, mes, anio) from history."""
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
                    ctx["org_patterns"] = self._extract_org_patterns(content)
            if "currency" not in ctx:
                c = detect_currency(content)
                if c:
                    ctx["currency"] = c
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
            if "mes" not in ctx and "date_from" not in ctx:
                m, a = extract_month_year(content)
                if m:
                    ctx["mes"] = m
                    ctx["anio"] = a
            if len(ctx) >= 8:
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

    @staticmethod
    def _fmt_ves(value: float | int | None) -> str:
        """Format a number in Venezuelan style: 1.234.567,89"""
        if value is None:
            return "-"
        try:
            n = float(value)
        except (TypeError, ValueError):
            return str(value)
        # Format with US locale then swap separators
        s = f"{n:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")

    @classmethod
    def _format_vendedores_table(
        cls,
        rows: list[dict],
        title: str,
        limit: int = 10,
    ) -> str:
        """Pre-formatea la tabla de vendedores con columnas fijas, formato
        venezolano y ranking ya calculado, ordenada por VENTA NETA DESC.

        El LLM tiende a re-renderizar tablas con muchas columnas similares
        (total_bruto vs total) y mezcla valores entre filas. Esta tabla sale
        ya final para que el LLM solo la copie verbatim.
        """
        if not rows:
            return f"## {title}\n\nLa consulta no arrojó resultados para los filtros aplicados."

        # Ordenar por venta NETA descendente (consistente con el header)
        sorted_rows = sorted(
            rows,
            key=lambda r: r.get("total", 0) or 0,
            reverse=True,
        )[:limit]

        lines = [
            f"## {title}",
            "",
            "⚠️ TABLA FINAL PRE-FORMATEADA — COPIA EXACTA EN LA RESPUESTA:",
            "- NO reordenes las filas (ya están ordenadas por venta neta descendente)",
            "- NO renombres las columnas",
            "- NO cambies los valores ni los formates de otra manera",
            "- NO omitas ni agregues filas",
            "",
            "| # | Vendedor | Facturas | Notas Crédito | Venta Bruta (Bs.) | Monto NC (Bs.) | Venta Neta (Bs.) |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
        for i, r in enumerate(sorted_rows, start=1):
            lines.append(
                "| {pos} | {vend} | {fact} | {nc} | {bruto} | {mnc} | {neto} |".format(
                    pos=i,
                    vend=r.get("vendedor", "-"),
                    fact=r.get("facturas", 0) or 0,
                    nc=r.get("notas_credito", 0) or 0,
                    bruto=cls._fmt_ves(r.get("total_bruto", 0)),
                    mnc=cls._fmt_ves(r.get("monto_nc", 0)),
                    neto=cls._fmt_ves(r.get("total", 0)),
                )
            )
        return "\n".join(lines)

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
        # org_patterns es lo que se pasa al filtro SQL (lista de patrones
        # ILIKE). org_name es solo para mostrar en etiquetas/logs.
        org_patterns = self._extract_org_patterns(message)

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
            org_patterns = hist_ctx.get("org_patterns")
        if not currency_ids:
            currency_ids = hist_ctx.get("currency")

        # Clarificación de org ambigua: si el usuario dice "inproa" sin
        # calificar (INPROA SANTONI, InproMaiz o AGROINPROA) y el historial
        # tampoco tiene una org específica, pedimos clarificación en vez
        # de adivinar. Esto es crítico para QA: Darwin no puede validar
        # contra su Excel si el bot mezcla orgs silenciosamente.
        if self._is_ambiguous_org(message) and not org_patterns:
            return (
                "## ¿A qué organización te refieres?\n\n"
                "El grupo Santoni tiene varias organizaciones con **INPROA** en el "
                "nombre y cada una tiene datos distintos. Para darte el dato "
                "exacto, especifica cuál quieres:\n\n"
                "| Organización | Giro | Cómo pedirla |\n"
                "|---|---|---|\n"
                "| **INPROA SANTONI C.A.** | Procesadora de arroz | `INPROA SANTONI` |\n"
                "| **InproMaiz C.A.** | Procesadora de maíz | `InproMaiz` |\n"
                "| **AGROINPROA C.A.** | Empresa agrícola | `AGROINPROA` |\n\n"
                "**Tip:** puedes pedir varias a la vez, por ejemplo:\n"
                "- `Top 10 vendedores de febrero 2026 en INPROA SANTONI`\n"
                "- `Top 10 vendedores de febrero 2026 en INPROA SANTONI e InproMaiz`\n\n"
                "Si no especificas organización, consultaré todas las que tienes "
                "permitidas en tu usuario."
            )

        # CRÍTICO: si no hay moneda especificada, default a VES.
        # Si no, las queries suman Bs + USD como si fueran la misma moneda
        # y el total es incorrecto (ej: "Bs 739M" = Bs 738M + USD 1.4M).
        # Usuarios que quieran USD deben decir explícitamente "en dólares".
        if not currency_ids:
            currency_ids = [205]  # VES
        # Inherit temporal context from history for follow-ups
        if not date_from and not date_to and not mes:
            if hist_ctx.get("date_from"):
                date_from = hist_ctx["date_from"]
                date_to = hist_ctx["date_to"]
            elif hist_ctx.get("mes"):
                mes = hist_ctx["mes"]
                anio = hist_ctx.get("anio", anio)

        label = build_period_label(date_from, date_to, mes, anio)

        # Determine which sections to include
        query_type = self._detect_query_type(message)
        if not query_type and hist_ctx:
            query_type = hist_ctx.get("query_type")

        # If a specific product is mentioned, also activate "producto" section
        has_product_mention = self._extract_product_search(message) is not None

        try:
            if query_type == "vendedor" or any(w in msg for w in self._QUERY_TYPES["vendedor"]):
                org_label = f" - {org_name}" if org_name else ""
                data = build_sales_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                vendedor_data = data.get("por_vendedor", [])
                # Tabla pre-formateada con ranking por venta neta DESC.
                # Usamos una tabla fija para que el LLM no re-renderice y
                # mezcle columnas/valores (problema observado con DeepSeek v3).
                limit_match = re.search(r'top\s*(\d+)', msg)
                vend_limit = int(limit_match.group(1)) if limit_match else 10
                sections.append(
                    self._format_vendedores_table(
                        vendedor_data,
                        title=f"Top {vend_limit} Vendedores por Venta Neta ({label}{org_label})",
                        limit=vend_limit,
                    )
                )

            if query_type == "top" or any(w in msg for w in self._QUERY_TYPES["top"]):
                limit = 20
                limit_match = re.search(r'top\s*(\d+)', msg)
                if limit_match:
                    limit = int(limit_match.group(1))
                org_label = f" - {org_name}" if org_name else ""
                logger.info(
                    "Top clients query: mes=%s, anio=%s, date_from=%s, date_to=%s, "
                    "zona=%s, vendedor=%s, org_name=%s, org_ids=%s, currency_ids=%s",
                    mes, anio, date_from, date_to, zona, vendedor, org_name, org_ids, currency_ids,
                )
                data = build_top_clients(
                    limit=limit, zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                logger.info("Top clients result: %d rows", len(data) if isinstance(data, list) else -1)
                # If specific period returned empty, retry with full year
                if self._is_empty_result(data) and (mes or (date_from and date_to)):
                    logger.info("Fallback: retrying with full year %s (mes=None)", anio)
                    data_year = build_top_clients(
                        limit=limit, zona=zona, vendedor=vendedor, mes=None, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=None, date_to=None,
                        currency_ids=currency_ids, org_name=org_patterns,
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

            if query_type == "cobranza" or any(w in msg for w in self._QUERY_TYPES["cobranza"]):
                data = build_collection_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                sections.append(self._format_summary(data, f"Resumen de Cobranza - {label}"))

            if query_type == "vencidas" or any(w in msg for w in self._QUERY_TYPES["vencidas"]):
                data = build_overdue_receivables(org_ids=org_ids, salesrep_id=salesrep_id)
                sections.append(self._format_summary(data, "Cuentas por Cobrar Vencidas"))

            if query_type == "producto" or has_product_mention or any(w in msg for w in self._QUERY_TYPES["producto"]):
                product_search = self._extract_product_search(message)
                category_search = self._extract_category_search(message)
                only_skus = "sku" in msg
                org_label = f" - {org_name}" if org_name else ""
                data = build_sales_by_product(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                    product_search=product_search,
                    category_search=category_search,
                    only_skus=only_skus,
                )
                if data.get("top_productos"):
                    filter_label = ""
                    if product_search:
                        filter_label = f" - '{product_search}'"
                    elif category_search:
                        filter_label = f" - Categoría '{category_search}'"
                    sections.append(f"## Top Productos Vendidos ({label}{org_label}{filter_label})")
                    sections.append(self._format_table(data["top_productos"]))
                if data.get("notas_credito_por_producto"):
                    sections.append(f"## Notas de Crédito por Producto ({label}{org_label})")
                    sections.append(self._format_table(data["notas_credito_por_producto"]))
                if data.get("por_categoria"):
                    sections.append(f"## Ventas por Categoría de Producto ({label})")
                    sections.append(self._format_table(data["por_categoria"]))

            if query_type == "ordenes" or any(w in msg for w in self._QUERY_TYPES["ordenes"]):
                only_pending = any(w in msg for w in ["pendiente", "borrador", "proceso", "pipeline"])
                data = build_sales_orders(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                    only_pending=only_pending,
                )
                pending_label = " Pendientes" if only_pending else ""
                sections.append(self._format_summary(data, f"Órdenes de Venta{pending_label} - {label}"))

            if query_type == "impuestos" or any(w in msg for w in self._QUERY_TYPES["impuestos"]):
                data = build_sales_tax_summary(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                sections.append(self._format_summary(data, f"Desglose de Impuestos en Ventas - {label}"))

            if query_type == "sucursal" or any(w in msg for w in self._QUERY_TYPES["sucursal"]):
                data = build_sales_by_branch(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                sections.append(f"## Ventas por Sucursal - {label}")
                sections.append(self._format_table(data))

            if query_type == "tasa" or any(w in msg for w in self._QUERY_TYPES["tasa"]):
                data = build_exchange_rates(limit=20)
                sections.append("## Tasas de Cambio Recientes")
                sections.append(self._format_table(data))

            if not has_product_mention and (query_type == "ventas" or any(w in msg for w in self._QUERY_TYPES["ventas"]) or not sections):
                data = build_sales_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                # If specific period returned empty, retry with full year
                if self._is_empty_result(data) and (mes or (date_from and date_to)):
                    data_year = build_sales_summary(
                        zona=zona, vendedor=vendedor, mes=None, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=None, date_to=None,
                        currency_ids=currency_ids, org_name=org_patterns,
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

        except Exception as exc:
            logger.error("Error consultando datos de ventas: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Esto puede deberse a un problema de conexión con iDempiere. "
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None
