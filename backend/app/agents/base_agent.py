"""
Base class for all SantoniBot specialized agents.
Each department agent inherits from this and implements its own
system prompt, data fetching, and query processing logic.

Supports both full-response (process) and streaming (stream) modes.
"""

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.config import get_settings
from app.services.llm_factory import create_llm

settings = get_settings()
logger = logging.getLogger("santonibot.agents")

# Performance limits
_MAX_TABLE_ROWS = 100
_MAX_HISTORY_MESSAGES = 40
_MAX_TOKENS = 4096

# Days of week in Spanish
_DIAS_SEMANA = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo",
}
_MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def _build_datetime_context() -> str:
    """Build a context string with the current date/time for the LLM."""
    now = datetime.now()
    dia = _DIAS_SEMANA[now.weekday()]
    mes = _MESES_ES[now.month]
    return (
        f"FECHA Y HORA ACTUAL DEL SISTEMA:\n"
        f"- Hoy es: {dia} {now.day} de {mes} de {now.year}\n"
        f"- Hora: {now.strftime('%H:%M')} (Venezuela)\n"
        f"- Mes actual: {mes} {now.year}\n"
        f"- Año actual: {now.year}\n"
        f"\nCuando el usuario diga 'actual', 'hoy', 'este mes', 'del mes', 'este año' "
        f"se refiere a: {mes} {now.year}.\n"
        f"NUNCA respondas con datos de otra fecha a menos que el usuario lo pida explícitamente.\n"
    )


class BaseAgent(ABC):
    """Base agent for all department-specific agents."""

    def __init__(self):
        self.llm = create_llm(
            temperature=0.1,
            max_tokens=_MAX_TOKENS,
            purpose="agent",
        )
        self._system_prompt = self.get_system_prompt()

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier name."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for the agent."""
        ...

    @property
    @abstractmethod
    def department(self) -> str:
        """Department this agent serves."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the agent's capabilities."""
        ...

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        ...

    @abstractmethod
    def get_sql_context(self) -> str:
        """Return SQL schema context relevant to this agent."""
        ...

    def fetch_data(
        self,
        message: str,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
        history: list[tuple[str, str]] | None = None,
    ) -> str | None:
        """
        Fetch relevant data from the database based on the user's message.
        Override in subclasses to provide department-specific data fetching.
        history contains recent conversation tuples: (role, content).
        """
        return None

    def get_capabilities(self) -> str:
        """Return a description of what this agent CAN and CANNOT do.

        Override in subclasses to declare honest capabilities.
        """
        return ""

    def _build_messages(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> tuple[list, bool, str | None]:
        """Build the LLM message list. Returns (messages, has_data, data_context)."""
        # Build datetime context
        datetime_ctx = _build_datetime_context()

        # Build capabilities context
        capabilities = self.get_capabilities()
        capabilities_block = ""
        if capabilities:
            capabilities_block = f"\n\n{capabilities}\n"

        # Enhance system prompt with date, capabilities, and instructions
        enhanced_prompt = (
            self._system_prompt + "\n\n"
            f"{datetime_ctx}"
            f"{capabilities_block}\n"
            "INSTRUCCIONES ADICIONALES:\n"
            "- Si el usuario hace una referencia contextual (ej: 'y por zona?', "
            "'dame mas detalle', 'y del mes pasado?'), usa el historial para entender el contexto.\n"
            "- Si pide COMPARACION entre periodos, presenta tabla comparativa "
            "con columnas: Concepto | Periodo 1 | Periodo 2 | Variacion | %.\n"
            "- Formato venezolano: punto=miles, coma=decimal (ej: 1.234.567,89).\n"
            "\nREGLAS ANTI-INVENCIÓN (OBLIGATORIAS):\n"
            "- Presenta SOLO los datos que recibes en 'DATOS REALES DE LA BASE DE DATOS'. NO agregues datos adicionales.\n"
            "- Si quieres mostrar un porcentaje, CALCÚLALO de los datos reales (ej: valor/total*100).\n"
            "- NUNCA digas 'vs mes anterior' o 'comparativo' si NO tienes datos de ambos períodos.\n"
            "- NUNCA agregues secciones de 'Recomendaciones' o 'Plan de acción' con información inventada.\n"
            "- NUNCA inventes nombres de clientes, proveedores, empleados, productos ni montos.\n"
            "- NUNCA inventes números de factura (FAC-xxxx), números de lote, porcentajes de humedad ni precios.\n"
            "- Las únicas sugerencias permitidas son consultas que el sistema realmente puede ejecutar.\n"
            "- Si los datos muestran un solo período, NO inventes comparativos con otros períodos.\n"
            "- PROHIBIDO copiar nombres o datos del historial de conversación para responder una nueva consulta.\n"
            "- Cada respuesta debe basarse EXCLUSIVAMENTE en los 'DATOS REALES' proporcionados para ESA consulta.\n"
            "- Si los datos muestran 5 empleados, tu tabla debe tener EXACTAMENTE 5 filas, ni más ni menos.\n"
            "\nREGLAS DE CONTEO Y TOTALES (CRÍTICAS):\n"
            "- Cuando los datos incluyen 'TOTAL EXACTO: N', debes usar ESE número como total. NO lo recalcules ni lo cambies.\n"
            "- Cuando los datos incluyen 'Total Empleados: N' o 'Total Producciones: N', copia ESE número exacto.\n"
            "- PROHIBIDO inventar totales, promedios o estadísticas que no estén en los datos.\n"
            "- Si cuentas filas en una tabla, el resultado DEBE coincidir con el total indicado en el encabezado.\n"
            "- Si los datos dicen 'Total Monto: 575.030.358,59', NO escribas un número diferente.\n"
            "- NUNCA digas 'Empleados activos: 1.057' si los datos dicen 'Total Empleados: 702'.\n"
            "- PROHIBIDO inventar 'Total deducciones: 0' si los datos muestran deducciones.\n"
            "- Los únicos números que puedes usar son los que aparecen LITERALMENTE en los datos.\n"
        )
        messages = [SystemMessage(content=enhanced_prompt)]

        # Data Catalog: inject real schema/stats context from iDempiere (optional)
        try:
            from app.services.data_catalog import get_catalog_service
            catalog = get_catalog_service()
            catalog_context = catalog.get_department_context(self.department)
            if catalog_context:
                messages.append(SystemMessage(content=catalog_context))
        except Exception as exc:
            logger.debug("Data catalog unavailable for %s: %s", self.name, exc)

        # RAG: retrieve relevant knowledge-base context (optional)
        try:
            from app.services.rag_service import get_rag_service
            rag = get_rag_service()
            rag_context = rag.get_context_for_agent(self.department, message)
            if rag_context:
                messages.append(SystemMessage(content=rag_context))
        except Exception as exc:
            logger.debug("RAG context unavailable for %s: %s", self.name, exc)

        # Fetch real data from the database
        try:
            from app.utils.sentry_utils import set_agent_context, track_query_performance
            set_agent_context(self.name)
            with track_query_performance(self.name, f"{self.name}.fetch_data"):
                data_context = self.fetch_data(message, org_ids=org_ids, salesrep_id=salesrep_id, history=history)
        except Exception as exc:
            logger.error(
                "Error in %s.fetch_data: %s: %s",
                self.name, type(exc).__name__, exc, exc_info=True,
            )
            # Report to Sentry with agent context
            try:
                from app.utils.sentry_utils import capture_agent_error
                capture_agent_error(self.name, exc, {
                    "message": message,
                    "department": self.department,
                })
            except Exception:
                pass
            data_context = (
                f"## Error al consultar datos\n"
                f"Se produjo un error al consultar la base de datos: {type(exc).__name__}.\n"
                f"Informa al usuario que hubo un problema de conexión con la base de datos "
                f"y que intente de nuevo en unos momentos."
            )

        if data_context:
            # Count actual data rows in tables for enforcement
            data_lines = data_context.split("\n")
            data_row_count = sum(
                1 for line in data_lines
                if line.strip().startswith("|")
                and "---" not in line
                and not any(h in line.lower() for h in ["nombre", "codigo", "producto", "proveedor", "concepto", "organizacion", "zona", "banco", "moneda", "cargo", "departamento", "tipo", "estado", "factura", "documento"])
            )
            row_enforcement = ""
            if data_row_count > 0:
                row_enforcement = (
                    f"- CONTEO EXACTO: Los datos contienen {data_row_count} filas de datos. "
                    f"Tu respuesta debe contener EXACTAMENTE {data_row_count} filas de datos, NI UNA MÁS.\n"
                    f"- NUNCA escribas '(Mostrando X de Y registros)' a menos que ESE TEXTO ya aparezca en los datos.\n"
                )

            messages.append(
                SystemMessage(
                    content=(
                        "══════════ DATOS REALES DE LA BASE DE DATOS ══════════\n"
                        "⚠️ INSTRUCCIÓN CRÍTICA: Usa EXCLUSIVAMENTE estos datos para responder.\n"
                        "- NO agregues filas, columnas, nombres, montos ni porcentajes que NO estén aquí.\n"
                        f"{row_enforcement}"
                        "- Si los datos muestran 0 para un campo, muestra 0. NUNCA inventes un valor.\n"
                        "- NO copies datos del historial de conversación para complementar.\n"
                        "- Si falta información que el usuario pidió, di 'no se encontraron datos' y sugiere alternativas.\n"
                        "- PROHIBIDO inventar nombres de personas, empresas, facturas, lotes o buques.\n"
                        "- PROHIBIDO mostrar porcentajes de humedad, proteína o impureza si NO aparecen en los datos.\n"
                        "- CUANDO RESUMAS: copia los totales EXACTOS de los datos. Si dice 'Total Empleados: 702', "
                        "  tu resumen debe decir 702, NO otro número.\n"
                        "- CUANDO CUENTES filas de una tabla: el conteo debe coincidir con lo indicado en el encabezado.\n"
                        "══════════════════════════════════════════════════════\n\n"
                        f"{data_context}"
                    )
                )
            )
        else:
            sql_context = self.get_sql_context()
            messages.append(
                SystemMessage(
                    content=(
                        "⚠️ INSTRUCCIÓN OBLIGATORIA — LA CONSULTA NO ARROJÓ RESULTADOS ⚠️\n\n"
                        "La consulta a la base de datos se ejecutó correctamente pero no arrojó "
                        "resultados para los filtros aplicados (período, producto, organización, etc.).\n\n"
                        "Tu ÚNICA respuesta permitida es:\n"
                        "1. Informar que la consulta no arrojó resultados para ese período/filtro específico.\n"
                        "2. Sugerir alternativas: otro período, otro filtro, o reformular la pregunta.\n"
                        "3. NUNCA digas 'no tengo acceso' ni 'no puedo consultar' — SÍ tienes acceso, "
                        "simplemente no hay registros que coincidan con los filtros.\n\n"
                        "PROHIBIDO TERMINANTEMENTE:\n"
                        "- NO generes tablas con datos numéricos inventados.\n"
                        "- NO inventes nombres de clientes, proveedores, empleados ni productos.\n"
                        "- NO muestres montos, porcentajes ni cifras que no provengan de los datos.\n"
                        "- NO digas 'no tengo acceso', 'no puedo consultar', 'no dispongo de esa información'.\n"
                        "- La base de datos SÍ está conectada y SÍ se ejecutó la consulta.\n\n"
                        + (f"Esquema disponible para referencia:\n{sql_context}" if sql_context else "")
                    )
                )
            )

        # Add conversation history (limited), cleaning corrupted responses
        # IMPORTANT: Strip markdown tables from previous responses to prevent
        # the LLM from recycling/copying data across different queries
        if history:
            for role, content in history[-_MAX_HISTORY_MESSAGES:]:
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "assistant":
                    clean = self._clean_corrupted_response(content)
                    clean = self._strip_tables_from_history(clean)
                    messages.append(AIMessage(content=clean))

        messages.append(HumanMessage(content=message))
        return messages, data_context is not None, data_context

    # Phrases that indicate the LLM is refusing to use provided data
    _NO_ACCESS_PHRASES = [
        "no tengo acceso",
        "no puedo acceder",
        "no dispongo",
        "no tengo acceso directo",
        "no cuento con acceso",
        "no tengo la capacidad",
        "no puedo consultar",
        "mis capacidades están limitadas",
        "no tengo información",
    ]

    @staticmethod
    def _extract_data_fingerprints(data_context: str) -> set[str]:
        """Extract key numeric fingerprints from data context for validation.

        Pulls out significant numbers (>= 4 digits) that appear in the data.
        These are used to verify the LLM response uses real data, not invented.
        """
        if not data_context:
            return set()
        # Extract formatted numbers with thousands separators: 1,234,567.89
        numbers = re.findall(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?', data_context)
        # Also extract large plain numbers (>= 1000)
        plain = re.findall(r'(?<!\d)\d{4,}(?:\.\d+)?(?!\d)', data_context)
        fingerprints = set()
        for n in numbers + plain:
            # Normalize: remove commas
            clean = n.replace(",", "")
            try:
                val = float(clean)
                if val >= 1000:
                    fingerprints.add(clean)
            except ValueError:
                pass
        return fingerprints

    @staticmethod
    def _detect_hallucination(
        response_text: str,
        has_data: bool,
        data_context: str | None = None,
    ) -> bool:
        """Detect if the LLM likely hallucinated data.

        Returns True if hallucination is detected:
        - When no data was provided (has_data=False): tables with numbers = hallucination
        - When data WAS provided (has_data=True): fake invoice/doc numbers = hallucination
        - ALWAYS: "no tengo acceso" phrases when data WAS provided = hallucination
        - When data WAS provided: response numbers don't match data = hallucination
        """
        # ALWAYS check for fake document numbers (these are never real)
        fake_docs = re.search(
            r'(?:FAC|NC|OC|FC|FP)-\d{4,}', response_text
        )
        if fake_docs:
            return True

        # ALWAYS check for fake lote numbers
        fake_lotes = re.search(
            r'(?:Lote|LOTE)\s+(?:MA|AR|PR|IN|MZ)-[A-Z]{2,}-\d{3,}', response_text
        )
        if fake_lotes:
            return True

        # When data WAS provided, detect "no tengo acceso" refusal
        if has_data:
            response_lower = response_text.lower()
            for phrase in BaseAgent._NO_ACCESS_PHRASES:
                if phrase in response_lower:
                    return True

            # NEW: Cross-reference check — verify LLM used real numbers
            # Extract significant numbers from the response tables
            if data_context:
                data_fps = BaseAgent._extract_data_fingerprints(data_context)
                if data_fps:
                    # Extract numbers from response tables only
                    response_table_lines = [
                        line for line in response_text.split("\n")
                        if line.strip().startswith("|") and "---" not in line
                    ]
                    if len(response_table_lines) >= 3:  # header + separator + data
                        response_table_text = "\n".join(response_table_lines)
                        # Get numbers from response tables
                        resp_nums = re.findall(
                            r'\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?',
                            response_table_text,
                        )
                        if resp_nums:
                            # Normalize response numbers (handle both . and , as thousands sep)
                            resp_clean = set()
                            for n in resp_nums:
                                # Venezuelan format: 1.234.567,89 → 1234567.89
                                if "," in n and "." in n:
                                    clean = n.replace(".", "").replace(",", ".")
                                else:
                                    clean = n.replace(",", "")
                                try:
                                    val = float(clean)
                                    if val >= 1000:
                                        resp_clean.add(f"{val:.0f}")
                                except ValueError:
                                    pass

                            # Normalize data fingerprints the same way
                            data_clean = set()
                            for fp in data_fps:
                                try:
                                    data_clean.add(f"{float(fp):.0f}")
                                except ValueError:
                                    pass

                            # If response has significant numbers in tables but
                            # NONE match any data fingerprint → hallucination
                            if resp_clean and data_clean and not resp_clean & data_clean:
                                logger.warning(
                                    "Fingerprint mismatch: response numbers %s "
                                    "don't overlap with data numbers %s",
                                    list(resp_clean)[:5], list(data_clean)[:5],
                                )
                                return True

            return False

        # No data was provided — check for generated tables
        table_with_numbers = re.search(
            r'\|[^|]*\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?[^|]*\|', response_text
        )
        if table_with_numbers:
            return True

        currency_in_table = re.search(
            r'\|[^|]*(?:Bs\.?|USD|\$)\s*\d+[^|]*\|', response_text
        )
        if currency_in_table:
            return True

        # Check for tables with any numbers > 0 (even without formatting)
        table_any_number = re.search(
            r'\|\s*\d+[\d.,]*\s*\|', response_text
        )
        if table_any_number:
            table_rows = re.findall(r'^\|.+\|$', response_text, re.MULTILINE)
            if len(table_rows) >= 4:
                return True

        return False

    @staticmethod
    def _clean_corrupted_response(text: str) -> str:
        """Detect and clean corrupted LLM responses (e.g. repeated text loops).

        Some LLM responses degenerate into repeating the same phrase/sentence.
        This pollutes conversation history and causes follow-up hallucinations.
        """
        if not text or len(text) < 200:
            return text

        # Detect repeated phrases: split into sentences and check for excessive repeats
        sentences = re.split(r'[.!?\n]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) >= 4:
            from collections import Counter
            counts = Counter(sentences)
            most_common_count = counts.most_common(1)[0][1] if counts else 0
            # If any sentence repeats 3+ times, the response is corrupted
            if most_common_count >= 3:
                # Keep only the first ~200 chars + a note
                truncated = text[:200].rsplit(' ', 1)[0]
                return (
                    f"{truncated}...\n\n"
                    "(Nota: la respuesta anterior se cortó por ser repetitiva. "
                    "Los datos fueron consultados correctamente.)"
                )

        return text

    @staticmethod
    def _strip_tables_from_history(text: str) -> str:
        """Remove markdown tables from previous responses to prevent data recycling.

        When follow-up queries ask for different months/filters, the LLM tends to
        copy employee names, IDs, and amounts from previous response tables, generating
        hallucinated data. Stripping tables forces the LLM to use only fresh query results.
        """
        if not text:
            return text

        lines = text.split('\n')
        cleaned_lines = []
        in_table = False
        table_replaced = False

        for line in lines:
            stripped = line.strip()
            # Detect table rows (lines starting with |)
            if stripped.startswith('|') and '|' in stripped[1:]:
                if not in_table:
                    in_table = True
                    table_replaced = False
                if not table_replaced:
                    cleaned_lines.append("*(Se consultaron datos reales — ver respuesta original)*")
                    table_replaced = True
                continue  # Skip table row
            else:
                if in_table:
                    in_table = False
                cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines)
        # Collapse multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', result)
        return result

    @staticmethod
    def _dict_has_data(d: dict) -> bool:
        """Check if a query result dict has any meaningful data rows.

        Returns False if all list values are empty and all numeric totals are 0.
        This prevents the LLM from receiving 'has_data=True' with empty tables,
        which causes it to hallucinate data to fill the void.
        """
        for v in d.values():
            if isinstance(v, list) and len(v) > 0:
                return True
            if isinstance(v, dict):
                # Check nested totals
                for nv in v.values():
                    if isinstance(nv, (int, float)) and nv > 0:
                        return True
                    if isinstance(nv, list) and len(nv) > 0:
                        return True
        return False

    _HALLUCINATION_REPLACEMENT = (
        "La consulta a iDempiere no arrojó resultados para los filtros aplicados.\n\n"
        "**¿Qué puedes intentar?**\n"
        "- Prueba con un período diferente (ej: otro mes o año)\n"
        "- Reformula la pregunta con más detalle\n"
        "- Verifica que los datos del período consultado estén cargados en el sistema\n\n"
        "*Nota: La conexión a iDempiere está activa. Solo muestro datos reales — "
        "no genero datos estimados ni aproximados.*"
    )

    async def process(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> dict:
        """Process a user message and return a complete response."""
        messages, has_data, data_context = self._build_messages(message, history, org_ids, salesrep_id)
        response = await self.llm.ainvoke(messages)

        response_text = response.content

        # Post-response validation: detect hallucination
        if self._detect_hallucination(response_text, has_data, data_context):
            logger.warning(
                "Hallucination detected in %s (has_data=%s). Replacing response.",
                self.name, has_data,
            )
            try:
                from app.utils.sentry_utils import add_breadcrumb
                add_breadcrumb(
                    category="agent",
                    message=f"Hallucination detected in {self.name}",
                    level="warning",
                    data={"agent": self.name, "has_data": has_data},
                )
            except Exception:
                pass
            if has_data:
                # LLM refused to use real data or invented numbers — re-invoke with stronger prompt
                logger.info("Re-invoking %s with anti-hallucination prompt", self.name)
                retry_msg = SystemMessage(content=(
                    "⚠️ TU RESPUESTA ANTERIOR FUE RECHAZADA porque contenía datos inventados "
                    "o dijiste 'no tengo acceso'. ESTO ES INCORRECTO.\n"
                    "Los datos reales YA fueron consultados y están disponibles arriba en "
                    "'DATOS REALES DE LA BASE DE DATOS'.\n"
                    "DEBES usar EXCLUSIVAMENTE esos datos para responder.\n"
                    "NUNCA inventes nombres de proveedores, clientes, productos ni montos.\n"
                    "NUNCA digas que no tienes acceso.\n"
                    "Los ÚNICOS números que puedes usar son los que aparecen LITERALMENTE en los datos.\n"
                    "Genera la respuesta ahora usando EXCLUSIVAMENTE los datos proporcionados."
                ))
                messages.append(retry_msg)
                messages.append(HumanMessage(content=message))
                try:
                    retry_response = await self.llm.ainvoke(messages)
                    response_text = retry_response.content
                    # Check again - if still hallucinating, use fallback
                    if self._detect_hallucination(response_text, has_data, data_context):
                        response_text = self._HALLUCINATION_REPLACEMENT
                except Exception:
                    response_text = self._HALLUCINATION_REPLACEMENT
            else:
                response_text = self._HALLUCINATION_REPLACEMENT

        return {
            "response": response_text,
            "agent_used": self.name,
            "metadata": {
                "department": self.department,
                "has_data": has_data,
            },
        }

    async def stream(
        self,
        message: str,
        history: list[tuple[str, str]] | None = None,
        user_departments: list[str] | None = None,
        org_ids: list[int] | None = None,
        salesrep_id: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream response tokens for real-time display.

        Includes post-stream hallucination detection: accumulates the full
        response and, if hallucination is detected (no real data but tables
        with numbers appeared), replaces the entire response.
        """
        messages, has_data, data_context = self._build_messages(message, history, org_ids, salesrep_id)
        accumulated = []
        async for chunk in self.llm.astream(messages):
            if chunk.content:
                accumulated.append(chunk.content)
                yield chunk.content

        # Post-stream hallucination check
        if accumulated:
            full_response = "".join(accumulated)
            if self._detect_hallucination(full_response, has_data, data_context):
                logger.warning(
                    "Hallucination detected in streamed %s (has_data=%s).",
                    self.name, has_data,
                )
                # Can't un-send tokens in streaming mode, but log for monitoring.
                # The chat.py save logic will record this for audit review.

    @staticmethod
    def _format_table(data: list[dict], columns: list[str] | None = None) -> str:
        """Format a list of dicts as a markdown table string for LLM context."""
        if not data:
            return "La consulta no arrojó resultados para los filtros aplicados."

        cols = columns or list(data[0].keys())
        header = "| " + " | ".join(str(c).replace("_", " ").title() for c in cols) + " |"
        separator = "| " + " | ".join("---" for _ in cols) + " |"

        rows = []
        for row in data[:_MAX_TABLE_ROWS]:
            values = []
            for c in cols:
                v = row.get(c, "")
                if isinstance(v, float):
                    values.append(f"{v:,.2f}")
                else:
                    values.append(str(v) if v is not None else "-")
            rows.append("| " + " | ".join(values) + " |")

        table = "\n".join([header, separator] + rows)
        if len(data) > _MAX_TABLE_ROWS:
            table += f"\n\n*(Mostrando {_MAX_TABLE_ROWS} de {len(data)} registros)*"
        return table

    @staticmethod
    def _format_summary(data: dict, title: str = "") -> str:
        """Format a summary dict as readable text for LLM context."""
        lines = []
        if title:
            lines.append(f"## {title}")

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"\n### {key.replace('_', ' ').title()}")
                for k, v in value.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        # Nested list of dicts inside a dict — render as table
                        lines.append(f"\n#### {k.replace('_', ' ').title()} [{len(v)} registros exactos]")
                        lines.append(BaseAgent._format_table(v))
                    elif isinstance(v, float):
                        lines.append(f"- {k.replace('_', ' ').title()}: {v:,.2f}")
                    else:
                        lines.append(f"- {k.replace('_', ' ').title()}: {v}")
            elif isinstance(value, list):
                lines.append(f"\n### {key.replace('_', ' ').title()} [{len(value)} registros exactos]")
                if value and isinstance(value[0], dict):
                    lines.append(BaseAgent._format_table(value))
                else:
                    for item in value[:20]:
                        lines.append(f"- {item}")
            elif isinstance(value, float):
                lines.append(f"- {key.replace('_', ' ').title()}: {value:,.2f}")
            else:
                lines.append(f"- {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines)
