"""
Agente de Compras de Insumos - Alimentos Santoni
Especializado en: órdenes de compra, proveedores, inventarios de materiales,
precios históricos, tiempos de entrega.

Fuente de datos: c_invoice (issotrx='N'), c_invoiceline,
m_product, c_bpartner en iDempiere (PostgreSQL 13).
"""

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
import re

from app.services.query_service import build_supply_purchases, build_product_purchase_history


class ComprasInsumosAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "compras_insumos"

    @property
    def display_name(self) -> str:
        return "Compras de Insumos"

    @property
    def department(self) -> str:
        return "compras_insumos"

    @property
    def description(self) -> str:
        return (
            "Consultas de compras de insumos: órdenes de compra, proveedores, "
            "inventarios, precios históricos, tiempos de entrega"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Compras de Insumos de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión de compras de insumos y materiales.

CAPACIDADES:
- Resumen de compras por período (total facturas, montos)
- Top proveedores por volumen de compra
- Productos más comprados (insumos, materiales, empaques)
- Análisis mensual de compras

CONTEXTO iDEMPIERE:
- Facturas de compra: c_invoice (issotrx='N', docstatus='CO') - las facturas de compra tienen issotrx='N'
- Líneas de factura: c_invoiceline (m_product_id, qtyinvoiced, linenetamt)
- Proveedores: c_bpartner (isvendor='Y') - 26,070 socios de negocio
- Productos: m_product (40,766 productos) con m_product_category
- Monedas: VES (Bolívares, ID 205), USD (Dólares, ID 100)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- Campos fiscales: lve_controlnumber, withholdingamt (retenciones)

REGLAS:
- Responde siempre en español
- Presenta precios con moneda y unidad de medida
- Usa formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89)
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente

CONTEXTO:
- Responsables: Onofrio Gueccia, Jorge Chahine

FORMATOS DE FECHA SOPORTADOS:
- Rango con separadores: "01/01/2026 al 31/01/2026" o "01/01/26 al 31/01/26"
- Rango compacto: "01012026 al 31012026" o "010126 al 310126"
- Mes y año: "enero 2026"
- Solo año: "2026"

IMPORTANTE SOBRE PERÍODOS:
- Los datos corresponden al año actual por defecto, a menos que el usuario especifique otro año
- SIEMPRE indica claramente el período de los datos que estás presentando
- Si el usuario hace una pregunta amplia sin período, presenta datos del año actual y sugiere: "Si necesitas datos de otro período, indícame el año, mes o rango de fechas."
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto"""

    def get_sql_context(self) -> str:
        return """
Datos de compras de insumos en iDempiere:
- c_invoice: Facturas de compra (issotrx='N', dateinvoiced, grandtotal, totallines, docstatus)
- c_invoiceline: Líneas (m_product_id, qtyinvoiced, linenetamt, priceactual)
- c_bpartner: Proveedores (isvendor='Y', name, value)
- m_product: Productos/insumos (name, m_product_category_id)
- m_product_category: Categorías de productos
"""

    def _extract_product_search(self, message: str) -> str | None:
        """Extract product code or name from user message."""
        msg = message.strip()
        # Product code pattern: letters+dash+letters+dash+digits (e.g. REP-LAMI-0037)
        code_match = re.search(r'[A-Za-z]{2,}[-][A-Za-z]{2,}[-]\d+', msg)
        if code_match:
            return code_match.group()
        # Quoted product name
        quoted = re.search(r'["\u201c](.+?)["\u201d]', msg)
        if quoted:
            return quoted.group(1)
        # "producto X" or "producto: X"
        prod_match = re.search(r'producto[:\s]+(\S+)', msg, re.IGNORECASE)
        if prod_match:
            return prod_match.group(1)
        return None

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None

        label = build_period_label(date_from, date_to, mes, anio)

        # Check if user is searching for a specific product
        product_search = self._extract_product_search(message)
        if product_search:
            try:
                history = build_product_purchase_history(
                    product_search=product_search,
                    org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    mes=mes, anio=anio,
                )
                if history:
                    sections.append(
                        f"## Historial de Compras - Producto '{product_search}' ({len(history)} registros)"
                    )
                    sections.append(self._format_table(history))
                else:
                    sections.append(
                        f"## Búsqueda de Producto '{product_search}'\n"
                        f"No se encontraron compras para este producto en el período {label}."
                    )
            except Exception:
                pass

        # General summary (always include unless product-specific search returned data)
        if not sections or any(w in msg for w in ["resumen", "total", "cuánto", "cuanto"]):
            summary = build_supply_purchases(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_summary(summary, f"Resumen de Compras de Insumos - {label}"))

        return "\n\n".join(sections) if sections else None
