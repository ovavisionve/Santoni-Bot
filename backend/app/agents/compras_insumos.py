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

    # Words that indicate a general query (not a specific product search)
    _GENERAL_KEYWORDS = [
        "resumen", "total", "proveedor", "proveedores", "mensual",
        "principales", "inventario", "stock", "todos los insumos",
        "cuánto se", "cuanto se", "cuánto factur", "cuanto factur",
    ]

    def _extract_product_search(self, message: str) -> str | None:
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

        # Product code pattern: letters+dash+letters+dash+digits (e.g. REP-LAMI-0037)
        code_match = re.search(r'[A-Za-z]{2,}[-][A-Za-z]{2,}[-]\d+', msg)
        if code_match:
            return code_match.group()

        # Quoted product name
        quoted = re.search(r'["\u201c](.+?)["\u201d]', msg)
        if quoted:
            return quoted.group(1)

        # "producto X" or "producto: X"
        prod_match = re.search(
            r'producto[:\s]+(.+?)(?:\s+(?:en|del|desde|este)\b|\s*[?]|$)',
            msg_lower,
        )
        if prod_match and len(prod_match.group(1).strip()) >= 3:
            return prod_match.group(1).strip()

        # "compras de {product}" / "historial de compras de {product}"
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
            # Skip generic terms
            if len(product) >= 3 and product not in (
                'insumos', 'los insumos', 'todos', 'todos los', 'todos los insumos',
            ):
                return product

        # "cuántas {product} compramos/compró"
        cuanto_match = re.search(
            r'cu[aá]nt[ao]s?\s+(.+?)\s+(?:compramos|comprado|compr[oó]|se\s+compr)',
            msg_lower,
        )
        if cuanto_match:
            product = cuanto_match.group(1).strip()
            if len(product) >= 3:
                return product

        # "precio(s) de (las últimas N compras de) {product}"
        precio_match = re.search(
            r'precios?\s+de(?:\s+las?\s+[úu]ltim[ao]s?\s+\d+\s+compras?\s+de)?\s+'
            r'(.+?)(?:\s+(?:en|del|desde|este|el)\b|\s*[?]|$)',
            msg_lower,
        )
        if precio_match:
            product = precio_match.group(1).strip()
            if len(product) >= 3:
                return product

        # Fallback: if message has no general keywords and looks like a product
        # description (e.g. user just typed "caja de carton para cereales")
        if not any(kw in msg_lower for kw in self._GENERAL_KEYWORDS):
            # Remove dates, question marks, common filler
            cleaned = re.sub(
                r'(?:en|del?|desde|hasta|este|el|año|mes|enero|febrero|marzo|abril|'
                r'mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|'
                r'\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}|\d{4})\b',
                '', msg_lower,
            )
            cleaned = re.sub(r'[?¿!¡,.]', '', cleaned).strip()
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            # Must have at least 2 words and 5+ chars to be a product name
            if len(cleaned) >= 5 and ' ' in cleaned:
                return cleaned

        return None

    def _extract_product_from_history(
        self, history: list[tuple[str, str]],
    ) -> str | None:
        """Try to extract a product search term from recent history."""
        if not history:
            return None
        for role, content in reversed(history):
            if role == "user":
                product = self._extract_product_search(content)
                if product:
                    return product
        return None

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
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
        # Follow-up: if no product in current message, check history
        if not product_search and history:
            product_search = self._extract_product_from_history(history)

        if product_search:
            try:
                prod_data = build_product_purchase_history(
                    product_search=product_search,
                    org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    mes=mes, anio=anio,
                )
                if prod_data:
                    sections.append(
                        f"## Historial de Compras - Producto '{product_search}' ({len(prod_data)} registros)"
                    )
                    sections.append(self._format_table(prod_data))
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
