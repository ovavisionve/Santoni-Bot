"""
Agente de Producción - Alimentos Santoni
Especializado en: producciones reales (m_production), movimientos de inventario (m_inout),
movimientos entre almacenes (m_movement), stock actual, y recetas/BOMs.

Fuente de datos: m_production, m_productionline, m_inout, m_inoutline,
m_movement, m_movementline, pp_product_bom, pp_product_bomline,
m_storageonhand, m_product, ad_org en iDempiere (PostgreSQL 13).
"""

import logging
import re

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)
from app.agents.keywords import (
    PRODUCCION_GENERAL,
    PRODUCCION_MATERIA_PRIMA,
    PRODUCCION_RECETAS,
    PRODUCCION_ALMACENES,
    PRODUCCION_DOCUMENTOS,
    COMPRAS_INVENTARIO,
    matches_any,
)

logger = logging.getLogger("santonibot.agents.produccion")
from app.services.query_service import (
    build_production_summary,
    build_production_orders,
    build_inventory_stock,
    build_production_runs,
    build_bom_info,
    build_warehouse_movements,
)


class ProduccionAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "produccion"

    @property
    def display_name(self) -> str:
        return "Producción"

    @property
    def department(self) -> str:
        return "produccion"

    @property
    def description(self) -> str:
        return (
            "Consultas de producción: órdenes de producción, productos terminados, "
            "insumos consumidos, recetas/BOMs, movimientos entre almacenes, "
            "recepciones de materia prima, despachos de producto terminado, stock actual"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Producción de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis de producción, movimientos de inventario y operaciones logísticas.

CAPACIDADES:
1. **Producciones reales (m_production)**: Órdenes de producción completadas, productos terminados fabricados, insumos/materias primas consumidas
2. **Recetas/BOMs (pp_product_bom)**: Bill of Materials — ingredientes y cantidades para fabricar cada producto
3. **Recepciones y despachos (m_inout)**: Materia prima recibida (V+), producto terminado despachado (C-)
4. **Movimientos entre almacenes (m_movement)**: Transferencias internas entre almacenes/silos
5. **Stock actual (m_storageonhand)**: Inventario actual por producto, almacén y organización

CONTEXTO iDEMPIERE:
- Producciones: m_production con m_productionline (producto terminado + insumos consumidos)
- Recetas: pp_product_bom con pp_product_bomline (componentes/ingredientes)
- Movimientos de inventario: m_inout, tipos: V+=Recepción MP, C-=Despacho PT, C+=Devolución cliente
- Movimientos internos: m_movement entre almacenes/silos
- Stock: m_storageonhand por producto/almacén/organización
- Organizaciones: INPROA SANTONI (arroz), InproMaiz (maíz), AGROINPROA, AGROPECUARIA R.R., AGA AGRICOLA, Santoni Service, INVERSIONES AGA, Agro Import
- IMPORTANTE: Los conteos exactos de producciones, BOMs, documentos, etc. SOLO están en los datos reales que recibes. NUNCA cites cifras de este contexto como si fueran datos.

REGLAS:
- Responde siempre en español, de forma técnica pero comprensible
- Usa unidades métricas (kg, toneladas) cuando la información lo amerite
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta, di "No se encontraron datos" y sugiere consultas alternativas.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me", NO adivines. Pide al usuario que reformule especificando: la organización, producto, línea de producción, período u otros datos necesarios.
- Cuando hables de "recepciones" te refieres a materia prima que llega
- Cuando hables de "despachos" te refieres a producto terminado que sale
- Cuando hables de "producciones" te refieres a órdenes de producción completadas en m_production

ANTI-ALUCINACIÓN (MUY IMPORTANTE):
- SOLO presenta datos que aparezcan EXPLÍCITAMENTE en el contexto de datos que recibes
- Si ves "Total Producciones: 0" o "La consulta no arrojó resultados", responde "No se encontraron datos para ese filtro" — NUNCA inventes cifras, nombres de productos ni cantidades
- Los nombres de productos REALES en iDempiere son como "ARROZ SANTONI PREMIUN 900GR X 24UND", "HARINA DE MAIZ BLANCO () MASANTONI 900GR", "CHICHA TONI 12UNID DE 250Gr", "NUTRI TONI 12UNID DE 400GR" — NO los simplifiques ni inventes nombres genéricos como "Arroz Santoni Blanco" o "Harina de Maíz Santoni"
- Si los datos muestran un "Error al consultar", informa del error y pide al usuario que intente de nuevo — NUNCA completes con datos imaginados
- Cada tabla incluye un conteo "[N filas reales]". No agregues filas ni modifiques cantidades

CONTEXTO OPERATIVO:
- 2 plantas en Agua Blanca, Estado Portuguesa
- Productos principales: Arroz Santoni (varios tipos), Harina de Maíz Santoni, Choco Toni, Nutri Toni
- Producción registrada en m_production: producto terminado (isendproduct='Y') + insumos consumidos (isendproduct='N')
- 229 recetas (BOMs) definidas con componentes detallados

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
            "✅ Producciones reales: órdenes de producción completadas, productos fabricados, insumos consumidos\n"
            "✅ Recetas/BOMs: ingredientes y cantidades para fabricar cada producto\n"
            "✅ Resumen de movimientos de inventario: recepciones (V+), despachos (C-), devoluciones (C+)\n"
            "✅ Movimientos entre almacenes: transferencias internas entre almacenes/silos\n"
            "✅ Cantidades movidas por producto, organización y mes\n"
            "✅ Listado de documentos de movimiento recientes\n"
            "✅ Stock/inventario actual (m_storageonhand) por producto, almacén y organización\n"
            "\n❌ NO puedo consultar: eficiencia OEE, mantenimientos o calidad de producto. "
            "Redirige al usuario al departamento correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos de producción en iDempiere:
- m_production: Producciones reales (movementdate, productionqty, docstatus)
- m_productionline: Líneas de producción (m_product_id, movementqty, isendproduct: Y=terminado, N=insumo)
- pp_product_bom: Bill of Materials / recetas
- pp_product_bomline: Componentes de cada BOM (m_product_id, qtybom, c_uom_id)
- m_inout: Movimientos de inventario (movementdate, movementtype, docstatus)
- m_inoutline: Líneas de movimiento (m_product_id, movementqty, m_locator_id)
- m_movement: Movimientos internos entre almacenes
- m_movementline: Líneas de movimiento interno (m_locator_id, m_locatorto_id, m_product_id, movementqty)
- m_storageonhand: Stock actual por producto/almacén
- m_product: Productos (name, m_product_category_id)
- m_warehouse: Almacenes
- ad_org: Organizaciones
"""

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

    # Keyword sets — from centralized keywords.py
    _PRODUCTION_KW_SET = PRODUCCION_GENERAL | PRODUCCION_MATERIA_PRIMA
    _BOM_KW_SET = PRODUCCION_RECETAS
    _MOVEMENT_KW_SET = PRODUCCION_ALMACENES
    _DOCUMENT_KW_SET = PRODUCCION_DOCUMENTOS
    _INVENTORY_KW_SET = COMPRAS_INVENTARIO

    @classmethod
    def _extract_product_search(cls, msg: str) -> str | None:
        """Extract product name from message for production queries."""
        msg_lower = msg.lower()
        # Look for product names after key phrases (order matters: longer first)
        _PATTERNS = [
            "producción de ", "produccion de ", "fabricación de ",
            "fabricacion de ", "receta de la ", "receta del ",
            "receta de ", "bom de ", "bom del ",
            "ingredientes del ", "ingredientes de la ",
            "ingredientes de ", "ingredientes lleva el ",
            "ingredientes lleva la ", "ingredientes lleva ",
            "componentes del ", "componentes de la ",
            "componentes de ", "qué lleva el ", "que lleva el ",
            "qué lleva la ", "que lleva la ",
            "qué tiene el ", "que tiene el ",
            "cómo se hace el ", "como se hace el ",
            "cómo se hace la ", "como se hace la ",
            "stock de ", "stock del ", "stock actual de ",
            "inventario de ", "inventario del ",
            "producción del ", "produccion del ",
        ]
        for pattern in _PATTERNS:
            if pattern in msg_lower:
                after = msg_lower.split(pattern, 1)[1].strip()
                # Take first meaningful chunk (up to punctuation or common stop words)
                for stop in ["?", ".", ",", " en ", " para ", " durante "]:
                    if stop in after:
                        after = after.split(stop, 1)[0].strip()
                if after and len(after) > 2:
                    return after
        return None

    @staticmethod
    def _row_count_marker(data: dict) -> str:
        """Add explicit row count markers to prevent LLM hallucination."""
        counts = []
        for key, value in data.items():
            if isinstance(value, list):
                counts.append(f"[{key}: {len(value)} filas reales]")
            elif isinstance(value, dict) and "total_producciones" in value:
                counts.append(f"[total_producciones: {value['total_producciones']}]")
            elif isinstance(value, dict) and "total_movimientos" in value:
                counts.append(f"[total_movimientos: {value['total_movimientos']}]")
            elif isinstance(value, dict) and "total_boms" in value:
                counts.append(f"[total_boms: {value['total_boms']}]")
        return "**Conteo verificado:** " + ", ".join(counts) if counts else ""

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None
            anio = None

        # Extract organization name from message
        org_name = self._extract_org_name(message)

        # Inherit temporal context and org_name from history for follow-ups
        if not date_from and not date_to and not mes and history:
            for role, content in reversed(history):
                if role != "user":
                    continue
                df, dt = extract_date_range(content)
                if df and dt:
                    date_from, date_to = df, dt
                    break
                m, a = extract_month_year(content)
                if m:
                    mes, anio = m, a
                    break
                elif re.search(r'20\d{2}', content):
                    anio = a
                    break
        if not org_name and history:
            for role, content in reversed(history):
                if role != "user":
                    continue
                o = self._extract_org_name(content)
                if o:
                    org_name = o
                    break

        label = build_period_label(date_from, date_to, mes, anio)
        product_search = self._extract_product_search(message)

        try:
            # Detect what the user is asking about
            wants_production = matches_any(msg, self._PRODUCTION_KW_SET)
            wants_bom = matches_any(msg, self._BOM_KW_SET)
            wants_movements = matches_any(msg, self._MOVEMENT_KW_SET)
            wants_documents = matches_any(msg, self._DOCUMENT_KW_SET)
            wants_inventory = matches_any(msg, self._INVENTORY_KW_SET)

            # Follow-up: inherit intent from history
            if not any([wants_production, wants_bom, wants_movements, wants_documents, wants_inventory]) and history:
                for role, content in reversed(history):
                    if role != "user":
                        continue
                    c = content.lower()
                    if matches_any(c, self._PRODUCTION_KW_SET):
                        wants_production = True
                        break
                    if matches_any(c, self._BOM_KW_SET):
                        wants_bom = True
                        break
                    if matches_any(c, self._MOVEMENT_KW_SET):
                        wants_movements = True
                        break
                    if matches_any(c, self._DOCUMENT_KW_SET):
                        wants_documents = True
                        break
                    if matches_any(c, self._INVENTORY_KW_SET):
                        wants_inventory = True
                        break

            # If no specific intent detected, show production runs + movement summary
            if not any([wants_production, wants_bom, wants_movements, wants_documents, wants_inventory]):
                wants_production = True

            # 1. Production activity — primary data from m_inout + supplementary from m_production
            if wants_production:
                # m_inout is the PRIMARY source of production data in Santoni's iDempiere.
                # Santoni tracks production via material movements (V+=receipt, C-=shipment,
                # P+=production), NOT via the Manufacturing module (pp_order is empty).
                # m_production only has ~32 records (BATCH SIROPE), not representative.
                summary = build_production_summary(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    org_name=org_name,
                )
                total_movs = summary.get("totales", {}).get("total_movimientos", 0)
                if total_movs > 0:
                    sections.append(self._format_summary(summary, f"Actividad de Producción (Movimientos) - {label}"))
                    sections.append(self._row_count_marker(summary))

                # Also include m_production data if any exists (supplementary)
                prod_data = build_production_runs(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    org_name=org_name, product_search=product_search,
                )
                total_prods = prod_data.get("totales", {}).get("total_producciones", 0)
                if total_prods > 0:
                    sections.append(self._format_summary(prod_data, f"Producciones Directas (m_production) - {label}"))
                    sections.append(self._row_count_marker(prod_data))

                # If neither source has data, inform the user
                if total_movs == 0 and total_prods == 0:
                    sections.append(
                        f"## Producción - {label}\n"
                        f"**RESULTADO: 0 registros de producción encontrados** para el período {label}.\n"
                        f"No se encontraron movimientos de inventario ni producciones directas.\n"
                        f"PROHIBIDO inventar cifras. Solo informa que no hay datos y sugiere consultas alternativas."
                    )

            # 2. BOMs / recipes
            if wants_bom:
                bom_data = build_bom_info(
                    product_search=product_search,
                    org_ids=org_ids,
                    org_name=org_name,
                )
                if self._dict_has_data(bom_data):
                    sections.append(self._format_summary(bom_data, "Recetas / Bill of Materials (BOM)"))
                    sections.append(self._row_count_marker(bom_data))

            # 3. Warehouse movements (m_movement)
            if wants_movements:
                mov_data = build_warehouse_movements(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    org_name=org_name,
                )
                if self._dict_has_data(mov_data):
                    sections.append(self._format_summary(mov_data, f"Movimientos entre Almacenes - {label}"))
                    sections.append(self._row_count_marker(mov_data))

            # 4. Material movements (m_inout) — recepciones/despachos
            if wants_documents:
                # Avoid duplicating build_production_summary if already called above
                if not wants_production:
                    summary = build_production_summary(
                        mes=mes, anio=anio, org_ids=org_ids,
                        date_from=date_from, date_to=date_to,
                        org_name=org_name,
                    )
                    sections.append(self._format_summary(summary, f"Movimientos de Inventario - {label}"))
                    sections.append(self._row_count_marker(summary))

                data = build_production_orders(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                    org_name=org_name,
                )
                if data:
                    sections.append(f"## Documentos de Movimiento Recientes [{len(data)} filas reales]")
                    sections.append(self._format_table(data))
                else:
                    sections.append("## Documentos de Movimiento Recientes [0 filas reales]")

            # 5. Inventory / stock
            if wants_inventory:
                inv_data = build_inventory_stock(
                    org_ids=org_ids,
                    product_search=product_search,
                    org_name=org_name,
                )
                sections.append(self._format_summary(
                    inv_data, "Inventario / Stock Actual",
                ))
                sections.append(self._row_count_marker(inv_data))

        except Exception as exc:
            logger.error("Error consultando datos de producción: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None
