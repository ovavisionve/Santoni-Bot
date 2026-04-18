"""System prompts para SQL Directo.

Se arma el prompt cacheable concatenando:
  - intro (texto inicial + REGLA #1)
  - REGLAs 2-3 (separar NC, destacar anulatorias)
  - REGLAs 4-5 (fuente de datos, desgloses completos)
  - REGLA 6a y 6b (mapeo columna→tabla, sintaxis PostgreSQL)
  - REGLAs 7-8 (aritmética mental, flujo documentos)
  - VIEWS_CATALOG (catálogo de views y reglas SQL)
  - instrucciones (12 instrucciones finales)

El resultado se expone como `SYSTEM_PROMPT_TEMPLATE` — un string formateable
que se concatena en `processor.py` con el `datetime_ctx` dinámico.
"""

from app.services.sql_direct.catalog import VIEWS_CATALOG

from .intro import INTRO, REGLA_1_DESGLOSE_ORG
from .reglas_2_3 import REGLA_2_SEPARAR_NC, REGLA_3_ANULATORIAS
from .reglas_4_5 import REGLA_4_FUENTE_DATOS, REGLA_5_DESGLOSES_COMPLETOS
from .regla_6a import REGLA_6_PARTE_A
from .regla_6b import REGLA_6_PARTE_B
from .reglas_7_8 import REGLA_7_ARITMETICA, REGLA_8_FLUJO_DOC
from .regla_9 import REGLA_9_CLARIFICACION
from .instrucciones import INSTRUCCIONES
from .format_prompt import FORMAT_SYSTEM_PROMPT

SYSTEM_PROMPT_TEMPLATE = (
    INTRO
    + REGLA_1_DESGLOSE_ORG
    + REGLA_2_SEPARAR_NC
    + REGLA_3_ANULATORIAS
    + REGLA_4_FUENTE_DATOS
    + REGLA_5_DESGLOSES_COMPLETOS
    + REGLA_6_PARTE_A
    + REGLA_6_PARTE_B
    + REGLA_7_ARITMETICA
    + REGLA_8_FLUJO_DOC
    + REGLA_9_CLARIFICACION
    + f"{VIEWS_CATALOG}\n\n"
    + INSTRUCCIONES
)

__all__ = ["SYSTEM_PROMPT_TEMPLATE", "FORMAT_SYSTEM_PROMPT"]
