"""VentasAgent — ties together prompts, extraction, formatting, and fetch logic."""

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

from .prompts import SYSTEM_PROMPT, CAPABILITIES, SQL_CONTEXT
from .extraction import (
    QUERY_TYPES,
    extract_zona,
    extract_vendedor,
    extract_org_name,
    extract_org_patterns,
    is_ambiguous_org,
    detect_query_type,
    extract_product_search,
    extract_category_search,
    extract_context_from_history,
)
from .formatting import (
    AMBIGUOUS_ORG_CLARIFICATION,
    format_vendedores_table,
    is_empty_result,
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
        return SYSTEM_PROMPT

    def get_capabilities(self) -> str:
        return CAPABILITIES

    def get_sql_context(self) -> str:
        return SQL_CONTEXT

    # ---- Back-compat classmethod wrappers (used by some tests/modules) ----

    _QUERY_TYPES = QUERY_TYPES

    @classmethod
    def _extract_zona(cls, msg: str) -> str | None:
        return extract_zona(msg)

    @classmethod
    def _extract_vendedor(cls, msg: str) -> str | None:
        return extract_vendedor(msg)

    @classmethod
    def _extract_org_name(cls, msg: str) -> str | None:
        return extract_org_name(msg)

    @classmethod
    def _extract_org_patterns(cls, msg: str) -> list[str] | None:
        return extract_org_patterns(msg)

    @classmethod
    def _is_ambiguous_org(cls, msg: str) -> bool:
        return is_ambiguous_org(msg)

    @classmethod
    def _detect_query_type(cls, msg: str) -> str | None:
        return detect_query_type(msg)

    @classmethod
    def _extract_product_search(cls, msg: str) -> str | None:
        return extract_product_search(msg)

    @classmethod
    def _extract_category_search(cls, msg: str) -> str | None:
        return extract_category_search(msg)

    def _extract_context_from_history(
        self, history: list[tuple[str, str]],
    ) -> dict:
        return extract_context_from_history(history)

    def _is_empty_result(self, data) -> bool:
        return is_empty_result(data)

    def fetch_data(
        self,
        message: str,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str | None:
        logger = logging.getLogger("santonibot.agents.ventas")
        msg = message.lower()
        sections = []

        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)

        if date_from and date_to:
            mes = None
            anio = None

        currency_ids = detect_currency(message)

        vendedor = extract_vendedor(message)
        zona = extract_zona(message)
        org_name = extract_org_name(message)
        org_patterns = extract_org_patterns(message)

        hist_ctx: dict = {}
        if history:
            hist_ctx = extract_context_from_history(history)
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
        # calificar y el historial tampoco tiene una org específica, pedimos
        # clarificación en vez de adivinar. Darwin no puede validar contra
        # su Excel si el bot mezcla orgs silenciosamente.
        if is_ambiguous_org(message) and not org_patterns:
            return AMBIGUOUS_ORG_CLARIFICATION

        # CRÍTICO: si no hay moneda especificada, default a VES.
        # Si no, las queries suman Bs + USD como si fueran la misma moneda
        # y el total es incorrecto (ej: "Bs 739M" = Bs 738M + USD 1.4M).
        if not currency_ids:
            currency_ids = [205]  # VES

        if not date_from and not date_to and not mes:
            if hist_ctx.get("date_from"):
                date_from = hist_ctx["date_from"]
                date_to = hist_ctx["date_to"]
            elif hist_ctx.get("mes"):
                mes = hist_ctx["mes"]
                anio = hist_ctx.get("anio", anio)

        label = build_period_label(date_from, date_to, mes, anio)

        query_type = detect_query_type(message)
        if not query_type and hist_ctx:
            query_type = hist_ctx.get("query_type")

        has_product_mention = extract_product_search(message) is not None

        try:
            if query_type == "vendedor" or any(w in msg for w in QUERY_TYPES["vendedor"]):
                org_label = f" - {org_name}" if org_name else ""
                data = build_sales_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                vendedor_data = data.get("por_vendedor", [])
                limit_match = re.search(r'top\s*(\d+)', msg)
                vend_limit = int(limit_match.group(1)) if limit_match else 10
                sections.append(
                    format_vendedores_table(
                        vendedor_data,
                        title=f"Top {vend_limit} Vendedores por Venta Neta ({label}{org_label})",
                        limit=vend_limit,
                    )
                )

            if query_type == "top" or any(w in msg for w in QUERY_TYPES["top"]):
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
                if is_empty_result(data) and (mes or (date_from and date_to)):
                    logger.info("Fallback: retrying with full year %s (mes=None)", anio)
                    data_year = build_top_clients(
                        limit=limit, zona=zona, vendedor=vendedor, mes=None, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=None, date_to=None,
                        currency_ids=currency_ids, org_name=org_patterns,
                    )
                    logger.info("Fallback result: %d rows", len(data_year) if isinstance(data_year, list) else -1)
                    if not is_empty_result(data_year):
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

            if query_type == "cobranza" or any(w in msg for w in QUERY_TYPES["cobranza"]):
                data = build_collection_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                sections.append(self._format_summary(data, f"Resumen de Cobranza - {label}"))

            if query_type == "vencidas" or any(w in msg for w in QUERY_TYPES["vencidas"]):
                data = build_overdue_receivables(org_ids=org_ids, salesrep_id=salesrep_id)
                sections.append(self._format_summary(data, "Cuentas por Cobrar Vencidas"))

            if query_type == "producto" or has_product_mention or any(w in msg for w in QUERY_TYPES["producto"]):
                product_search = extract_product_search(message)
                category_search = extract_category_search(message)
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

            if query_type == "ordenes" or any(w in msg for w in QUERY_TYPES["ordenes"]):
                only_pending = any(w in msg for w in ["pendiente", "borrador", "proceso", "pipeline"])
                data = build_sales_orders(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                    only_pending=only_pending,
                )
                pending_label = " Pendientes" if only_pending else ""
                sections.append(self._format_summary(data, f"Órdenes de Venta{pending_label} - {label}"))

            if query_type == "impuestos" or any(w in msg for w in QUERY_TYPES["impuestos"]):
                data = build_sales_tax_summary(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                sections.append(self._format_summary(data, f"Desglose de Impuestos en Ventas - {label}"))

            if query_type == "sucursal" or any(w in msg for w in QUERY_TYPES["sucursal"]):
                data = build_sales_by_branch(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                sections.append(f"## Ventas por Sucursal - {label}")
                sections.append(self._format_table(data))

            if query_type == "tasa" or any(w in msg for w in QUERY_TYPES["tasa"]):
                data = build_exchange_rates(limit=20)
                sections.append("## Tasas de Cambio Recientes")
                sections.append(self._format_table(data))

            if not has_product_mention and (query_type == "ventas" or any(w in msg for w in QUERY_TYPES["ventas"]) or not sections):
                data = build_sales_summary(
                    zona=zona, vendedor=vendedor, mes=mes, anio=anio,
                    org_ids=org_ids, salesrep_id=salesrep_id,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids, org_name=org_patterns,
                )
                if is_empty_result(data) and (mes or (date_from and date_to)):
                    data_year = build_sales_summary(
                        zona=zona, vendedor=vendedor, mes=None, anio=anio,
                        org_ids=org_ids, salesrep_id=salesrep_id,
                        date_from=None, date_to=None,
                        currency_ids=currency_ids, org_name=org_patterns,
                    )
                    if not is_empty_result(data_year):
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
