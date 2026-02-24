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

from app.services.query_service import build_supply_purchases, build_product_purchase_history, build_inventory_stock


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
- Inventario/stock actual por producto, almacén, organización y categoría
- Búsqueda de productos en inventario por nombre o código

CONTEXTO iDEMPIERE:
- Facturas de compra: c_invoice (issotrx='N', docstatus='CO') - las facturas de compra tienen issotrx='N'
- Líneas de factura: c_invoiceline (m_product_id, qtyinvoiced, linenetamt)
- Proveedores: c_bpartner (isvendor='Y') - 26,070 socios de negocio
- Productos: m_product (40,766 productos) con m_product_category
- Monedas en iDempiere (Santoni usa múltiples códigos de moneda):
  * VES (ID 205) - Bolívares Soberanos (todas las organizaciones)
  * DOL (ID 1000000) - Dólares en INPROA SANTONI
  * DoL (ID 1000011) - Dólares en InproMaiz
  * Dol (ID 1000006) - Dólares en INVERSIONES AGA
  * USA (ID 1000003) - Dólares en AGROINPROA
  * dol (ID 1000008) - Dólares en AGROPECUARIA R.R.
  * DLA (ID 1000017) - Dólares en Santoni Service
  * Dla (ID 1000013) - Dólares en AGA AGRICOLA
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- Campos fiscales: lve_controlnumber, withholdingamt (retenciones)

REGLAS:
- Responde ÚNICAMENTE en español. NUNCA uses palabras en otros idiomas (inglés, ruso, etc.)
- Presenta precios con moneda y unidad de medida
- Usa formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89)
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente
- IMPORTANTE SOBRE MONEDAS: Los datos ya vienen filtrados por moneda.
  * Por defecto se muestran datos en Bolívares (VES).
  * Si el campo "moneda" dice "USD", los datos son en dólares.
  * Si dice "Todas las monedas (mixto)", aclara que los montos mezclan VES y USD.
  * NUNCA intentes convertir entre monedas. Cada moneda se consulta por separado.

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
- Si el usuario especificó un rango de fechas, los datos ya vienen filtrados para ese rango exacto

SOBRE INVENTARIO/STOCK:
- Los datos de inventario provienen de m_storageonhand (stock actual en almacenes)
- La cantidad es la existencia actual (qtyonhand), NO es un histórico
- Los productos pueden estar en múltiples almacenes y organizaciones
- Categorías principales: MANT. Y REPUESTOS, MANTENIMIENTO INSTALACIONES, REPUESTOS PLANTA, más productos alimenticios
- Si el usuario busca un producto específico, los datos ya vienen filtrados por nombre/código
- La columna 'unidad' muestra la unidad de medida del producto (kg, unidad, litro, etc.)"""

    def get_sql_context(self) -> str:
        return """
Datos de compras de insumos en iDempiere:
- c_invoice: Facturas de compra (issotrx='N', dateinvoiced, grandtotal, totallines, docstatus)
- c_invoiceline: Líneas (m_product_id, qtyinvoiced, linenetamt, priceactual)
- c_bpartner: Proveedores (isvendor='Y', name, value)
- m_product: Productos/insumos (name, m_product_category_id)
- m_product_category: Categorías de productos
- m_storageonhand: Stock actual en almacenes (m_product_id, qtyonhand, m_locator_id)
- m_locator: Ubicaciones de almacén (m_warehouse_id)
- m_warehouse: Almacenes (name, ad_org_id)
"""

    # Currency IDs in Santoni's iDempiere
    _VES_IDS = [205]
    _USD_IDS = [1000000, 1000003, 1000006, 1000008, 1000011, 1000013, 1000017]

    # Keywords that indicate the user wants USD
    _USD_KEYWORDS = [
        "dólares", "dolares", "dólar", "dolar", "usd",
        "en dólares", "en dolares", "en dólar", "en dolar",
    ]

    # Keywords that indicate the user wants VES
    _VES_KEYWORDS = [
        "bolívares", "bolivares", "bolívar", "bolivar", "ves",
        "en bolívares", "en bolivares",
    ]

    # Words that indicate a general query (not a specific product search)
    _GENERAL_KEYWORDS = [
        "resumen", "total", "proveedor", "proveedores", "mensual",
        "principales", "inventario", "stock", "existencia", "almacén",
        "almacen", "todos los insumos",
        "cuánto se", "cuanto se", "cuánto factur", "cuanto factur",
    ]

    # Keywords that indicate an inventory/stock query
    _INVENTORY_KEYWORDS = [
        "inventario", "stock", "existencia", "existencias",
        "almacén", "almacen", "almacenes",
        "disponible", "disponibilidad", "disponibles",
        "cuánto hay", "cuanto hay", "cuánto queda", "cuanto queda",
        "cuánto tenemos", "cuanto tenemos",
        "en almacén", "en almacen", "en bodega",
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

        # NOTE: No aggressive fallback. If no specific pattern matches,
        # return None and let the general summary + LLM handle the query.
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

    def _detect_currency(self, message: str, history: list[tuple[str, str]] | None = None) -> list[int] | None:
        """Detect which currency the user wants based on message and history.

        Returns currency_ids list, or None for default (VES).
        Checks current message first, then history for follow-ups like "Y en dólares?".
        """
        msg_lower = message.lower()

        # Check current message for USD keywords
        if any(kw in msg_lower for kw in self._USD_KEYWORDS):
            return self._USD_IDS

        # Check current message for VES keywords
        if any(kw in msg_lower for kw in self._VES_KEYWORDS):
            return self._VES_IDS

        # Check history for currency context (follow-ups)
        if history:
            for role, content in reversed(history):
                if role == "user":
                    content_lower = content.lower()
                    if any(kw in content_lower for kw in self._USD_KEYWORDS):
                        return self._USD_IDS
                    if any(kw in content_lower for kw in self._VES_KEYWORDS):
                        return self._VES_IDS
                    # Stop at first user message that doesn't mention currency
                    break

        # Default: VES (bolívares)
        return self._VES_IDS

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None

        label = build_period_label(date_from, date_to, mes, anio)

        # Detect currency preference
        currency_ids = self._detect_currency(message, history)

        # Check if user is searching for a specific product
        product_search = self._extract_product_search(message)
        # Follow-up: if no product in current message, check history
        if not product_search and history:
            product_search = self._extract_product_from_history(history)

        # Check if this is an inventory/stock query
        is_inventory = any(w in msg for w in self._INVENTORY_KEYWORDS)

        product_found = False

        if is_inventory:
            # For inventory queries, use product_search as filter if available
            inv_data = build_inventory_stock(
                org_ids=org_ids,
                product_search=product_search,
            )
            filter_label = f" - '{product_search}'" if product_search else ""
            sections.append(self._format_summary(
                inv_data, f"Inventario / Stock Actual{filter_label}",
            ))
            product_found = True
        elif product_search:
            try:
                prod_data = build_product_purchase_history(
                    product_search=product_search,
                    org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    mes=mes, anio=anio,
                )
                if prod_data:
                    product_found = True
                    sections.append(
                        f"## Historial de Compras - Producto '{product_search}' ({len(prod_data)} registros)"
                    )
                    sections.append(self._format_table(prod_data))
                else:
                    sections.append(
                        f"## Búsqueda de Producto '{product_search}'\n"
                        f"No se encontraron compras para '{product_search}' en el período {label}."
                    )
            except Exception:
                pass

        # General summary: always include unless specific product/inventory data was found
        if not product_found:
            summary = build_supply_purchases(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
                currency_ids=currency_ids,
            )
            sections.append(self._format_summary(summary, f"Resumen de Compras de Insumos - {label}"))

        return "\n\n".join(sections) if sections else None
