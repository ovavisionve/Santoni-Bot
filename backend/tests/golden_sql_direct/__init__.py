"""Golden suite para SQL Directo.

Suite de pruebas automatizadas que invocan directamente a
`process_with_sql_direct()` y validan:

  1. Que Claude genere SQL para preguntas que DEBE resolver con SQL
     (no debe responder NO_SQL para preguntas de datos).
  2. Que el SQL generado pase el validador (solo SELECT, whitelist, etc).
  3. Que la ejecución contra iDempiere devuelva filas (o 0 filas
     documentadas cuando el período/filtro no tiene datos reales).
  4. Que REGLA #9 dispare clarificación para términos ambiguos
     ("inproa" sin calificador, "ventas marzo" sin moneda, etc.)
     en vez de adivinar o caer a fallback.

La suite es complementaria al golden runner clásico
(`tests/golden/runner.py`) que valida agentes tradicionales.

Uso:
    docker compose exec backend python -m tests.golden_sql_direct

Split en varios archivos por dominio para mantener cada uno < 150 líneas:
  - cases_basic.py: queries simples (COUNT, SUM, empleados, cumpleaños)
  - cases_complex.py: agregaciones multi-tabla (CxC aging, ausentismo multi-mes)
  - cases_clarification.py: casos REGLA #9 (org ambigua, moneda ambigua)
  - runner.py: lógica de ejecución, validación y reporte
  - __main__.py: entry point que orquesta
"""

from .cases_basic import CASES_BASIC
from .cases_complex import CASES_COMPLEX
from .cases_clarification import CASES_CLARIFICATION

ALL_CASES = CASES_BASIC + CASES_COMPLEX + CASES_CLARIFICATION

__all__ = [
    "ALL_CASES",
    "CASES_BASIC",
    "CASES_COMPLEX",
    "CASES_CLARIFICATION",
]
