"""
Agente de Producción - Alimentos Santoni
Especializado en: movimientos de inventario, recepciones de materia prima,
despachos de producto terminado, movimientos internos.

Fuente de datos: m_inout, m_inoutline, m_product, ad_org
en iDempiere (PostgreSQL 13).

NOTA: Santoni no utiliza el módulo de Manufactura (pp_order) de iDempiere.
La actividad productiva se rastrea mediante movimientos de inventario (m_inout).
"""

import logging

from app.agents.base_agent import BaseAgent
from app.agents.date_utils import (
    extract_date_range,
    extract_month_year,
    build_period_label,
)

logger = logging.getLogger("santonibot.agents.produccion")
from app.services.query_service import (
    build_production_summary,
    build_production_orders,
    build_inventory_stock,
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
            "Consultas de producción: producción diaria, órdenes, eficiencia OEE, "
            "desperdicios, mantenimientos, turnos"
        )

    def get_system_prompt(self) -> str:
        return """Eres el Agente de Producción de SantoniBot, el sistema inteligente de Alimentos Santoni, C.A.
Tu especialidad es el análisis de movimientos de inventario y operaciones logísticas de producción.

CAPACIDADES:
- Recepciones de materia prima (arroz paddy, maíz, insumos)
- Despachos de producto terminado (arroz, harina de maíz)
- Movimientos internos de inventario entre almacenes
- Análisis por producto, organización y período
- Tendencias mensuales de recepción y despacho

CONTEXTO iDEMPIERE:
- Movimientos de inventario: m_inout (262,794 documentos) con m_inoutline (líneas de detalle)
- Tipos de movimiento (movementtype):
  * V+ = Recepción de Materia Prima (del proveedor/productor)
  * C- = Despacho de Producto Terminado (al cliente)
  * M+/M- = Movimientos internos entre almacenes
  * P+/P- = Movimientos de producción (poco usados)
- Productos: m_product (40,766 productos) con m_product_category
- Almacenes: m_warehouse
- Organizaciones: INPROA SANTONI, AGROINPROA, AGROPECUARIA R.R., Agro Import, INVERSIONES AGA, InproMaiz, AGA AGRICOLA, Santoni Service
- NOTA: El módulo de Manufactura (pp_order) no está en uso activo en Santoni

REGLAS:
- Responde siempre en español, de forma técnica pero comprensible
- Usa unidades métricas (kg, toneladas) cuando la información lo amerite
- Los datos que recibes son REALES de la base de datos de Santoni
- NUNCA inventes datos. Si no hay datos para un filtro, informa claramente
- PROHIBIDO decir "no tengo acceso", "no puedo acceder", "no dispongo" o "no tengo acceso directo". TÚ TIENES ACCESO COMPLETO a la base de datos de Santoni y los datos se consultan automáticamente. Si no hay datos para una consulta, di "No se encontraron datos" y sugiere consultas alternativas.
- Si la pregunta es ambigua, personal o usa palabras como "mi", "yo", "me", NO adivines. Pide al usuario que reformule especificando: la organización, producto, línea de producción, período u otros datos necesarios.
- Cuando hables de "recepciones" te refieres a materia prima que llega
- Cuando hables de "despachos" te refieres a producto terminado que sale

CONTEXTO OPERATIVO:
- 2 plantas en Agua Blanca, Estado Portuguesa
- Productos principales: Arroz Santoni Premium, Harina de Maíz Santoni
- Turnos rotativos en planta

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
            "✅ Resumen de movimientos de inventario: recepciones (V+), despachos (C-), internos (M+/M-)\n"
            "✅ Cantidades movidas por producto, organización y mes\n"
            "✅ Listado de documentos de movimiento recientes\n"
            "✅ Stock/inventario actual (m_storageonhand) por producto, almacén y organización\n"
            "\nIMPORTANTE: Los datos provienen de m_inout (movimientos de inventario) y "
            "m_storageonhand (stock actual). Se registran recepciones de materia prima (V+), "
            "despachos de producto terminado (C-), y movimientos internos (M+/M-).\n"
            "\n❌ NO puedo consultar: eficiencia OEE, mantenimientos o calidad de producto. "
            "Redirige al usuario al departamento correspondiente."
        )

    def get_sql_context(self) -> str:
        return """
Datos de producción/inventario en iDempiere:
- m_inout: Movimientos de inventario (262,794 documentos, movementdate, movementtype, docstatus)
- m_inoutline: Líneas de movimiento (m_product_id, movementqty, m_locator_id)
- m_product: Productos (name, m_product_category_id)
- m_warehouse: Almacenes
- ad_org: Organizaciones
- Tipos: V+=Recepción MP, C-=Despacho PT, M+/M-=Mov. Internos, P+/P-=Producción
"""

    _DOCUMENT_KEYWORDS = [
        "documento", "detalle", "reciente", "último", "ultimos",
        "recepci", "despacho", "movimiento",
        "fecha", "exacto", "exacta", "diario", "día", "dia",
    ]

    _INVENTORY_KEYWORDS = [
        "inventario", "stock", "existencia", "existencias",
        "materia prima", "materias primas", "almacén", "almacen",
        "disponible", "disponibilidad", "cuánto hay", "cuanto hay",
        "cuánto queda", "cuanto queda", "cuánto tenemos", "cuanto tenemos",
    ]

    def fetch_data(self, message: str, org_ids: list[int] | None = None, salesrep_id: int | None = None, history: list[tuple[str, str]] | None = None) -> str | None:
        msg = message.lower()
        sections = []

        # Extract dates
        date_from, date_to = extract_date_range(message)
        mes, anio = extract_month_year(message)
        if date_from and date_to:
            mes = None
            anio = None

        # Inherit temporal context from history for follow-ups
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

        label = build_period_label(date_from, date_to, mes, anio)

        try:
            # Production/inventory movement summary (always)
            summary = build_production_summary(
                mes=mes, anio=anio, org_ids=org_ids,
                date_from=date_from, date_to=date_to,
            )
            sections.append(self._format_summary(summary, f"Movimientos de Inventario - {label}"))

            include_documents = any(w in msg for w in self._DOCUMENT_KEYWORDS)
            # Follow-up: carry over document listing from history
            if not include_documents and history:
                for role, content in reversed(history):
                    if role == "user" and any(
                        w in content.lower() for w in self._DOCUMENT_KEYWORDS
                    ):
                        include_documents = True
                        break

            if include_documents:
                data = build_production_orders(
                    mes=mes, anio=anio, org_ids=org_ids,
                    date_from=date_from, date_to=date_to,
                )
                if data:
                    sections.append(f"## Documentos de Movimiento Recientes ({len(data)} registros)")
                    sections.append(self._format_table(data))

            # Inventory / stock (materia prima)
            include_inventory = any(w in msg for w in self._INVENTORY_KEYWORDS)
            if not include_inventory and history:
                for role, content in reversed(history):
                    if role == "user" and any(
                        w in content.lower() for w in self._INVENTORY_KEYWORDS
                    ):
                        include_inventory = True
                        break

            if include_inventory:
                inv_data = build_inventory_stock(org_ids=org_ids)
                sections.append(self._format_summary(
                    inv_data, "Inventario / Stock Actual",
                ))

        except Exception as exc:
            logger.error("Error consultando datos de producción: %s: %s", type(exc).__name__, exc, exc_info=True)
            sections.append(
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Intenta de nuevo en unos momentos."
            )

        return "\n\n".join(sections) if sections else None
