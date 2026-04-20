"""Static metadata used by the data catalog: tables, profile columns, date columns."""

# ──────────────────────────────────────────────────────────────────
# Tablas relevantes por departamento (schema adempiere)
# Estas son las tablas que los agentes realmente consultan.
# ──────────────────────────────────────────────────────────────────

DEPARTMENT_TABLES: dict[str, list[str]] = {
    "ventas": [
        "c_invoice",
        "c_invoiceline",
        "c_payment",
        "c_bpartner",
        "c_bpartner_location",
        "c_salesregion",
        "c_doctype",
        "m_product",
        "m_product_category",
        "c_currency",
    ],
    "finanzas": [
        "c_bankaccount",
        "c_bankstatement",
        "c_bankstatementline",
        "c_payment",
        "c_invoice",
        "c_bpartner",
        "c_currency",
    ],
    "contabilidad": [
        "gl_journal",
        "gl_journalline",
        "c_elementvalue",
        "c_acctschema",
        "c_period",
        "fact_acct",
        "c_allocationline",
    ],
    "rrhh": [
        "hr_employee",
        "hr_department",
        "hr_job",
        "hr_process",
        "hr_movement",
        "hr_concept",
        "hr_payroll",
        "c_bpartner",
    ],
    "produccion": [
        "m_product",
        "m_production",
        "m_productionline",
        "m_storageonhand",
        "m_warehouse",
        "m_locator",
        "m_product_category",
    ],
    "compras_insumos": [
        "c_invoice",
        "c_invoiceline",
        "c_bpartner",
        "m_product",
        "m_product_category",
        "c_currency",
        "c_doctype",
    ],
    "compras_productores": [
        "c_invoice",
        "c_invoiceline",
        "c_bpartner",
        "m_product",
        "c_currency",
        "c_doctype",
    ],
}

# Columnas "interesantes" para profiling (valores distintos, rangos)
PROFILE_COLUMNS: dict[str, list[str]] = {
    "c_invoice": ["docstatus", "issotrx", "c_currency_id", "dateinvoiced"],
    "c_payment": ["docstatus", "isreceipt", "c_currency_id", "datetrx"],
    "c_bpartner": ["isvendor", "iscustomer", "isemployee", "isactive"],
    "c_salesregion": ["name", "isactive"],
    "c_doctype": ["name", "docbasetype", "isactive"],
    "m_product": ["producttype", "isactive", "issold", "ispurchased"],
    "m_product_category": ["name", "isactive"],
    "hr_employee": ["isactive", "startdate", "enddate"],
    "hr_department": ["name", "isactive"],
    "hr_job": ["name", "isactive"],
    "hr_payroll": ["name", "isactive"],
    "hr_concept": ["name", "isactive"],
    "c_currency": ["iso_code", "cursymbol", "isactive"],
    "c_elementvalue": ["accounttype", "issummary", "isactive"],
    "m_warehouse": ["name", "isactive"],
    "c_bankaccount": ["accountno", "isactive"],
}

# Columnas de fecha para determinar rangos temporales
DATE_COLUMNS: dict[str, str] = {
    "c_invoice": "dateinvoiced",
    "c_payment": "datetrx",
    "gl_journal": "datedoc",
    "hr_process": "dateacct",
    "hr_movement": "validfrom",
    "m_production": "movementdate",
    "c_bankstatement": "statementdate",
    "fact_acct": "dateacct",
}


def get_all_relevant_tables() -> set[str]:
    """Devuelve el set de todas las tablas relevantes sin duplicados."""
    tables: set[str] = set()
    for dept_tables in DEPARTMENT_TABLES.values():
        tables.update(dept_tables)
    return tables
