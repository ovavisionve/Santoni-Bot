"""
Agente de Ventas - Alimentos Santoni
AGENTE PRIORITARIO - Especializado en: ranking de ventas, clientes,
cobranza, zonas, vendedores, metas, productos.

Fuente de datos: c_invoice (issotrx='Y'), c_payment (isreceipt='Y'),
c_bpartner en iDempiere (PostgreSQL 13).
"""

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
- Facturas de venta: c_invoice (issotrx='Y', docstatus='CO') - 447,386 facturas
- Líneas de factura: c_invoiceline (m_product_id, qtyinvoiced, linenetamt)
- Cobros: c_payment (isreceipt='Y', docstatus='CO') - 798,150 pagos
- Clientes: c_bpartner (26,070 registros) - campos: ismayorista, isclap, ispublico, codigoventas
- Zonas: c_salesregion (vinculado via c_bpartner_location, una zona por cliente)
- Distribuidores: salesrep_id en c_invoice apunta a c_bpartner (son distribuidores/intermediarios, NO vendedores internos)
- NOTA: Los vendedores internos (Carlos Matias, Lenny Silva, etc.) NO están vinculados a las facturas en iDempiere
- Monedas: VES (Bolívares, ID 205), USD (Dólares, IDs múltiples)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- Campos fiscales: lve_controlnumber, withholdingamt (retenciones IVA)
- Productos: m_product (40,766 productos), m_product_category

REGLAS:
- Responde siempre en español, de forma clara y orientada a la acción
- Cuando muestres rankings, usa tablas con posición, nombre, valor
- Destaca alertas: clientes morosos, zonas con caída de ventas, metas incumplidas
- Usa formato de moneda (Bs.) con separadores de miles (punto=miles, coma=decimal)
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa que no hay resultados
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

SOBRE DISTRIBUIDORES:
- La columna "distribuidor" muestra el distribuidor/intermediario asignado a la factura (salesrep_id)
- Los distribuidores NO son vendedores internos de Santoni. Son empresas o personas que intermedian la venta
- Si dice "Sin Distribuidor" significa que la factura no tiene distribuidor asignado

SOBRE TIPOLOGÍA:
- La columna "tipologia" muestra el grupo/categoría del cliente (c_bp_group)
- Refleja la clasificación que Santoni asigna a cada cliente en iDempiere"""

    def get_sql_context(self) -> str:
        return """
Datos de ventas de iDempiere:
- c_invoice: Facturas (issotrx='Y', dateinvoiced, grandtotal, totallines, c_bpartner_id, salesrep_id, docstatus)
- c_invoiceline: Líneas de factura (m_product_id, qtyinvoiced, linenetamt)
- c_payment: Pagos/cobros (isreceipt='Y', datetrx, payamt, tendertype, c_bpartner_id)
- c_bpartner: Clientes y vendedores (name, value, ismayorista, isclap, ispublico)
- c_salesregion: Zonas de venta
- c_bpartner_location: Ubicación del cliente (c_salesregion_id)
- m_product: Productos (name, m_product_category_id)
"""

    # ---- Extraction helpers (reused for history) ----

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
    _QUERY_TYPES = {
        "top": ["top", "mejor", "ranking", "pareto", "principales"],
        "cobranza": ["cobran", "cobro", "recauda", "pago"],
        "vencidas": ["atrasa", "vencid", "pendiente", "deuda", "mora"],
        "ventas": ["venta", "factur", "ingreso", "volumen"],
    }

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
        msg_lower = msg.lower()
        for qtype, kws in cls._QUERY_TYPES.items():
            if any(w in msg_lower for w in kws):
                return qtype
        return None

    def _extract_context_from_history(
        self, history: list[tuple[str, str]],
    ) -> dict:
        """Extract zona, vendedor, org_name, currency, query_type from history."""
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
            if "query_type" not in ctx:
                qt = self._detect_query_type(content)
                if qt:
                    ctx["query_type"] = qt
            if len(ctx) >= 5:
                break
        return ctx

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates: try range first, then month/year
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)

        # If date range provided, nullify mes/anio (range takes priority)
        if date_from and date_to:
            mes = None

        # Detect currency filter
        currency_ids = detect_currency(message)

        vendedor = self._extract_vendedor(message)
        zona = self._extract_zona(message)
        org_name = self._extract_org_name(message)

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

        label = build_period_label(date_from, date_to, mes, anio)

        # Determine which sections to include
        query_type = self._detect_query_type(message)
        if not query_type and hist_ctx:
            query_type = hist_ctx.get("query_type")

        if query_type == "top" or any(w in msg for w in self._QUERY_TYPES["top"]):
            limit = 20
            limit_match = re.search(r'top\s*(\d+)', msg)
            if limit_match:
                limit = int(limit_match.group(1))
            org_label = f" - {org_name}" if org_name else ""
            data = build_top_clients(
                limit=limit, zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                org_ids=org_ids, salesrep_id=salesrep_id,
                date_from=date_from, date_to=date_to,
                currency_ids=currency_ids, org_name=org_name,
            )
            sections.append(f"## Top {limit} Clientes por Ventas ({label}{org_label})")
            sections.append(self._format_table(data))

        if query_type == "cobranza" or any(w in msg for w in self._QUERY_TYPES["cobranza"]):
            data = build_collection_summary(
                zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                org_ids=org_ids, salesrep_id=salesrep_id,
                date_from=date_from, date_to=date_to,
                currency_ids=currency_ids, org_name=org_name,
            )
            sections.append(self._format_summary(data, f"Resumen de Cobranza - {label}"))

        if query_type == "vencidas" or any(w in msg for w in self._QUERY_TYPES["vencidas"]):
            data = build_overdue_receivables(org_ids=org_ids, salesrep_id=salesrep_id)
            sections.append("## Cuentas por Cobrar Vencidas")
            sections.append(self._format_table(data))

        if query_type == "ventas" or any(w in msg for w in self._QUERY_TYPES["ventas"]) or not sections:
            data = build_sales_summary(
                zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                org_ids=org_ids, salesrep_id=salesrep_id,
                date_from=date_from, date_to=date_to,
                currency_ids=currency_ids, org_name=org_name,
            )
            sections.append(self._format_summary(data, f"Resumen de Ventas - {label}"))

        return "\n\n".join(sections) if sections else None
