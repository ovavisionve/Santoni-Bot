"""
Agente de Compras a Productores - Alimentos Santoni
Especializado en: compras de materia prima agrícola (arroz, maíz) a productores,
volúmenes, precios por kilo/tonelada, pagos pendientes, productores registrados.

Fuente de datos: c_order (issotrx='N'), c_orderline, c_bpartner (isagricultor='Y'),
m_product en iDempiere (PostgreSQL 13).
"""

import logging

from app.agents.base_agent import BaseAgent

logger = logging.getLogger("santonibot.agents.compras_productores")
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
    detect_currency,
)
from app.services.query_service import (
    build_producer_purchases,
    build_registered_producers,
    build_producer_pending_payments,
    build_producer_price_analysis,
)


class ComprasProductoresAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "compras_productores"

    @property
    def display_name(self) -> str:
        return "Compras a Productores"

    @property
    def department(self) -> str:
        return "compras_productores"

    @property
    def description(self) -> str:
        return (
            "Consultas de compras a productores agrícolas: arroz paddy, maíz, "
            "volúmenes, precios, pagos pendientes, productores registrados"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Compras a Productores de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es la gestión de compras de materia prima agrícola a productores.

CAPACIDADES:
- Resumen de compras por producto, período y productor
- Top productores por volumen y monto
- Pagos pendientes a productores
- Análisis de precios por kg/tonelada
- Productores registrados

CONTEXTO iDEMPIERE:
- Órdenes de compra: c_order (issotrx='N', docstatus IN ('CO','CL')). CO=completada, CL=cerrada.
- Líneas de orden: c_orderline (m_product_id, qtyordered, priceactual, linenetamt)
- Productores: c_bpartner (isagricultor='Y', codigoproductor, codigocompras)
- Productos: m_product (arroz paddy acondicionado, maíz blanco de consumo)
- Campos de guías agrícolas en c_order: driver, plateno, grossweight, tareweight, netweight, classification, tipofrijol, guidemac, guideproducer, guidesada
- Ubicación productores: c_bpartner_location → c_city → c_region
- Monedas: VES (Bolívares, ID 205), USD (Dólares, ID 100)
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service

REGLAS:
- Responde siempre en español
- Presenta volúmenes en kg y toneladas
- Presenta precios en Bs./kg con formato venezolano (punto=miles, coma=decimal)
- Distingue entre Arroz Paddy Húmedo y Maíz
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta, di "No se encontraron datos" y sugiere consultas alternativas.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me", NO adivines. Pide al usuario que reformule especificando: la organización, productor, cultivo, período u otros datos necesarios.

CONTEXTO:
- Responsable: Marlenis Figueredo
- Productos principales: Arroz Paddy Acondicionado, Maíz Blanco de Consumo
- El usuario puede referirse al arroz como "arroz paddy", "arroz húmedo", etc.
- El usuario puede referirse al maíz como "maíz blanco", "maíz", etc.
- Zonas productoras: Portuguesa, Barinas, Apure, Lara, Cojedes

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

    def get_capabilities(self) -> str:
        return (
            "CAPACIDADES REALES (lo que SÍ puedo consultar en la base de datos):\n"
            "✅ Resumen de compras a productores: totales por producto, período\n"
            "✅ Top 20 productores por volumen y monto\n"
            "✅ Pagos pendientes a productores (facturas no pagadas)\n"
            "✅ Análisis de precios por producto (min, promedio, max)\n"
            "✅ Productores registrados (nombre, código, ciudad)\n"
            "\nNota: Los campos de humedad/impureza y datos de guías agrícolas están en proceso "
            "de integración.\n"
            "❌ NO puedo consultar temas fuera de compras a productores. "
            "Redirige al usuario al agente correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos de compras a productores en iDempiere:
- c_order: Órdenes de compra (issotrx='N', dateordered, grandtotal, docstatus, driver, plateno, grossweight, netweight, classification)
- c_orderline: Líneas (m_product_id, qtyordered, priceactual, linenetamt)
- c_bpartner: Productores (isagricultor='Y', codigoproductor, name, value)
- c_bpartner_location: Ubicación (c_city_id, c_region_id)
- m_product: Productos agrícolas (arroz, maíz)
"""

    # ---- History-based follow-up helpers ----

    @staticmethod
    def _extract_producto(msg: str) -> str | None:
        msg_lower = msg.lower()
        if "arroz" in msg_lower:
            return "arroz paddy"
        if "maíz" in msg_lower or "maiz" in msg_lower:
            return "maiz"
        return None

    @staticmethod
    def _extract_producer_name(msg: str) -> str | None:
        """Extract a producer name from the message.

        Handles patterns like:
        - 'productor Jose Luis Perez'
        - 'deuda de Jose Luis Perez'
        - 'pago a Juan Garcia'
        """
        import re
        msg_lower = msg.lower()
        # Pattern: "productor <name>" or "a productor <name>"
        for pattern in [
            r'(?:productor|proveedor)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{3,})',
            r'(?:deuda|pago|pagos|pendiente)\s+(?:de|a|del|al)\s+(?:productor\s+)?([A-ZÁÉÍÓÚÑa-záéíóúñ][A-ZÁÉÍÓÚÑa-záéíóúñ\s]{3,})',
        ]:
            m = re.search(pattern, msg, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                # Remove trailing common words
                for stop in ["en ", "del ", "de ", "este ", "por ", "para "]:
                    idx = name.lower().find(stop)
                    if idx > 3:
                        name = name[:idx].strip()
                if len(name) >= 4:
                    return name
        return None

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

    _SECTION_KEYWORDS: dict[str, list[str]] = {
        "productores": ["productor", "registrad", "cuántos", "cuantos"],
        "pendientes": ["pago", "pendiente", "deuda", "deb"],
        "precios": ["precio", "costo", "valor"],
    }

    def _extract_context_from_history(
        self, history: list[tuple[str, str]],
    ) -> dict:
        """Extract producto, section keywords, and temporal context from recent user history."""
        ctx: dict = {}
        if not history:
            return ctx
        for role, content in reversed(history):
            if role != "user":
                continue
            if "producto" not in ctx:
                prod = self._extract_producto(content)
                if prod:
                    ctx["producto"] = prod
            msg = content.lower()
            if "sections" not in ctx:
                for section, kws in self._SECTION_KEYWORDS.items():
                    if any(w in msg for w in kws):
                        ctx["sections"] = section
                        break
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
            if len(ctx) >= 5:
                break
        return ctx

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None
            anio = None

        producto = self._extract_producto(message)
        producer_name = self._extract_producer_name(message)

        # Follow-up: carry over context from history
        hist_ctx: dict = {}
        if history and (not producto or not any(
            any(w in msg for w in kws) for kws in self._SECTION_KEYWORDS.values()
        )):
            hist_ctx = self._extract_context_from_history(history)

        if not producto:
            producto = hist_ctx.get("producto")

        # Inherit temporal context from history for follow-ups
        if not date_from and not date_to and not mes:
            if hist_ctx.get("date_from"):
                date_from = hist_ctx["date_from"]
                date_to = hist_ctx["date_to"]
            elif hist_ctx.get("mes"):
                mes = hist_ctx["mes"]
                anio = hist_ctx.get("anio", anio)

        label = build_period_label(date_from, date_to, mes, anio)

        # Extract organization name from message (e.g. "en INPROA SANTONI", "de inpromaiz")
        org_name = self._extract_org_name(message)
        if not org_name and history:
            for role, content in reversed(history):
                if role != "user":
                    continue
                o = self._extract_org_name(content)
                if o:
                    org_name = o
                    break

        # Detect currency preference (e.g. "en dólares", "monto en usd")
        currency_ids = detect_currency(message)
        if not currency_ids and history:
            for role, content in reversed(history):
                if role == "user":
                    currency_ids = detect_currency(content)
                    if currency_ids:
                        break
                    # Stop at first user message that doesn't mention currency
                    break

        try:
            summary = build_producer_purchases(
                producto=producto, mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to, org_name=org_name,
            )
            sections.append(self._format_summary(summary, f"Compras a Productores - {label}"))

            include_productores = any(w in msg for w in self._SECTION_KEYWORDS["productores"])
            include_pendientes = any(w in msg for w in self._SECTION_KEYWORDS["pendientes"])
            include_precios = any(w in msg for w in self._SECTION_KEYWORDS["precios"])

            # If follow-up has no section keywords, carry over from history
            if not include_productores and not include_pendientes and not include_precios:
                section_type = hist_ctx.get("sections")
                if section_type == "productores":
                    include_productores = True
                elif section_type == "pendientes":
                    include_pendientes = True
                elif section_type == "precios":
                    include_precios = True

            if include_productores:
                try:
                    producers = build_registered_producers(org_ids=org_ids)
                    if producers:
                        sections.append("## Productores (Proveedores) Registrados")
                        sections.append(self._format_table(producers))
                except Exception as exc:
                    logger.warning("Error consultando productores registrados: %s", exc)

            # If user asks about a specific producer's debt, always include pendientes
            if producer_name and not include_pendientes:
                include_pendientes = True

            if include_pendientes:
                try:
                    pending = build_producer_pending_payments(
                        producto=producto, org_ids=org_ids, producer_name=producer_name,
                        currency_ids=currency_ids,
                    )
                    if pending:
                        total_pendiente = sum(d.get("monto_total", 0) for d in pending)
                        sections.append(
                            f"## Facturas Pendientes de Pago ({len(pending)} facturas - Total: Bs. {total_pendiente:,.2f})"
                        )
                        sections.append(self._format_table(pending))
                except Exception as exc:
                    logger.warning("Error consultando pagos pendientes a productores: %s", exc)

            if include_precios:
                try:
                    prices = build_producer_price_analysis(
                        anio=anio, org_ids=org_ids,
                        date_from=date_from, date_to=date_to,
                    )
                    if prices:
                        sections.append(f"## Análisis de Precios ({label}) (Bs./kg)")
                        sections.append(self._format_table(prices))
                except Exception as exc:
                    logger.warning("Error consultando análisis de precios: %s", exc)

        except Exception as exc:
            logger.error("Error consultando datos de compras a productores: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None
