"""
Agente de Compras de Insumos - Alimentos Santoni
Especializado en: órdenes de compra, proveedores, inventarios de materiales,
precios históricos, tiempos de entrega.

Fuente de datos: c_invoice (issotrx='N'), c_invoiceline,
m_product, c_bpartner en iDempiere (PostgreSQL 13).
"""

import logging

from app.agents.base_agent import BaseAgent

logger = logging.getLogger("santonibot.agents.compras_insumos")
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
import re

from app.services.query_service import (
    build_supply_purchases,
    build_product_purchase_history,
    build_inventory_stock,
    build_pending_purchase_orders,
    build_supplier_price_comparison,
    build_purchase_payment_status,
)


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
- Órdenes de compra pendientes (c_order) por período, proveedor y estado
- Comparación de precios entre proveedores para un mismo producto
- Estado de pago de facturas de compra (pagadas vs pendientes)

CONTEXTO iDEMPIERE:
- Facturas de compra: c_invoice (issotrx='N', docstatus IN ('CO','CL')) - CO=completada, CL=cerrada (pagada). Ambos estados son válidos.
- Órdenes de compra: c_order (issotrx='N') - órdenes pendientes, en proceso y completadas
- Líneas de factura: c_invoiceline (m_product_id, qtyinvoiced, linenetamt)
- Proveedores: c_bpartner (isvendor='Y')
- Productos: m_product con m_product_category
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
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si los datos están vacíos, di "No se encontraron datos para ese filtro". NUNCA culpes a problemas de acceso — la conexión SIEMPRE está activa.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me", NO adivines. Pide al usuario que reformule especificando: la organización, producto, proveedor, período u otros datos necesarios.
- En follow-ups como "dame el inventario de ese producto", los datos YA fueron consultados automáticamente. Presenta los datos que recibes, no inventes excusas.
- IMPORTANTE SOBRE MONEDAS: Los datos se separan automáticamente por moneda.
  * Por defecto se muestran TODAS las monedas (Bs. y USD por separado).
  * Si el usuario pide "en dólares" o "en bolívares", los datos vienen filtrados a esa moneda.
  * La columna "moneda" indica si cada fila es en "Bs." o "USD".
  * NUNCA sumes montos de monedas diferentes. Presenta cada moneda por separado.
  * NUNCA intentes convertir entre monedas.

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

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Resumen de compras: total facturas y montos por período, separado por moneda\n"
            "✅ Top 20 proveedores por volumen de compra\n"
            "✅ Top 20 productos más comprados por valor\n"
            "✅ Tendencia mensual de compras\n"
            "✅ Historial de compras de un producto específico (por nombre o código)\n"
            "✅ Stock/inventario actual por producto, almacén, organización y categoría\n"
            "✅ Órdenes de compra pendientes (c_order) por período, estado y proveedor\n"
            "✅ Comparación de precios entre proveedores para un mismo producto\n"
            "✅ Estado de pago de facturas de compra (pagadas vs pendientes)\n"
            "✅ Gastos operativos registrados como facturas de compra (AP)\n"
            "\n❌ NO puedo consultar: nómina ni servicios públicos. "
            "Redirige al usuario al agente de RRHH o Finanzas."
        )

    def get_sql_context(self) -> str:
        return """
Datos de compras de insumos en iDempiere:
- c_invoice: Facturas de compra (issotrx='N', dateinvoiced, grandtotal, ispaid, docstatus)
- c_invoiceline: Líneas (m_product_id, qtyinvoiced, linenetamt, priceactual)
- c_order: Órdenes de compra (issotrx='N', dateordered, grandtotal, docstatus DR/IP/CO)
- c_orderline: Líneas de orden (m_product_id, qtyordered, priceactual)
- c_bpartner: Proveedores (isvendor='Y', name, value)
- m_product: Productos/insumos (name, m_product_category_id)
- m_product_category: Categorías de productos
- m_storageonhand: Stock actual en almacenes (m_product_id, qtyonhand, m_locator_id)
- m_locator: Ubicaciones de almacén (m_warehouse_id)
- m_warehouse: Almacenes (name, ad_org_id)
"""

    # Currency IDs in Santoni's iDempiere
    _VES_IDS = [205]
    _USD_IDS = [100, 1000000, 1000003, 1000006, 1000008, 1000009, 1000011, 1000013, 1000017]

    from app.agents.keywords import MONEDA_USD as _USD_KW_SET
    from app.agents.keywords import MONEDA_VES as _VES_KW_SET

    # Import centralized keyword sets for query type detection
    from app.agents.keywords import (
        COMPRAS_GENERAL as _GENERAL_KW_SET,
        COMPRAS_INVENTARIO as _INVENTORY_KW_SET,
        COMPRAS_ORDENES as _ORDER_KW_SET,
        COMPRAS_PRECIOS as _PRICE_COMPARE_KW_SET,
    )

    # Organization name mapping (keyword → iDempiere org name)
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
    def _extract_org_name(cls, msg: str) -> str | None:
        msg_lower = msg.lower()
        for kw, val in cls._ORG_MAP:
            if kw in msg_lower:
                return val
        return None

    from app.agents.keywords import COMPRAS_PAGOS as _PAYMENT_KW_SET

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

        # Pronoun references: "ese producto", "este producto", "del producto", etc.
        # These refer to a product from context → return None to trigger history lookup.
        # Must come AFTER product code and quoted name checks (those are explicit).
        if re.search(r'\b(?:ese|este|aquel|el|del|dicho|mismo)\s+producto\b', msg_lower):
            return None

        # "producto X" or "producto: X"
        prod_match = re.search(
            r'producto[:\s]+(.+?)(?:\s+(?:en|del|desde|este)\b|\s+\d{4}\b|\s*[?]|$)',
            msg_lower,
        )
        if prod_match and len(prod_match.group(1).strip()) >= 3:
            return prod_match.group(1).strip()

        # "compras de {product}" / "historial de compras de {product}"
        compras_match = re.search(
            r'(?:compras?\s+de|historial\s+de(?:\s+compras?\s+de)?)\s+'
            r'(.+?)(?:\s+(?:en|del|desde|este|el|último|ultima)\b|\s+\d{4}\b|\s*[?]|$)',
            msg_lower,
        )
        if compras_match:
            product = compras_match.group(1).strip()
            product = re.sub(
                r'(?:\s+(?:del?|en|este|el|[úu]ltimo|ultima|trimestre|semestre|mes|año)|\s+\d{4})\s*$',
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

        # "comparación de precios de X entre proveedores" — must come BEFORE generic "precio de X"
        compare_match = re.search(
            r'comparaci[oó]n\s+de\s+precios?\s+de\s+'
            r'(.+?)(?:\s+entre\s+proveedores?|\s+(?:en|del|desde|este)\b|\s+\d{4}\b|\s*[?]|$)',
            msg_lower,
        )
        if compare_match:
            product = compare_match.group(1).strip()
            if len(product) >= 3:
                return product

        # "precio(s) de (las últimas N compras de) {product}"
        precio_match = re.search(
            r'precios?\s+de(?:\s+las?\s+[úu]ltim[ao]s?\s+\d+\s+compras?\s+de)?\s+'
            r'(.+?)(?:\s+(?:en|del|desde|este|el)\b|\s+\d{4}\b|\s*[?]|$)',
            msg_lower,
        )
        if precio_match:
            product = precio_match.group(1).strip()
            product = re.sub(r'\s+\d{4}\s*$', '', product)
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
            r'(.+?)(?:\s+(?:en|del|desde|este)\b|\s+\d{4}\b|\s*[?]|$)',
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

    def _extract_dates_from_history(
        self, history: list[tuple[str, str]],
    ) -> tuple[str | None, str | None, int | None, int | None]:
        """Extract temporal context from recent history for follow-up messages.

        Scans backwards through user messages looking for one that contains
        explicit temporal info (date range or month name).

        Returns (date_from, date_to, mes, anio) or all-None if nothing found.
        """
        for role, content in reversed(history):
            if role != "user":
                continue
            df, dt = extract_date_range(content)
            if df:
                # History message had an explicit date range
                mes_h, anio_h = extract_month_year(content)
                return df, dt, mes_h, anio_h
            mes_h, anio_h = extract_month_year(content)
            if mes_h is not None:
                # History message had an explicit month
                return None, None, mes_h, anio_h
        return None, None, None, None

    def _detect_currency(self, message: str, history: list[tuple[str, str]] | None = None) -> list[int] | None:
        """Detect which currency the user wants based on message and history.

        Returns currency_ids list, or None for default (VES).
        Checks current message first, then history for follow-ups like "Y en dólares?".
        """
        msg_lower = message.lower()

        # Check current message for USD keywords
        if any(kw in msg_lower for kw in self._USD_KW_SET):
            return self._USD_IDS

        # Check current message for VES keywords
        if any(kw in msg_lower for kw in self._VES_KW_SET):
            return self._VES_IDS

        # Check history for currency context (follow-ups)
        if history:
            for role, content in reversed(history):
                if role == "user":
                    content_lower = content.lower()
                    if any(kw in content_lower for kw in self._USD_KW_SET):
                        return self._USD_IDS
                    if any(kw in content_lower for kw in self._VES_KW_SET):
                        return self._VES_IDS
                    # Stop at first user message that doesn't mention currency
                    break

        # Default: show all currencies (no filter)
        return None

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates from current message
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        # Track if user explicitly mentioned a year/month or if it's just the default
        _has_explicit_year = bool(re.search(r'20\d{2}', message))
        _has_explicit_month = mes is not None
        has_explicit_period = _has_explicit_year or _has_explicit_month or bool(date_from)
        if date_from and date_to:
            mes = None
            anio = None

        # Follow-up: if no specific temporal context in current message,
        # inherit from history (e.g. "Y en dólares?" after "compras este mes")
        if mes is None and date_from is None and history:
            h_df, h_dt, h_mes, h_anio = self._extract_dates_from_history(history)
            if h_df or h_mes is not None:
                date_from, date_to = h_df, h_dt
                mes = h_mes
                if h_anio is not None:
                    anio = h_anio
                if date_from and date_to:
                    mes = None
                    anio = None

        label = build_period_label(date_from, date_to, mes, anio)

        # Extract organization name from message (e.g. "en la empresa INPROA SANTONI")
        org_name = self._extract_org_name(message)
        if not org_name and history:
            for role, content in reversed(history):
                if role != "user":
                    continue
                o = self._extract_org_name(content)
                if o:
                    org_name = o
                    break

        # Detect currency preference
        currency_ids = self._detect_currency(message, history)

        # Check if user is searching for a specific product
        product_search = self._extract_product_search(message)
        # Follow-up: if no product in current message, check history
        if not product_search and history:
            product_search = self._extract_product_from_history(history)

        # Detect query type using centralized keyword sets
        is_inventory = any(w in msg for w in self._INVENTORY_KW_SET)
        is_orders = any(w in msg for w in self._ORDER_KW_SET)
        is_price_compare = any(w in msg for w in self._PRICE_COMPARE_KW_SET)
        is_payment = any(w in msg for w in self._PAYMENT_KW_SET)

        product_found = False

        try:
            if is_inventory:
                inv_data = build_inventory_stock(
                    org_ids=org_ids,
                    product_search=product_search,
                )
                if not self._dict_has_data(inv_data):
                    return None
                filter_label = f" - '{product_search}'" if product_search else ""
                sections.append(self._format_summary(
                    inv_data, f"Inventario / Stock Actual{filter_label}",
                ))
                product_found = True

            elif is_payment:
                payment_data = build_purchase_payment_status(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids,
                )
                if not self._dict_has_data(payment_data):
                    return None

                # Build explicit totals for payment status
                resumen = payment_data.get("resumen_pago", [])
                payment_lines = [f"## Estado de Pago de Facturas de Compra - {label}"]
                total_facs = sum(r.get("facturas", 0) for r in resumen)
                payment_lines.append(f"\nTOTAL EXACTO DE FACTURAS: {total_facs}")
                for r in resumen:
                    payment_lines.append(
                        f"- {r['estado_pago']} ({r['moneda']}): "
                        f"{r['facturas']} facturas, monto: {r['total']:,.2f}"
                    )
                sections.append("\n".join(payment_lines))

                # Add overdue detail
                vencidas = payment_data.get("facturas_vencidas", [])

            elif is_orders:
                orders_data = build_pending_purchase_orders(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids,
                    product_search=product_search,
                )
                if not self._dict_has_data(orders_data):
                    return None

                # Build explicit totals for pending orders
                totals_info = orders_data.get("totales", {})
                por_moneda = totals_info.get("por_moneda", [])
                total_ordenes = totals_info.get("total_ordenes", 0)
                order_lines = [f"## Órdenes de Compra Pendientes (DR/IP) - {label}"]
                order_lines.append(f"\nTOTAL EXACTO DE ÓRDENES PENDIENTES: {total_ordenes}")
                for pm in por_moneda:
                    order_lines.append(
                        f"- {pm['moneda']}: {pm['total_ordenes']} órdenes, "
                        f"monto total: {pm['total_monto']:,.2f}"
                    )
                sections.append("\n".join(order_lines))

                # Add status, supplier, and detail tables
                for detail_key in ("por_estado", "por_proveedor", "detalle_ordenes"):
                    detail_data = orders_data.get(detail_key, [])
                    if detail_data:
                        sections.append(
                            f"\n### {detail_key.replace('_', ' ').title()} "
                            f"[{len(detail_data)} registros exactos]"
                        )
                        sections.append(self._format_table(detail_data))
                if vencidas:
                    sections.append(
                        f"\n### Facturas Vencidas Sin Pagar [{len(vencidas)} registros exactos]"
                    )
                    sections.append(self._format_table(vencidas))
                product_found = True

            elif is_price_compare and product_search:
                # For price comparison, only filter by date if user explicitly
                # specified a period.  Otherwise show ALL historical data so
                # the user can see every supplier that has ever sold this product.
                cmp_anio = anio if has_explicit_period else None
                cmp_df = date_from if has_explicit_period else None
                cmp_dt = date_to if has_explicit_period else None
                compare_data = build_supplier_price_comparison(
                    product_search=product_search,
                    org_ids=org_ids, anio=cmp_anio,
                    date_from=cmp_df, date_to=cmp_dt,
                    org_name=org_name,
                )
                if compare_data:
                    product_found = True
                    period_note = f" - {label}" if has_explicit_period else " - Todo el historial"
                    sections.append(
                        f"## Comparación de Precios - '{product_search}'{period_note} ({len(compare_data)} proveedores)"
                    )
                    sections.append(self._format_table(compare_data))
                else:
                    sections.append(
                        f"## Comparación de Precios - '{product_search}'\n"
                        f"No se encontraron datos de precios para '{product_search}'."
                    )

            elif product_search:
                try:
                    # Check if user is asking for suppliers of a product
                    is_supplier_query = any(w in msg for w in ["proveedores", "proveedor", "quien vende", "quién vende"])

                    if is_supplier_query:
                        # Supplier queries ("quién vende X") should show ALL
                        # historical suppliers unless user specified a period.
                        sup_anio = anio if has_explicit_period else None
                        sup_df = date_from if has_explicit_period else None
                        sup_dt = date_to if has_explicit_period else None
                        compare_data = build_supplier_price_comparison(
                            product_search=product_search,
                            org_ids=org_ids, anio=sup_anio,
                            date_from=sup_df, date_to=sup_dt,
                            org_name=org_name,
                        )
                        if compare_data:
                            product_found = True
                            period_note = f" - {label}" if has_explicit_period else " - Todo el historial"
                            sections.append(
                                f"## Proveedores de '{product_search}'{period_note} ({len(compare_data)} proveedores)"
                            )
                            sections.append(self._format_table(compare_data))

                    if not product_found:
                        prod_data = build_product_purchase_history(
                            product_search=product_search,
                            org_ids=org_ids,
                            date_from=date_from, date_to=date_to,
                            mes=mes, anio=anio,
                            org_name=org_name,
                        )
                        if prod_data:
                            product_found = True
                            sections.append(
                                f"## Historial de Compras - Producto '{product_search}' ({len(prod_data)} registros)"
                            )
                            sections.append(self._format_table(prod_data))
                        else:
                            # Try without date filter as fallback
                            prod_data_all = build_product_purchase_history(
                                product_search=product_search,
                                org_ids=org_ids,
                                org_name=org_name,
                            )
                            if prod_data_all:
                                product_found = True
                                sections.append(
                                    f"## Historial de Compras - Producto '{product_search}' "
                                    f"(no hay datos en {label}, mostrando todo el historial: "
                                    f"{len(prod_data_all)} registros)"
                                )
                                sections.append(self._format_table(prod_data_all))
                            else:
                                sections.append(
                                    f"## Búsqueda de Producto '{product_search}'\n"
                                    f"No se encontraron compras para '{product_search}' "
                                    f"en ningún período registrado.\n"
                                    f"Verifica el nombre o código del producto."
                                )
                except Exception as exc:
                    logger.warning("Error buscando historial de producto '%s': %s", product_search, exc)

            # General summary: always include unless specific data was found
            if not product_found:
                summary = build_supply_purchases(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids,
                )
                # Check if there's actually data — if total_facturas==0, return None
                # so base_agent activates anti-hallucination for empty results
                total_facturas = summary.get("totales", {}).get("total_facturas", 0)
                if total_facturas == 0:
                    return None

                # Build explicit totals header so LLM can't misread nested data
                totals_info = summary.get("totales", {})
                por_moneda = totals_info.get("por_moneda", [])
                totals_lines = [f"## Resumen de Compras de Insumos - {label}"]
                totals_lines.append(f"\nTOTAL EXACTO DE FACTURAS: {total_facturas}")
                for pm in por_moneda:
                    totals_lines.append(
                        f"- {pm['moneda']}: {pm['total_facturas']} facturas, "
                        f"monto total: {pm['total_monto']:,.2f}"
                    )
                sections.append("\n".join(totals_lines))

                # Add detail tables
                for detail_key in ("por_proveedor", "por_mes", "por_producto"):
                    detail_data = summary.get(detail_key, [])
                    if detail_data:
                        sections.append(
                            f"\n### {detail_key.replace('_', ' ').title()} "
                            f"[{len(detail_data)} registros exactos]"
                        )
                        sections.append(self._format_table(detail_data))

        except Exception as exc:
            logger.error("Error consultando datos de compras de insumos: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None
