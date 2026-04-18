"""Casos básicos para SQL Directo.

Preguntas simples de datos que Claude debe resolver sin ambigüedad:
  - Conteos (empleados, facturas)
  - Cumpleaños del mes (view lve_empleadosactivos)
  - Top vendedores
  - Promedios de sueldo

Cada caso declara:
  - id: identificador único
  - pregunta: prompt del usuario
  - history: historial previo (vacío para casos stand-alone)
  - expect_sql: True si debe generar SQL, False si debe declinar/clarificar
  - min_rows: mínimo de filas esperadas (0 si vacío es válido)
  - must_contain_tables: tablas que el SQL DEBE referenciar
  - forbidden_tables: tablas que NO debe usar (ej. hr_employee cuando se espera lve_*)
"""

CASES_BASIC = [
    {
        "id": "empleados_empaque_inproa",
        "pregunta": "¿Cuántos empleados hay en EMPAQUE de INPROA SANTONI?",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["lve_empleadosactivos"],
        "forbidden_tables": ["hr_employee"],
        "notes": "Debe usar view LVE, no tabla raw (inflaría 77%).",
    },
    {
        "id": "empleados_por_departamento_inproa",
        "pregunta": "¿Cuántos empleados por departamento en INPROA SANTONI?",
        "history": [],
        "expect_sql": True,
        "min_rows": 5,
        "must_contain_tables": ["lve_empleadosactivos"],
        "forbidden_tables": ["hr_employee"],
        "notes": "GROUP BY departamento, view LVE.",
    },
    {
        "id": "cumpleanios_mayo_inproa",
        "pregunta": "¿Quiénes cumplen años en mayo en INPROA SANTONI?",
        "history": [],
        "expect_sql": True,
        "min_rows": 0,  # puede ser 0 si nadie cumple, pero debe generar SQL
        "must_contain_tables": ["lve_empleadosactivos"],
        "forbidden_tables": ["hr_employee"],
        "notes": "EXTRACT(MONTH FROM birthday) = 5. View LVE.",
    },
    {
        "id": "sueldo_promedio_inpromaiz",
        "pregunta": "Sueldo promedio base en InproMaiz",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["lve_empleadosactivos"],
        "forbidden_tables": ["hr_employee"],
        "notes": "AVG(sueldo) — NO AVG(total) por performance.",
    },
    {
        "id": "cobranza_bolivares_feb",
        "pregunta": "¿Cuánto se cobró en bolívares en febrero 2026?",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["c_payment"],
        "forbidden_tables": [],
        "notes": "isreceipt='Y', currency VES=205.",
    },
    {
        "id": "top_vendedores_feb_inproa",
        "pregunta": "Top 10 vendedores en INPROA SANTONI en febrero 2026 en bolívares",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["c_invoice", "ad_user"],
        "forbidden_tables": [],
        "notes": "totallines (no grandtotal), docstatus IN ('CO','CL'), VES.",
    },
    {
        "id": "orgs_activas_count",
        "pregunta": "¿Cuántas organizaciones activas hay en iDempiere?",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["ad_org"],
        "forbidden_tables": [],
        "notes": "COUNT(*) WHERE isactive='Y'. Debe excluir demos si aplica blacklist.",
    },
    {
        "id": "facturas_venta_marzo_2026_ves",
        "pregunta": "¿Cuántas facturas de venta se emitieron en bolívares en marzo 2026?",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": ["c_invoice", "c_doctype"],
        "forbidden_tables": [],
        "notes": "docbasetype IN ('ARI','ARC') discriminado, currency=205.",
    },
    {
        "id": "saldos_bancarios_ves",
        "pregunta": "¿Cuál es el saldo actual de las cuentas bancarias en bolívares?",
        "history": [],
        "expect_sql": True,
        "min_rows": 1,
        "must_contain_tables": [],  # puede ser c_bankaccount o lve_saldos*
        "forbidden_tables": [],
        "notes": "Saldos en VES, c_bankaccount o view LVE de saldos.",
    },
    {
        "id": "productores_arroz_registrados",
        "pregunta": "¿Cuántos productores de arroz hay registrados?",
        "history": [],
        "expect_sql": True,
        "min_rows": 0,
        "must_contain_tables": [],  # c_bpartner con iscustomer/isvendor filter
        "forbidden_tables": [],
        "notes": "Productores = proveedores agrícolas, isvendor='Y'.",
    },
]
