"""ComprasInsumosAgent — split from compras_insumos.py (Abr 2026).

Delegates product/keyword/currency extraction to `.extraction` and the prompt
strings to `.prompts`. Keeps classmethod wrappers on the agent class so any
caller doing `ComprasInsumosAgent._extract_product_search(msg)` still works.
"""

import logging

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    build_period_label,
    extract_date_range,
    extract_month_year,
)
from app.services.query_service import (
    build_inventory_stock,
    build_pending_purchase_orders,
    build_product_purchase_history,
    build_purchase_payment_status,
    build_supplier_price_comparison,
    build_supply_purchases,
)

from .extraction import (
    GENERAL_KEYWORDS,
    INVENTORY_KEYWORDS,
    ORDER_KEYWORDS,
    ORG_MAP,
    PAYMENT_KEYWORDS,
    PRICE_COMPARE_KEYWORDS,
    USD_IDS,
    USD_KEYWORDS,
    VES_IDS,
    VES_KEYWORDS,
    detect_currency,
    extract_dates_from_history,
    extract_org_name,
    extract_product_from_history,
    extract_product_search,
)
from .prompts import CAPABILITIES, SQL_CONTEXT, SYSTEM_PROMPT

logger = logging.getLogger("santonibot.agents.compras_insumos")


class ComprasInsumosAgent(BaseAgent):
    # Class attributes kept for backward-compat (tests / external callers
    # can still reference ComprasInsumosAgent._USD_IDS, etc.).
    _VES_IDS = VES_IDS
    _USD_IDS = USD_IDS
    _USD_KEYWORDS = USD_KEYWORDS
    _VES_KEYWORDS = VES_KEYWORDS
    _GENERAL_KEYWORDS = GENERAL_KEYWORDS
    _INVENTORY_KEYWORDS = INVENTORY_KEYWORDS
    _ORDER_KEYWORDS = ORDER_KEYWORDS
    _PRICE_COMPARE_KEYWORDS = PRICE_COMPARE_KEYWORDS
    _PAYMENT_KEYWORDS = PAYMENT_KEYWORDS
    _ORG_MAP = ORG_MAP

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
        return SYSTEM_PROMPT

    def get_capabilities(self) -> str:
        return CAPABILITIES

    def get_sql_context(self) -> str:
        return SQL_CONTEXT

    @classmethod
    def _extract_org_name(cls, msg: str) -> str | None:
        return extract_org_name(msg)

    @classmethod
    def _extract_product_search(cls, message: str) -> str | None:
        return extract_product_search(message)

    @classmethod
    def _extract_product_from_history(
        cls, history: list[tuple[str, str]],
    ) -> str | None:
        return extract_product_from_history(history)

    @classmethod
    def _extract_dates_from_history(
        cls, history: list[tuple[str, str]],
    ) -> tuple[str | None, str | None, int | None, int | None]:
        return extract_dates_from_history(history)

    @classmethod
    def _detect_currency(
        cls,
        message: str,
        history: list[tuple[str, str]] | None = None,
    ) -> list[int] | None:
        return detect_currency(message, history)

    def fetch_data(
        self,
        message: str,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str | None:
        msg = message.lower()
        sections: list[str] = []

        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None
            anio = None

        if mes is None and date_from is None and history:
            h_df, h_dt, h_mes, h_anio = extract_dates_from_history(history)
            if h_df or h_mes is not None:
                date_from, date_to = h_df, h_dt
                mes = h_mes
                if h_anio is not None:
                    anio = h_anio
                if date_from and date_to:
                    mes = None
                    anio = None

        label = build_period_label(date_from, date_to, mes, anio)

        org_name = extract_org_name(message)
        if not org_name and history:
            for role, content in reversed(history):
                if role != "user":
                    continue
                o = extract_org_name(content)
                if o:
                    org_name = o
                    break

        currency_ids = detect_currency(message, history)

        product_search = extract_product_search(message)
        if not product_search and history:
            product_search = extract_product_from_history(history)

        is_inventory = any(w in msg for w in INVENTORY_KEYWORDS)
        is_orders = any(w in msg for w in ORDER_KEYWORDS)
        is_price_compare = any(w in msg for w in PRICE_COMPARE_KEYWORDS)
        is_payment = any(w in msg for w in PAYMENT_KEYWORDS)

        product_found = False

        try:
            if is_inventory:
                inv_data = build_inventory_stock(
                    org_ids=org_ids,
                    product_search=product_search,
                    org_name=org_name,
                )
                filter_label = f" - '{product_search}'" if product_search else ""
                sections.append(self._format_summary(
                    inv_data, f"Inventario / Stock Actual{filter_label}",
                ))
                product_found = True

            if is_orders:
                orders_data = build_pending_purchase_orders(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids,
                    product_search=product_search,
                    org_name=org_name,
                )
                sections.append(self._format_summary(
                    orders_data, f"Órdenes de Compra - {label}",
                ))
                product_found = True

            if is_payment:
                payment_data = build_purchase_payment_status(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    org_name=org_name,
                )
                sections.append(self._format_summary(
                    payment_data,
                    f"Estado de Pago de Facturas de Compra - {label}",
                ))
                product_found = True

            if is_price_compare and product_search:
                compare_data = build_supplier_price_comparison(
                    product_search=product_search,
                    org_ids=org_ids, anio=anio,
                    date_from=date_from, date_to=date_to,
                    org_name=org_name,
                )
                if compare_data:
                    product_found = True
                    sections.append(
                        f"## Comparación de Precios - '{product_search}' "
                        f"({len(compare_data)} proveedores)"
                    )
                    sections.append(self._format_table(compare_data))
                else:
                    sections.append(
                        f"## Comparación de Precios - '{product_search}'\n"
                        f"No se encontraron datos de precios para "
                        f"'{product_search}' en el período {label}."
                    )

            if not product_found and product_search:
                try:
                    is_supplier_query = any(
                        w in msg for w in [
                            "proveedores", "proveedor",
                            "quien vende", "quién vende",
                        ]
                    )

                    if is_supplier_query:
                        compare_data = build_supplier_price_comparison(
                            product_search=product_search,
                            org_ids=org_ids, anio=anio,
                            date_from=date_from, date_to=date_to,
                            org_name=org_name,
                        )
                        if compare_data:
                            product_found = True
                            sections.append(
                                f"## Proveedores de '{product_search}' "
                                f"({len(compare_data)} proveedores)"
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
                                f"## Historial de Compras - Producto "
                                f"'{product_search}' ({len(prod_data)} registros)"
                            )
                            sections.append(self._format_table(prod_data))
                        else:
                            prod_data_all = build_product_purchase_history(
                                product_search=product_search,
                                org_ids=org_ids,
                                org_name=org_name,
                            )
                            if prod_data_all:
                                product_found = True
                                sections.append(
                                    f"## Historial de Compras - Producto "
                                    f"'{product_search}' (no hay datos en "
                                    f"{label}, mostrando todo el historial: "
                                    f"{len(prod_data_all)} registros)"
                                )
                                sections.append(
                                    self._format_table(prod_data_all)
                                )
                            else:
                                sections.append(
                                    f"## Búsqueda de Producto "
                                    f"'{product_search}'\n"
                                    f"No se encontraron compras para "
                                    f"'{product_search}' en ningún período "
                                    f"registrado.\nVerifica el nombre o "
                                    f"código del producto."
                                )
                except Exception as exc:
                    logger.warning(
                        "Error buscando historial de producto '%s': %s",
                        product_search, exc,
                    )

            if not product_found:
                summary = build_supply_purchases(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    currency_ids=currency_ids,
                    org_name=org_name,
                )
                sections.append(self._format_summary(
                    summary, f"Resumen de Compras de Insumos - {label}",
                ))

        except Exception as exc:
            logger.error(
                "Error consultando datos de compras de insumos: %s: %s",
                type(exc).__name__, exc, exc_info=True,
            )
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: "
                f"{type(exc).__name__}.\nIntenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None
