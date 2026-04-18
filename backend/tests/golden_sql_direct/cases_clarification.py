"""Casos de REGLA #9 — clarificación de términos ambiguos.

Estos casos verifican que Claude NO adivine cuando el usuario usa términos
con múltiples interpretaciones válidas. El bot debe devolver NO_SQL seguido
de una pregunta al usuario, y el processor debe surfacear esa pregunta
(en vez de caer a fallback).

Casos cubiertos:
  (a) Org ambigua: "inproa" sin calificador
  (b) Moneda ambigua: "total ventas marzo" sin moneda
  (c) Producto ambiguo: "compras de grano" (arroz vs maíz)

También probamos las EXCEPCIONES de REGLA #9: cuando el historial tiene
contexto claro, el bot NO debe preguntar.
"""

CASES_CLARIFICATION = [
    {
        "id": "org_ambigua_inproa_sin_contexto",
        "pregunta": "ventas de inproa en febrero 2026",
        "history": [],
        "expect_sql": False,
        "expect_clarification": True,
        "clarification_keywords": ["INPROA SANTONI", "InproMaiz", "AGROINPROA"],
        "notes": (
            "REGLA #9(a). 3 orgs matchean '%inproa%' → bot debe preguntar, "
            "no adivinar."
        ),
    },
    {
        "id": "moneda_ambigua_ventas_marzo",
        "pregunta": "total ventas marzo 2026",
        "history": [],
        "expect_sql": False,
        "expect_clarification": True,
        "clarification_keywords": ["bolívares", "dólares"],
        "notes": (
            "REGLA #9(b). Sin moneda → bot debe preguntar. Bs y USD no "
            "son comparables ni sumables."
        ),
    },
    {
        "id": "producto_ambiguo_compras_grano",
        "pregunta": "compras de grano en marzo 2026",
        "history": [],
        "expect_sql": False,
        "expect_clarification": True,
        "clarification_keywords": ["arroz", "maíz"],
        "notes": (
            "REGLA #9(d). 'grano' puede ser arroz paddy o maíz. "
            "Santoni compra ambos con lineamientos distintos."
        ),
    },
    {
        "id": "excepcion_org_en_historial",
        "pregunta": "¿y las de febrero?",
        "history": [
            ("user", "ventas de INPROA SANTONI en enero 2026 en bolívares"),
            ("assistant", "INPROA SANTONI vendió Bs. 3.200.000.000,00 en enero 2026."),
        ],
        "expect_sql": True,
        "expect_clarification": False,
        "clarification_keywords": [],
        "notes": (
            "EXCEPCIÓN REGLA #9(a). Historial ya tiene INPROA SANTONI "
            "+ moneda → bot sigue con ese contexto, NO pregunta."
        ),
    },
    {
        "id": "excepcion_moneda_en_historial",
        "pregunta": "total ventas marzo 2026",
        "history": [
            ("user", "ventas de INPROA SANTONI en febrero 2026 en dólares"),
            ("assistant", "INPROA SANTONI vendió USD 1.200.000 en febrero 2026."),
        ],
        "expect_sql": True,
        "expect_clarification": False,
        "clarification_keywords": [],
        "notes": (
            "EXCEPCIÓN REGLA #9(b). Historial ya mencionó dólares → "
            "bot asume dólares sin preguntar."
        ),
    },
    {
        "id": "periodo_ambiguo_no_requiere_pregunta",
        "pregunta": "ventas recientes de INPROA SANTONI en bolívares",
        "history": [],
        "expect_sql": True,
        "expect_clarification": False,
        "clarification_keywords": [],
        "notes": (
            "REGLA #9(c). 'recientes' sin fecha → asumir mes corriente "
            "(default razonable). NO preguntar."
        ),
    },
    {
        "id": "empleados_activos_sin_fecha",
        "pregunta": "empleados activos en AGROINPROA",
        "history": [],
        "expect_sql": True,
        "expect_clarification": False,
        "clarification_keywords": [],
        "notes": (
            "REGLA #9(c). 'activos' sin fecha → todos los activos actualmente. "
            "view LVE ya filtra esto. NO preguntar."
        ),
    },
]
