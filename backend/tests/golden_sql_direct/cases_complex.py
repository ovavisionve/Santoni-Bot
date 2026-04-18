"""Casos complejos para SQL Directo.

Queries con agregaciones multi-tabla, CTEs, UNION ALL (desglose + total),
correlacionadas escalares (CxC aging), multi-mes.

Estos casos verifican que Claude entienda los patrones documentados en
REGLAs #6, #7 y en los ejemplos del catálogo:
  - Desglose por organización cuando la pregunta es macro
  - UNION ALL con columna `sort_order` auxiliar
  - Scalar correlated subquery para CxC aging
  - Discriminación ARI vs ARC en conteo de facturas
"""

CASES_COMPLEX = [
    {
        "id": "ventas_usd_marzo_desglose_por_org",
        "pregunta": "Total de ventas en dólares en marzo 2026",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["c_invoice", "c_doctype"],
        "forbidden_tables": [],
        "must_contain_keywords": ["GROUP BY", "ad_org_id"],
        "notes": (
            "Pregunta agregada sin org específica → debe agrupar por ad_org_id "
            "(REGLA #1). Discriminar facturas vs notas de crédito."
        ),
    },
    {
        "id": "ausentismo_agroinproa_marzo",
        "pregunta": "Ausentismo en AGROINPROA en marzo 2026",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["hr_movement", "hr_concept"],
        "forbidden_tables": [],
        "must_contain_keywords": ["ILIKE", "%Permiso%"],
        "notes": "ILIKE genérico (%Falta%, %Permiso%, %Reposo%). UNION ALL con TOTAL.",
    },
    {
        "id": "cxc_aging_inpromaiz",
        "pregunta": "Facturas vencidas de InproMaiz con más de 60 días",
        "history": [],
        "expect_sql": True,
        "min_rows": 0,
        "must_contain_tables": ["c_invoice", "c_allocationline"],
        "forbidden_tables": [],
        "must_contain_keywords": ["c_allocationhdr"],
        "notes": (
            "Scalar correlated subquery sobre c_allocationline "
            "(REGLA #6b). Alias `i.c_invoice_id` visible en subquery."
        ),
    },
    {
        "id": "resumen_nomina_inproa_marzo",
        "pregunta": "Resumen de nómina de INPROA SANTONI en marzo 2026 por tipo",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["hr_movement", "hr_process", "hr_payroll"],
        "forbidden_tables": [],
        "must_contain_keywords": ["UNION ALL", "TOTAL"],
        "notes": (
            "Desglose por tipo_nomina + TOTAL GENERAL vía UNION ALL. "
            "hr_movement.validfrom, NO hr_process.hrdate (inexistente)."
        ),
    },
    {
        "id": "ventas_multi_moneda_marzo_desglose",
        "pregunta": "Ventas de marzo 2026 en bolívares y dólares por separado",
        "history": [],
        "expect_sql": True,
        "min_rows": 2,
        "must_contain_tables": ["c_invoice"],
        "forbidden_tables": [],
        "must_contain_keywords": ["c_currency_id"],
        "notes": "Usuario pide ambas monedas explícitamente → NO clarificar, ejecutar.",
    },
    {
        "id": "producto_antiguedad_empleados_inproa",
        "pregunta": "Empleados con más de 5 años de antigüedad en INPROA SANTONI",
        "history": [],
        "expect_sql": True,
        "min_rows": 0,
        "must_contain_tables": ["lve_empleadosactivos"],
        "forbidden_tables": ["hr_employee"],
        "must_contain_keywords": ["AGE", "startdate"],
        "notes": "EXTRACT(YEAR FROM AGE(CURRENT_DATE, startdate)). Usar alias `v.`.",
    },
    {
        "id": "historial_followup_orgs",
        "pregunta": "¿Y ahora en InproMaiz?",
        "history": [
            ("user", "¿Cuánto se cobró en bolívares en febrero 2026 en INPROA SANTONI?"),
            ("assistant", "En INPROA SANTONI se cobraron Bs. 5.432.100.000,00 en febrero 2026."),
        ],
        "expect_sql": True,
        "min_rows": 0,
        "must_contain_tables": ["c_payment"],
        "forbidden_tables": [],
        "must_contain_keywords": ["InproMaiz"],
        "notes": (
            "Follow-up: hereda período (feb 2026), métrica (cobranza VES), "
            "cambia SOLO la org. NO debe preguntar."
        ),
    },
    {
        "id": "compras_insumos_mes_corriente",
        "pregunta": "Compras de insumos este mes",
        "history": [],
        "expect_sql": True,
        "min_rows": 0,
        "must_contain_tables": ["c_invoice"],
        "forbidden_tables": [],
        "must_contain_keywords": [],
        "notes": (
            "Sin fecha explícita → REGLA #9(c) asume mes corriente, NO pregunta. "
            "issotrx='N' (compras), docstatus IN ('CO','CL')."
        ),
    },
]
