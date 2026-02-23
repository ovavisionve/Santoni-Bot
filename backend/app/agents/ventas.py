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
- Zonas: c_salesregion (vinculado via c_bpartner_location)
- Vendedores: salesrep_id en c_invoice apunta a c_bpartner
- Monedas: VES (Bolívares, ID 205), USD (Dólares, ID 100)
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
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

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

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates: try range first, then month/year
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)

        # If date range provided, nullify mes/anio (range takes priority)
        if date_from and date_to:
            mes = None

        vendedor = None
        for v in ["carlos matias", "lenny silva", "yuleidys gutierrez"]:
            if v in msg:
                vendedor = v.title()
                break

        zona = None
        for z in ["portuguesa", "barinas", "lara", "carabobo", "aragua", "zulia"]:
            if z in msg:
                zona = z.title()
                break

        label = build_period_label(date_from, date_to, mes, anio)

        if any(w in msg for w in ["top", "mejor", "ranking", "pareto", "principales"]):
            limit = 20
            limit_match = re.search(r'top\s*(\d+)', msg)
            if limit_match:
                limit = int(limit_match.group(1))
            data = build_top_clients(
                limit=limit, zona=zona, vendedor=vendedor, anio=anio,
                org_ids=org_ids, salesrep_id=salesrep_id,
                date_from=date_from, date_to=date_to,
            )
            sections.append(f"## Top {limit} Clientes por Ventas ({label})")
            sections.append(self._format_table(data))

        if any(w in msg for w in ["cobran", "cobro", "recauda", "pago"]):
            data = build_collection_summary(
                zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                org_ids=org_ids, salesrep_id=salesrep_id,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_summary(data, f"Resumen de Cobranza - {label}"))

        if any(w in msg for w in ["atrasa", "vencid", "pendiente", "deuda", "mora"]):
            data = build_overdue_receivables(org_ids=org_ids, salesrep_id=salesrep_id)
            sections.append("## Cuentas por Cobrar Vencidas")
            sections.append(self._format_table(data))

        if any(w in msg for w in ["venta", "factur", "ingreso", "volumen"]) or not sections:
            data = build_sales_summary(
                zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                org_ids=org_ids, salesrep_id=salesrep_id,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_summary(data, f"Resumen de Ventas - {label}"))

        return "\n\n".join(sections) if sections else None
